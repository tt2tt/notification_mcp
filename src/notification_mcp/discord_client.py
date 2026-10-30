"""Discord Webhookへのメッセージ送信を行うモジュール。"""

import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

# Discordの仕様上、メッセージ本文の最大文字数
_MAX_CONTENT_LENGTH = 2000

# 送信タイムアウトのデフォルト秒数
_DEFAULT_TIMEOUT_SECONDS = 10.0

# リトライ対象とするHTTPステータスコード(レート制限・サーバー側の一時的な不調)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# リトライ1回あたりの待機秒数の上限(巨大なRetry-Afterで処理が長時間止まるのを防ぐ)
_MAX_WAIT_SECONDS = 60.0

# 秒数として解釈できるRetry-Afterヘッダーの形式(整数または小数)
_RETRY_AFTER_SECONDS_PATTERN = re.compile(r"\d+(\.\d+)?")


async def send_webhook_message(
    webhook_url: str, message: str, timeout: float = _DEFAULT_TIMEOUT_SECONDS
) -> None:
    """Discord Webhookへテキストメッセージを非同期送信する。"""
    # Discordの上限文字数を超えていないか事前にチェックする
    if len(message) > _MAX_CONTENT_LENGTH:
        raise ValueError(
            f"メッセージが{_MAX_CONTENT_LENGTH}文字を超えています(現在{len(message)}文字)。"
        )

    # 本文中の@everyone/@hereによる全員宛て通知のみ無効化する
    # (個別ユーザー・ロールへのメンションは従来どおり通知する)
    allowed_mentions = {"parse": ["users", "roles"]}
    payload = {"content": message, "allowed_mentions": allowed_mentions}

    # DiscordのWebhook APIにJSON形式でPOSTする(応答なし時に備えタイムアウトを設定)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()


def _resolve_wait_seconds(error: httpx.HTTPStatusError, attempt: int) -> float:
    """次のリトライまでの待機秒数を求める。

    `Retry-After`ヘッダーが秒数形式であればその値を優先し、
    無い場合やHTTP日付形式等の秒数として解釈できない場合は指数バックオフとする。
    上限(`_MAX_WAIT_SECONDS`)を超えるかどうかの判定は呼び出し側で行う。

    Args:
        error: リトライ対象となったHTTPステータスエラー。
        attempt: 0始まりの試行回数。

    Returns:
        次のリトライまでの待機秒数(サーバー指示どおりの値で、上限による丸めはしない)。
    """
    # 秒数形式のRetry-Afterヘッダーがあれば、サーバーの指示に従う
    retry_after = error.response.headers.get("Retry-After")
    if retry_after is not None and _RETRY_AFTER_SECONDS_PATTERN.fullmatch(retry_after):
        return float(retry_after)

    # それ以外は指数バックオフで待機する
    return 2**attempt


async def send_webhook_message_with_retry(
    webhook_url: str, message: str, max_retries: int = 3
) -> None:
    """一時的なエラー時に指数バックオフでリトライしながらWebhookへ送信する。

    待機秒数が`_MAX_WAIT_SECONDS`を超える場合は、指示より早い再送や
    長時間のブロックを避けるため、リトライせずに例外を送出する。

    Args:
        webhook_url: 送信先のWebhook URL。
        message: 送信するメッセージ本文。
        max_retries: 初回送信後にリトライする最大回数。

    Raises:
        httpx.HTTPStatusError: リトライ対象外のエラー、リトライ上限到達、
            または待機秒数が上限を超えた場合。
        httpx.TransportError: 通信エラーがリトライ上限まで続いた場合。
        ValueError: メッセージが文字数上限を超えている場合。
    """
    for attempt in range(max_retries + 1):
        try:
            await send_webhook_message(webhook_url, message)
            return
        except httpx.HTTPStatusError as error:
            # 429/5xxなど一時的なエラーのみリトライし、それ以外は即座に伝播する
            is_last_attempt = attempt >= max_retries
            is_retryable = error.response.status_code in _RETRYABLE_STATUS_CODES
            if is_last_attempt or not is_retryable:
                raise
            wait_seconds = _resolve_wait_seconds(error, attempt)

            # 待機秒数が上限を超える場合は、早すぎる再送を避けるためリトライを諦める
            if wait_seconds > _MAX_WAIT_SECONDS:
                logger.warning(
                    "待機秒数が上限を超えるためリトライを中止します"
                    "(HTTPステータス: %d、指示された待機: %.1f秒、上限: %.1f秒)",
                    error.response.status_code,
                    wait_seconds,
                    _MAX_WAIT_SECONDS,
                )
                raise
            logger.warning(
                "送信に失敗したためリトライします"
                "(試行 %d/%d、HTTPステータス: %d、%.1f秒後に再送信)",
                attempt + 1,
                max_retries,
                error.response.status_code,
                wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
        except httpx.TransportError as error:
            # 接続エラー・タイムアウトも一時的な不調とみなしリトライする
            if attempt >= max_retries:
                raise
            wait_seconds = 2**attempt
            logger.warning(
                "送信に失敗したためリトライします"
                "(試行 %d/%d、通信エラー: %s、%.1f秒後に再送信)",
                attempt + 1,
                max_retries,
                type(error).__name__,
                wait_seconds,
            )
            await asyncio.sleep(wait_seconds)

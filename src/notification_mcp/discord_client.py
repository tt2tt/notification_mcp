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

    # DiscordのWebhook APIにJSON形式でPOSTする(応答なし時に備えタイムアウトを設定)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(webhook_url, json={"content": message})
        response.raise_for_status()


def _resolve_wait_seconds(error: httpx.HTTPStatusError, attempt: int) -> float:
    """次のリトライまでの待機秒数を求める。

    `Retry-After`ヘッダーが秒数形式であればその値を優先し、
    無い場合やHTTP日付形式等の秒数として解釈できない場合は指数バックオフとする。
    いずれの場合も待機秒数は`_MAX_WAIT_SECONDS`を上限とする。

    Args:
        error: リトライ対象となったHTTPステータスエラー。
        attempt: 0始まりの試行回数。

    Returns:
        次のリトライまでの待機秒数。
    """
    # 秒数形式のRetry-Afterヘッダーがあれば、サーバーの指示に従う
    retry_after = error.response.headers.get("Retry-After")
    if retry_after is not None and _RETRY_AFTER_SECONDS_PATTERN.fullmatch(retry_after):
        wait_seconds = float(retry_after)
    else:
        # それ以外は指数バックオフで待機する
        wait_seconds = 2**attempt

    # 上限を超える待機はしない(inf等の異常値もここで上限に丸める)
    return min(wait_seconds, _MAX_WAIT_SECONDS)


async def send_webhook_message_with_retry(
    webhook_url: str, message: str, max_retries: int = 3
) -> None:
    """一時的なエラー時に指数バックオフでリトライしながらWebhookへ送信する。"""
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

"""Discord Webhookへのメッセージ送信を行うモジュール。"""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

# Discordの仕様上、メッセージ本文の最大文字数
_MAX_CONTENT_LENGTH = 2000

# 送信タイムアウトのデフォルト秒数
_DEFAULT_TIMEOUT_SECONDS = 10.0

# リトライ対象とするHTTPステータスコード(レート制限・サーバー側の一時的な不調)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


async def send_webhook_message(
    webhook_url: str, message: str, timeout: float = _DEFAULT_TIMEOUT_SECONDS
) -> None:
    """Discord Webhookへテキストメッセージを非同期送信する。"""
    if len(message) > _MAX_CONTENT_LENGTH:
        raise ValueError(
            f"メッセージが{_MAX_CONTENT_LENGTH}文字を超えています(現在{len(message)}文字)。"
        )

    # DiscordのWebhook APIにJSON形式でPOSTする(応答なし時に備えタイムアウトを設定)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(webhook_url, json={"content": message})
        response.raise_for_status()


def _resolve_wait_seconds(error: httpx.HTTPStatusError, attempt: int) -> float:
    """次のリトライまでの待機秒数を求める(Retry-Afterヘッダー優先、無ければ指数バックオフ)。"""
    retry_after = error.response.headers.get("Retry-After")
    if retry_after is not None:
        return float(retry_after)
    return 2**attempt


async def send_webhook_message_with_retry(
    webhook_url: str, message: str, max_retries: int = 3
) -> None:
    """一時的なエラー時に指数バックオフでリトライしながらWebhookへ送信する。"""
    for attempt in range(max_retries + 1):
        try:
            await send_webhook_message(webhook_url, message)
            return
        except httpx.HTTPStatusError as error:
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

"""Discord Webhookへのメッセージ送信を行うモジュール。"""

import httpx

# Discordの仕様上、メッセージ本文の最大文字数
_MAX_CONTENT_LENGTH = 2000

# 送信タイムアウトのデフォルト秒数
_DEFAULT_TIMEOUT_SECONDS = 10.0


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

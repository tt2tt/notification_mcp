"""Discord Webhookへのメッセージ送信を行うモジュール。"""

import httpx

# Discordの仕様上、メッセージ本文の最大文字数
_MAX_CONTENT_LENGTH = 2000


async def send_webhook_message(webhook_url: str, message: str) -> None:
    """Discord Webhookへテキストメッセージを非同期送信する。"""
    if len(message) > _MAX_CONTENT_LENGTH:
        raise ValueError(
            f"メッセージが{_MAX_CONTENT_LENGTH}文字を超えています(現在{len(message)}文字)。"
        )

    # DiscordのWebhook APIにJSON形式でPOSTする
    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json={"content": message})
        response.raise_for_status()

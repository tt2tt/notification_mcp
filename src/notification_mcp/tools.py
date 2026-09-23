"""MCPツールとして公開する処理をまとめたモジュール。"""

import httpx

from notification_mcp.config import load_webhook_config
from notification_mcp.discord_client import send_webhook_message_with_retry


async def send_notification(channel: str, message: str) -> str:
    """指定チャンネルのWebhookへ通知を送信するMCPツール本体。"""
    # .envから読み込んだチャンネル名とWebhook URLの対応表を取得する
    webhook_config = load_webhook_config()

    webhook_url = webhook_config.get(channel)
    if webhook_url is None:
        available = ", ".join(sorted(webhook_config))
        return (
            f"エラー: チャンネル '{channel}' は設定されていません。"
            f"利用可能なチャンネル: {available}"
        )

    try:
        await send_webhook_message_with_retry(webhook_url, message)
    except httpx.HTTPStatusError as error:
        return (
            f"エラー: '{channel}' への送信に失敗しました"
            f"(HTTPステータス: {error.response.status_code})"
        )
    except httpx.HTTPError:
        return f"エラー: '{channel}' への送信に失敗しました(通信エラー)"
    except ValueError as error:
        return f"エラー: {error}"

    return f"'{channel}' へ通知を送信しました。"

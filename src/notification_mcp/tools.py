"""MCPツールとして公開する処理をまとめたモジュール。"""

import logging

import httpx

from notification_mcp.config import load_webhook_config
from notification_mcp.discord_client import send_webhook_message_with_retry

logger = logging.getLogger(__name__)


async def send_notification(channel: str, message: str) -> str:
    """指定チャンネルのWebhookへ通知を送信するMCPツール本体。"""
    # .envから読み込んだチャンネル名とWebhook URLの対応表を取得する
    try:
        webhook_config = load_webhook_config()
    except ValueError as error:
        logger.error("Webhook設定の読み込みに失敗しました: %s", error)
        return f"エラー: {error}"

    webhook_url = webhook_config.get(channel)
    if webhook_url is None:
        available = ", ".join(sorted(webhook_config))
        logger.warning("未設定のチャンネルが指定されました: %s", channel)
        return (
            f"エラー: チャンネル '{channel}' は設定されていません。"
            f"利用可能なチャンネル: {available}"
        )

    try:
        await send_webhook_message_with_retry(webhook_url, message)
    except httpx.HTTPStatusError as error:
        logger.error(
            "'%s' への送信に失敗しました(HTTPステータス: %s)",
            channel,
            error.response.status_code,
        )
        return (
            f"エラー: '{channel}' への送信に失敗しました"
            f"(HTTPステータス: {error.response.status_code})"
        )
    except httpx.HTTPError:
        logger.error("'%s' への送信に失敗しました(通信エラー)", channel)
        return f"エラー: '{channel}' への送信に失敗しました(通信エラー)"
    except ValueError as error:
        logger.warning("'%s' への送信を中止しました: %s", channel, error)
        return f"エラー: {error}"

    logger.info("'%s' へ通知を送信しました。", channel)
    return f"'{channel}' へ通知を送信しました。"

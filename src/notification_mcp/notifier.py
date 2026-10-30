"""通知送信のサービス層をまとめたモジュール。

MCPツール・CLI等の境界層から共通で呼び出され、失敗時は`NotificationError`系の例外を送出する。
"""

import logging

from notification_mcp.config import load_webhook_config
from notification_mcp.error_handlers import reraise_as
from notification_mcp.exceptions import ChannelNotConfiguredError, WebhookConfigError

logger = logging.getLogger(__name__)


@reraise_as(WebhookConfigError, ValueError)
def _load_webhook_config() -> dict[str, str]:
    """Webhook設定を読み込み、`{チャンネル名: URL}`の辞書を返す。

    Returns:
        チャンネル名とWebhook URLの対応表。

    Raises:
        WebhookConfigError: 設定が存在しない、またはURLの形式が不正な場合。
    """
    # .envから読み込んだ設定を返す(ValueErrorはデコレータで変換される)
    return load_webhook_config()


def _resolve_webhook_url(webhook_config: dict[str, str], channel: str) -> str:
    """チャンネル名に対応するWebhook URLを返す。

    Args:
        webhook_config: チャンネル名とWebhook URLの対応表。
        channel: 送信先のチャンネル名。

    Returns:
        指定チャンネルのWebhook URL。

    Raises:
        ChannelNotConfiguredError: 指定チャンネルが設定されていない場合。
    """
    # 指定されたチャンネル名が設定済みかどうかを確認する
    webhook_url = webhook_config.get(channel)
    if webhook_url is None:
        # 指定ミスに気付けるよう、利用可能なチャンネル名を併記する
        channel_names = sorted(webhook_config)
        available = ", ".join(channel_names)
        raise ChannelNotConfiguredError(
            f"チャンネル '{channel}' は設定されていません。"
            f"利用可能なチャンネル: {available}"
        )
    return webhook_url

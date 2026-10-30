"""通知送信のサービス層をまとめたモジュール。

MCPツール・CLI等の境界層から共通で呼び出され、失敗時は`NotificationError`系の例外を送出する。
"""

import logging

from notification_mcp.config import load_webhook_config
from notification_mcp.error_handlers import reraise_as
from notification_mcp.exceptions import WebhookConfigError

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

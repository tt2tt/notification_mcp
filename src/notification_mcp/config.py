"""Webhook設定の読み込み・検証を行うモジュール。"""

import os
import re

from dotenv import load_dotenv

# .envからDISCORD_WEBHOOK_<チャンネル名>を拾うためのプレフィックス
_WEBHOOK_ENV_PREFIX = "DISCORD_WEBHOOK_"

# Discord WebhookのURL形式を検証するための正規表現
_WEBHOOK_URL_PATTERN = re.compile(
    r"^https://discord(app)?\.com/api/webhooks/\d+/.+$"
)


def validate_webhook_url(url: str) -> None:
    """Webhook URLの形式を検証し、不正であれば例外を送出する。

    例外メッセージはログ等に記録される可能性があるため、URL本体は含めない。
    """
    if not _WEBHOOK_URL_PATTERN.match(url):
        raise ValueError("不正なDiscord Webhook URL形式です。")


def load_webhook_config() -> dict[str, str]:
    """.envからチャンネル名とWebhook URLの対応表を読み込む。"""
    # プロセス起動時に.envを読み込み、環境変数として展開する
    load_dotenv()

    webhook_config: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith(_WEBHOOK_ENV_PREFIX):
            continue
        channel = key.removeprefix(_WEBHOOK_ENV_PREFIX).lower()
        validate_webhook_url(value)
        webhook_config[channel] = value

    if not webhook_config:
        raise ValueError(
            f"Webhook URLが1件も設定されていません。"
            f"'.env'に{_WEBHOOK_ENV_PREFIX}<チャンネル名>を追加してください。"
        )

    return webhook_config

"""Webhook設定の読み込み・検証を行うモジュール。"""

import logging
import os
import re

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# .envからDISCORD_WEBHOOK_<チャンネル名>を拾うためのプレフィックス
_WEBHOOK_ENV_PREFIX = "DISCORD_WEBHOOK_"

# Discord WebhookのURL形式を検証するための正規表現
_WEBHOOK_URL_PATTERN = re.compile(
    r"^https://discord(app)?\.com/api/webhooks/\d+/.+$"
)


def _is_valid_webhook_url(url: str) -> bool:
    """Webhook URLがDiscordの形式に一致するかを判定する。

    Args:
        url: 判定するWebhook URL。

    Returns:
        形式に一致する場合は`True`。
    """
    # 正規表現に先頭から一致するかで判定する
    return _WEBHOOK_URL_PATTERN.match(url) is not None


def validate_webhook_url(url: str) -> None:
    """Webhook URLの形式を検証し、不正であれば例外を送出する。

    例外メッセージはログ等に記録される可能性があるため、URL本体は含めない。

    Args:
        url: 検証するWebhook URL。

    Raises:
        ValueError: URLの形式が不正な場合。
    """
    # 形式に一致しなければ、URL本体を含めずに例外を送出する
    if not _is_valid_webhook_url(url):
        raise ValueError("不正なDiscord Webhook URL形式です。")


def load_webhook_config() -> dict[str, str]:
    """.envからチャンネル名とWebhook URLの対応表を読み込む。

    値が空(空白のみを含む)のキーは未設定とみなして警告ログを出し、読み飛ばす。
    1つの未設定チャンネルのために、他の設定済みチャンネルまで送信できなくなることを防ぐ。

    Returns:
        チャンネル名(小文字)とWebhook URLの対応表。

    Raises:
        ValueError: 有効なWebhook URLが1件も設定されていない場合、
            またはURLの形式が不正な場合。
    """
    # プロセス起動時に.envを読み込み、環境変数として展開する
    load_dotenv()

    webhook_config: dict[str, str] = {}
    # プレフィックスに一致する環境変数だけを抽出し、チャンネル名をキーにした辞書を作る
    for key, value in os.environ.items():
        if not key.startswith(_WEBHOOK_ENV_PREFIX):
            continue
        channel = key.removeprefix(_WEBHOOK_ENV_PREFIX).lower()

        # 値が空のキーは未設定とみなし、警告のうえ読み飛ばす
        if not value.strip():
            logger.warning(
                "Webhook URLが空のため、チャンネル '%s' を読み飛ばします。", channel
            )
            continue

        validate_webhook_url(value)
        webhook_config[channel] = value

    if not webhook_config:
        raise ValueError(
            f"Webhook URLが1件も設定されていません。"
            f"'.env'に{_WEBHOOK_ENV_PREFIX}<チャンネル名>を追加してください。"
        )

    return webhook_config

"""Webhook設定の読み込み・検証を行うモジュール。"""

import logging
import os
import re

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# .envからDISCORD_WEBHOOK_<チャンネル名>を拾うためのプレフィックス
_WEBHOOK_ENV_PREFIX = "DISCORD_WEBHOOK_"

# Discord WebhookのURL形式を検証するための正規表現(全体一致・空白を含まない)
_WEBHOOK_URL_PATTERN = re.compile(r"https://discord(app)?\.com/api/webhooks/\d+/\S+")


def _is_valid_webhook_url(url: str) -> bool:
    """Webhook URLがDiscordの形式に一致するかを判定する。

    Args:
        url: 判定するWebhook URL。

    Returns:
        形式に一致する場合は`True`。
    """
    # 末尾に余計な文字が付いたURLを通さないよう、全体一致で判定する
    return _WEBHOOK_URL_PATTERN.fullmatch(url) is not None


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


def _parse_webhook_entry(key: str, value: str) -> tuple[str, str] | None:
    """`DISCORD_WEBHOOK_<チャンネル名>`の1件からチャンネル名とWebhook URLを取り出す。

    不正な1件のために他のチャンネルまで送信できなくなることを防ぐため、
    使用できない設定は例外にせず、警告ログを出して読み飛ばす。
    ログにはURL本体を含めない。

    Args:
        key: 環境変数名(`DISCORD_WEBHOOK_`で始まる)。
        value: 環境変数の値(Webhook URL)。

    Returns:
        `(チャンネル名(小文字), 前後の空白を除いたURL)`。
        チャンネル名が空・値が空・URL形式が不正な場合は`None`。
    """
    # プレフィックスを除いたチャンネル名を小文字化し、URLの前後の空白を取り除く
    channel = key.removeprefix(_WEBHOOK_ENV_PREFIX).lower()
    webhook_url = value.strip()

    # チャンネル名が空のキー(DISCORD_WEBHOOK_のみ)は指定できないため読み飛ばす
    if not channel:
        logger.warning("チャンネル名が空のキーがあるため読み飛ばします。")
        return None

    # 値が空のキーは未設定とみなして読み飛ばす
    if not webhook_url:
        logger.warning(
            "Webhook URLが空のため、チャンネル '%s' を読み飛ばします。", channel
        )
        return None

    # URL形式が不正なキーは送信できないため読み飛ばす
    if not _is_valid_webhook_url(webhook_url):
        logger.warning(
            "Webhook URLの形式が不正なため、チャンネル '%s' を読み飛ばします。", channel
        )
        return None

    # 使用できる設定としてチャンネル名とURLを返す
    return channel, webhook_url


def load_webhook_config() -> dict[str, str]:
    """.envからチャンネル名とWebhook URLの対応表を読み込む。

    チャンネル名が空・値が空・URL形式が不正なキーは警告ログを出して読み飛ばし、
    不正な1件のために他の設定済みチャンネルまで送信できなくなることを防ぐ。

    Returns:
        チャンネル名(小文字)とWebhook URLの対応表。

    Raises:
        ValueError: 使用できるWebhook URLが1件も設定されていない場合。
    """
    # プロセス起動時に.envを読み込み、環境変数として展開する
    load_dotenv()

    webhook_config: dict[str, str] = {}
    # プレフィックスに一致する環境変数だけを抽出し、チャンネル名をキーにした辞書を作る
    for key, value in os.environ.items():
        if not key.startswith(_WEBHOOK_ENV_PREFIX):
            continue

        # 1件ごとに解析し、使用できない設定は読み飛ばす
        entry = _parse_webhook_entry(key, value)
        if entry is None:
            continue
        channel, webhook_url = entry
        webhook_config[channel] = webhook_url

    # 使用できる設定が1件もなければ、設定方法を案内する例外を送出する
    if not webhook_config:
        raise ValueError(
            "使用できるWebhook URLが1件も設定されていません。"
            f"'.env'に{_WEBHOOK_ENV_PREFIX}<チャンネル名>を追加するか、"
            "既存の値が空・形式不正でないか確認してください。"
        )

    return webhook_config

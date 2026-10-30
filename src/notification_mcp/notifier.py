"""通知送信のサービス層をまとめたモジュール。

MCPツール・CLI等の境界層から共通で呼び出され、失敗時は`NotificationError`系の例外を送出する。
"""

import logging
import re

from notification_mcp.config import load_webhook_config
from notification_mcp.discord_client import send_webhook_message_with_retry
from notification_mcp.error_handlers import reraise_as, translate_send_errors
from notification_mcp.exceptions import (
    ChannelNotConfiguredError,
    InvalidChannelError,
    WebhookConfigError,
)

logger = logging.getLogger(__name__)

# チャンネル名として許可する形式(.envのキー名に使える英数字・'_'と'-'のみ)
_CHANNEL_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def _validate_channel(channel: str) -> None:
    """チャンネル名の形式を検証する。

    改行・制御文字等を含むチャンネル名がログや結果メッセージに出力され、
    偽のログ行を書き込まれること(ログインジェクション)を防ぐ。

    Args:
        channel: 送信先のチャンネル名。

    Raises:
        InvalidChannelError: 英数字・`_`・`-`以外の文字を含む、または空の場合。
    """
    # 許可した文字のみで構成されていなければ、入力値を含めずに例外を送出する
    if _CHANNEL_NAME_PATTERN.fullmatch(channel) is None:
        raise InvalidChannelError(
            "チャンネル名の形式が不正です(英数字・'_'・'-'のみ使用できます)。"
        )


@reraise_as(WebhookConfigError, ValueError)
def _load_webhook_config() -> dict[str, str]:
    """Webhook設定を読み込み、`{チャンネル名: URL}`の辞書を返す。

    Returns:
        チャンネル名とWebhook URLの対応表。

    空値・形式不正のURLは`load_webhook_config`で警告のうえ読み飛ばされる。

    Raises:
        WebhookConfigError: 使用できるWebhook URLが1件も設定されていない場合。
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
        # 指定ミスに気付けるよう利用可能なチャンネル名を併記し、
        # .envのURLが空・形式不正で読み飛ばされた可能性も案内する
        channel_names = sorted(webhook_config)
        available = ", ".join(channel_names)
        raise ChannelNotConfiguredError(
            f"チャンネル '{channel}' は設定されていません。"
            f"利用可能なチャンネル: {available}"
            "(.envに設定済みの場合は、Webhook URLが空または形式不正のため"
            "読み飛ばされていないかログを確認してください)"
        )

    # 設定済みのチャンネルであれば対応するWebhook URLを返す
    return webhook_url


@translate_send_errors
async def _send(channel: str, webhook_url: str, message: str) -> None:
    """Webhookへリトライ付きでメッセージを送信する。

    Args:
        channel: 送信先のチャンネル名(例外メッセージ用)。
        webhook_url: 送信先のWebhook URL。
        message: 送信するメッセージ本文。

    Raises:
        SendFailedError: HTTPエラーまたは通信エラーで送信に失敗した場合。
        MessageRejectedError: メッセージが文字数上限を超えている場合。
    """
    # 送信時の例外はデコレータでチャンネル名入りの通知例外へ変換される
    await send_webhook_message_with_retry(webhook_url, message)


async def notify(channel: str, message: str) -> None:
    """指定チャンネルのWebhookへ通知を送信する。

    Args:
        channel: 送信先のチャンネル名(`.env`の`DISCORD_WEBHOOK_<チャンネル名>`に対応)。
            大文字・小文字は区別しない。
        message: 送信するメッセージ本文。

    Raises:
        InvalidChannelError: チャンネル名の形式が不正な場合。
        WebhookConfigError: 使用できるWebhook URLが1件も設定されていない場合。
        ChannelNotConfiguredError: 指定チャンネルが未設定、またはURLが空・形式不正で
            読み飛ばされた場合。
        MessageRejectedError: メッセージが文字数上限を超えている場合。
        SendFailedError: HTTPエラーまたは通信エラーで送信に失敗した場合。
    """
    # ログや結果メッセージへ出力する前に、チャンネル名の形式を検証する
    _validate_channel(channel)

    # .envのキーから作るチャンネル名は小文字化されるため、指定側も小文字にそろえる
    channel = channel.lower()

    # .envから読み込んだチャンネル名とWebhook URLの対応表を取得する
    webhook_config = _load_webhook_config()

    # 指定されたチャンネル名からWebhook URLを解決する
    webhook_url = _resolve_webhook_url(webhook_config, channel)

    # リトライ付きでWebhookへ送信する
    await _send(channel, webhook_url, message)

    # 送信成功を記録する(Webhook URLは出力しない)
    logger.info("'%s' へ通知を送信しました。", channel)

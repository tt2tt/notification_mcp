"""Webhook設定の読み込み・検証を行うモジュール。"""

import logging
import os
import re

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# .envからDISCORD_WEBHOOK_<チャンネル名>を拾うためのプレフィックス
_WEBHOOK_ENV_PREFIX = "DISCORD_WEBHOOK_"

# Discord WebhookのURL形式を検証するための正規表現(全体一致で使用)
# トークンはURLセーフな文字(英数字・'_'・'-')に限定し、ログの伏せ字処理で
# トークンの一部が残る値(引用符等を含む値)を受け付けない。
# トークン末尾のスラッシュ1つと、末尾の任意のクエリのみ許可する
_WEBHOOK_URL_PATTERN = re.compile(
    r"https://discord(app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+/?(\?\S*)?"
)

# チャンネル名として許可する形式(.envのキー名に使える英数字・'_'と'-'のみ)
_CHANNEL_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def is_valid_channel_name(channel: str) -> bool:
    """チャンネル名が許可された形式(英数字・`_`・`-`のみ、1文字以上)かを判定する。

    改行・制御文字等を含む名前がログやメッセージへ出力され、
    偽のログ行を書き込まれること(ログインジェクション)を防ぐために使用する。

    Args:
        channel: 判定するチャンネル名。

    Returns:
        許可された形式の場合は`True`。
    """
    # 許可した文字のみで構成されているかを全体一致で判定する
    return _CHANNEL_NAME_PATTERN.fullmatch(channel) is not None


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
        チャンネル名の形式が不正(空を含む)・値が空・URL形式が不正な場合は`None`。
    """
    # プレフィックスを除いたチャンネル名を小文字化し、URLの前後の空白を取り除く
    channel = key.removeprefix(_WEBHOOK_ENV_PREFIX).lower()
    webhook_url = value.strip()

    # 指定できない形式のチャンネル名(空を含む)は読み飛ばす
    # (ログインジェクションを防ぐため、ログに名前は出力しない)
    if not is_valid_channel_name(channel):
        logger.warning("チャンネル名の形式が不正なキーがあるため読み飛ばします。")
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


def _is_webhook_key(key: str) -> bool:
    """環境変数名がWebhookの設定(`DISCORD_WEBHOOK_`で始まる)かを判定する。

    `.env`のキーは大文字小文字が区別されるため、大文字にそろえて判定する。

    Args:
        key: 判定する環境変数名。

    Returns:
        Webhookの設定を表すキーの場合は`True`。
    """
    # 大文字にそろえてプレフィックスと比較する
    upper_key = key.upper()
    return upper_key.startswith(_WEBHOOK_ENV_PREFIX)


def _export_non_webhook_env(dotenv_entries: dict[str, str | None]) -> None:
    """`.env`のWebhook以外の設定を、既存の環境変数を上書きせずに`os.environ`へ反映する。

    `HTTPS_PROXY`等、`httpx`等のライブラリが環境変数から読む設定を`.env`に書けるようにする
    (従来の`load_dotenv()`と同じく、既に設定されている環境変数は変更しない)。
    Webhookの設定は送信のたびに読み直すため、`os.environ`へは反映しない。

    Args:
        dotenv_entries: `dotenv_values()`で読み込んだ`.env`の内容。
    """
    for key, value in dotenv_entries.items():
        # Webhookの設定と、値のない行は反映対象外とする
        if _is_webhook_key(key) or value is None:
            continue

        # 既に設定されている環境変数は上書きしない
        os.environ.setdefault(key, value)


def _read_webhook_env() -> dict[str, str]:
    """`.env`とOS環境変数から`DISCORD_WEBHOOK_`で始まる設定を読み込む。

    Webhookの設定は呼び出しのたびに`.env`から読み直し、`os.environ`へは展開しない。
    そのため実行中のMCPサーバーでも、`.env`の名称変更・削除・値の修正が次回の送信から反映される。
    同じキーがOS環境変数にもある場合は、OS環境変数を優先する。
    キーのプレフィックスは大文字小文字を区別せず判定し、キー名は大文字にそろえる。

    Returns:
        環境変数名(大文字)とその値の対応表(値のない行は空文字列として扱う)。
    """
    # 読み込んだ設定を格納する対応表を用意する
    webhook_env: dict[str, str] = {}

    # .envの内容を毎回読み直し、Webhook以外の設定は環境変数へ反映する
    dotenv_entries = dotenv_values()
    _export_non_webhook_env(dotenv_entries)

    # .envからプレフィックスに一致するキーだけを取り出す
    for key, value in dotenv_entries.items():
        if not _is_webhook_key(key):
            continue

        # 「KEY」のみで値のない行は空値として扱う(後段で未設定として読み飛ばす)
        if value is None:
            value = ""
        upper_key = key.upper()
        webhook_env[upper_key] = value

    # OS環境変数を後から反映し、.envより優先させる
    for key, value in os.environ.items():
        if _is_webhook_key(key):
            upper_key = key.upper()
            webhook_env[upper_key] = value

    # .envとOS環境変数を合わせた設定を返す
    return webhook_env


def load_webhook_config() -> dict[str, str]:
    """.envとOS環境変数からチャンネル名とWebhook URLの対応表を読み込む。

    `.env`は呼び出しのたびに読み直すため、変更は再起動なしで反映される。
    チャンネル名の形式が不正・値が空・URL形式が不正なキーは警告ログを出して読み飛ばし、
    不正な1件のために他の設定済みチャンネルまで送信できなくなることを防ぐ。

    Returns:
        チャンネル名(小文字)とWebhook URLの対応表。

    Raises:
        ValueError: 使用できるWebhook URLが1件も設定されていない場合。
    """
    # .envとOS環境変数からDISCORD_WEBHOOK_系の設定を読み込む
    webhook_env = _read_webhook_env()

    # チャンネル名をキーにした対応表を用意する
    webhook_config: dict[str, str] = {}
    for key, value in webhook_env.items():
        # 1件ごとに解析し、使用できない設定は読み飛ばす
        entry = _parse_webhook_entry(key, value)
        if entry is None:
            continue

        # 解析結果のチャンネル名とURLを対応表へ登録する
        channel, webhook_url = entry
        webhook_config[channel] = webhook_url

    # 使用できる設定が1件もなければ、設定方法を案内する例外を送出する
    if not webhook_config:
        raise ValueError(
            "使用できるWebhook URLが1件も設定されていません。"
            f"'.env'に{_WEBHOOK_ENV_PREFIX}<チャンネル名>を追加するか、"
            "既存の値が空・形式不正でないか確認してください。"
        )

    # 使用できるチャンネルの対応表を返す
    return webhook_config

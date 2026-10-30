"""error_handlers.pyのユニットテスト。"""

import logging

import httpx
import pytest

from notification_mcp.error_handlers import (
    reraise_as,
    return_error_message,
    return_exit_code,
    translate_send_errors,
)
from notification_mcp.exceptions import (
    ChannelNotConfiguredError,
    SendFailedError,
    WebhookConfigError,
)

_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789012345678/dummy-token"


def test_reraise_as_converts_exception():
    """指定した例外がメッセージを引き継いだtargetの例外へ変換され、連鎖は切られる。"""

    # ValueErrorを送出する関数にデコレータを適用する
    @reraise_as(WebhookConfigError, ValueError)
    def load() -> None:
        raise ValueError("設定がありません")

    # WebhookConfigErrorへ変換されることを確認する
    with pytest.raises(WebhookConfigError) as exc_info:
        load()

    # メッセージが引き継がれ、元例外がトレースバックに表示されないことを確認する
    assert str(exc_info.value) == "設定がありません"
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__


async def test_translate_send_errors_converts_http_status_error():
    """HTTPStatusErrorがステータスコード入りのSendFailedErrorへ変換され、URLは含まれない。"""

    # 404応答のHTTPStatusErrorを送出する送信関数にデコレータを適用する
    @translate_send_errors
    async def send(channel: str) -> None:
        request = httpx.Request("POST", _WEBHOOK_URL)
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError("Not Found", request=request, response=response)

    # SendFailedErrorへ変換されることを確認する
    with pytest.raises(SendFailedError) as exc_info:
        await send("general")

    # チャンネル名とステータスコードを含み、Webhook URLを含まないことを確認する
    message = str(exc_info.value)
    assert "general" in message
    assert "404" in message
    assert _WEBHOOK_URL not in message


async def test_return_error_message_returns_prefixed_message():
    """通知例外は「エラー: 」付きの文字列、想定外の例外は汎用メッセージとして返る。"""

    # 通知例外を送出するツール関数にデコレータを適用する
    @return_error_message
    async def notification_tool() -> str:
        raise ChannelNotConfiguredError("チャンネル 'x' は設定されていません。")

    # Webhook URLを含む想定外の例外を送出するツール関数にデコレータを適用する
    @return_error_message
    async def unexpected_tool() -> str:
        raise RuntimeError(_WEBHOOK_URL)

    # 通知例外のメッセージが「エラー: 」付きで返ることを確認する
    result = await notification_tool()
    assert result == "エラー: チャンネル 'x' は設定されていません。"

    # 想定外の例外は内容(URL)を含まない汎用メッセージで返ることを確認する
    unexpected_result = await unexpected_tool()
    assert unexpected_result.startswith("エラー: ")
    assert _WEBHOOK_URL not in unexpected_result


def test_return_exit_code_returns_one_on_error(caplog):
    """例外発生時は終了コード1を返し、想定外の例外の内容(URL)はログに出力されない。"""

    # Webhook URLを含む想定外の例外を送出するメイン関数にデコレータを適用する
    @return_exit_code
    def main() -> int:
        raise RuntimeError(_WEBHOOK_URL)

    # 終了コード1が返ることを確認する
    with caplog.at_level(logging.WARNING):
        exit_code = main()
    assert exit_code == 1

    # ログには型名のみ記録され、Webhook URLが含まれないことを確認する
    assert "RuntimeError" in caplog.text
    assert _WEBHOOK_URL not in caplog.text

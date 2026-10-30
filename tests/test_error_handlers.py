"""error_handlers.pyのユニットテスト。"""

import httpx
import pytest

from notification_mcp.error_handlers import (
    reraise_as,
    translate_send_errors,
)
from notification_mcp.exceptions import (
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

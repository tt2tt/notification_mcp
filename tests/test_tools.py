"""tools.pyのユニットテスト。"""

import httpx

from notification_mcp import notifier, tools

_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789012345678/dummy-token"


async def test_send_notification_returns_success_message(monkeypatch):
    """送信に成功した場合、成功メッセージが返る。"""
    monkeypatch.setattr(
        notifier, "load_webhook_config", lambda: {"general": _WEBHOOK_URL}
    )

    async def fake_send(webhook_url: str, message: str) -> None:
        return None

    monkeypatch.setattr(notifier, "send_webhook_message_with_retry", fake_send)

    result = await tools.send_notification("general", "test")

    assert result == "'general' へ通知を送信しました。"


async def test_send_notification_returns_error_for_unknown_channel(monkeypatch):
    """未設定のチャンネルを指定した場合、利用可能なチャンネル名を含むエラーが返る。"""
    monkeypatch.setattr(
        notifier, "load_webhook_config", lambda: {"general": _WEBHOOK_URL}
    )

    result = await tools.send_notification("unknown", "test")

    assert "unknown" in result
    assert "general" in result


async def test_send_notification_returns_error_on_http_failure(monkeypatch):
    """送信失敗時、エラーメッセージにWebhook URLが含まれないことを確認する。"""
    monkeypatch.setattr(
        notifier, "load_webhook_config", lambda: {"general": _WEBHOOK_URL}
    )

    async def fake_send(webhook_url: str, message: str) -> None:
        request = httpx.Request("POST", webhook_url)
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError("Not Found", request=request, response=response)

    monkeypatch.setattr(notifier, "send_webhook_message_with_retry", fake_send)

    result = await tools.send_notification("general", "test")

    assert "404" in result
    assert _WEBHOOK_URL not in result

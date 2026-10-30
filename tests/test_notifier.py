"""notifier.pyのユニットテスト。"""

import pytest

from notification_mcp import notifier
from notification_mcp.exceptions import (
    ChannelNotConfiguredError,
)

_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789012345678/dummy-token"


async def test_notify_sends_message_successfully(monkeypatch):
    """設定済みチャンネルを指定すると、対応するWebhook URLへメッセージが送信される。"""
    # 設定読込と送信処理をモック化し、送信内容を記録する
    monkeypatch.setattr(
        notifier, "load_webhook_config", lambda: {"general": _WEBHOOK_URL}
    )
    sent: list[tuple[str, str]] = []

    async def fake_send(webhook_url: str, message: str) -> None:
        sent.append((webhook_url, message))

    monkeypatch.setattr(notifier, "send_webhook_message_with_retry", fake_send)

    # 通知を送信する
    await notifier.notify("general", "test")

    # 解決されたWebhook URLへ本文が1回だけ送信されたことを確認する
    assert sent == [(_WEBHOOK_URL, "test")]


async def test_notify_raises_for_unknown_channel(monkeypatch):
    """未設定のチャンネルを指定すると、利用可能なチャンネル名を含む例外が送出される。"""
    # 設定読込をモック化する
    monkeypatch.setattr(
        notifier, "load_webhook_config", lambda: {"general": _WEBHOOK_URL}
    )

    # 未設定チャンネルを指定するとChannelNotConfiguredErrorが送出されることを確認する
    with pytest.raises(ChannelNotConfiguredError) as exc_info:
        await notifier.notify("unknown", "test")

    # 利用可能なチャンネル名を含み、Webhook URLを含まないことを確認する
    message = str(exc_info.value)
    assert "general" in message
    assert _WEBHOOK_URL not in message

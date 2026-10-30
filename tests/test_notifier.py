"""notifier.pyのユニットテスト。"""

import pytest

from notification_mcp import notifier
from notification_mcp.exceptions import (
    ChannelNotConfiguredError,
    InvalidChannelError,
    WebhookConfigError,
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


async def test_notify_raises_webhook_config_error(monkeypatch):
    """設定読込でValueErrorが発生すると、WebhookConfigErrorへ変換されて送出される。"""

    # 設定が1件もない状態を模してValueErrorを送出させる
    def fake_load() -> dict[str, str]:
        raise ValueError("Webhook URLが1件も設定されていません。")

    monkeypatch.setattr(notifier, "load_webhook_config", fake_load)

    # WebhookConfigErrorへ変換されることを確認する
    with pytest.raises(WebhookConfigError):
        await notifier.notify("general", "test")


async def test_notify_raises_for_invalid_channel_name(monkeypatch):
    """改行等を含むチャンネル名は、設定読込前に入力値を含まない例外で拒否される。"""

    # 検証より先に設定読込が行われた場合に検知できるよう、呼び出しを記録する
    calls: list[str] = []

    def fake_load() -> dict[str, str]:
        calls.append("load")
        return {"general": _WEBHOOK_URL}

    monkeypatch.setattr(notifier, "load_webhook_config", fake_load)
    injected_channel = "x\n2026-10-30 00:00:00 [INFO] 偽のログ行"

    # InvalidChannelErrorが送出されることを確認する
    with pytest.raises(InvalidChannelError) as exc_info:
        await notifier.notify(injected_channel, "test")

    # メッセージに入力値を含まず、設定読込も行われていないことを確認する
    assert "偽のログ行" not in str(exc_info.value)
    assert calls == []

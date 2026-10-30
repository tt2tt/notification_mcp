"""notifier.pyのユニットテスト。"""

from notification_mcp import notifier

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

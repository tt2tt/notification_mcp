"""config.pyのユニットテスト。"""

import os

import pytest

from notification_mcp import config

_VALID_URL = "https://discord.com/api/webhooks/123456789012345678/dummy-token"
_INVALID_URL = "https://example.com/not-a-webhook"


def test_validate_webhook_url_accepts_valid_url():
    """正しい形式のDiscord Webhook URLはエラーにならない。"""
    config.validate_webhook_url(_VALID_URL)  # 例外が発生しなければ成功


def test_validate_webhook_url_rejects_invalid_url():
    """Discord以外のドメインなど不正な形式のURLはValueErrorになる。"""
    with pytest.raises(ValueError):
        config.validate_webhook_url(_INVALID_URL)


def test_load_webhook_config_returns_channel_url_dict(monkeypatch):
    """DISCORD_WEBHOOK_プレフィックスの環境変数から{チャンネル名: URL}が得られる。"""
    # load_dotenv()は呼び出し元ディレクトリから親をたどって実プロジェクトの.envを
    # 見つけてしまうため、テストではno-op化してos.environのみを対象にする
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DISCORD_WEBHOOK_GENERAL", _VALID_URL)
    monkeypatch.setenv("DISCORD_WEBHOOK_ALERT", _VALID_URL)

    result = config.load_webhook_config()

    assert result == {"general": _VALID_URL, "alert": _VALID_URL}


def test_load_webhook_config_raises_when_no_webhooks_configured(monkeypatch):
    """DISCORD_WEBHOOK_で始まる環境変数が1件もなければValueErrorになる。"""
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    # 環境変数に残っているDISCORD_WEBHOOK_系をすべて取り除く
    for key in list(os.environ):
        if key.startswith("DISCORD_WEBHOOK_"):
            monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError):
        config.load_webhook_config()

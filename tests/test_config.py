"""config.pyのユニットテスト。"""

import logging
import os

import pytest

from notification_mcp import config

_VALID_URL = "https://discord.com/api/webhooks/123456789012345678/dummy-token"
_INVALID_URL = "https://example.com/not-a-webhook"


@pytest.fixture(autouse=True)
def _isolate_webhook_env(monkeypatch):
    """テストが実プロジェクトの.envや開発環境の環境変数に依存しないよう分離する。"""
    # dotenv_values()は呼び出し元ディレクトリから親をたどって実プロジェクトの.envを
    # 見つけてしまうため、空の内容を返すようにしてos.environのみを対象にする
    monkeypatch.setattr(config, "dotenv_values", lambda: {})

    # 環境変数に残っているDISCORD_WEBHOOK_系を、大文字小文字を区別せずすべて取り除く
    for key in list(os.environ):
        upper_key = key.upper()
        if upper_key.startswith("DISCORD_WEBHOOK_"):
            monkeypatch.delenv(key, raising=False)


def test_validate_webhook_url_accepts_valid_url():
    """正しい形式のDiscord Webhook URLはエラーにならない。"""
    config.validate_webhook_url(_VALID_URL)  # 例外が発生しなければ成功


def test_validate_webhook_url_rejects_invalid_url():
    """Discord以外のドメインなど不正な形式のURLはValueErrorになる。"""
    with pytest.raises(ValueError):
        config.validate_webhook_url(_INVALID_URL)


def test_load_webhook_config_returns_channel_url_dict(monkeypatch):
    """DISCORD_WEBHOOK_プレフィックスの環境変数から{チャンネル名: URL}が得られる。"""
    # 2チャンネル分のWebhook URLを設定する
    monkeypatch.setenv("DISCORD_WEBHOOK_GENERAL", _VALID_URL)
    monkeypatch.setenv("DISCORD_WEBHOOK_ALERT", _VALID_URL)

    result = config.load_webhook_config()

    # チャンネル名が小文字化された対応表が返ることを確認する
    assert result == {"general": _VALID_URL, "alert": _VALID_URL}


def test_load_webhook_config_raises_when_no_webhooks_configured():
    """DISCORD_WEBHOOK_で始まる環境変数が1件もなければValueErrorになる。"""
    # フィクスチャで全件除去済みの状態で読み込むとValueErrorになることを確認する
    with pytest.raises(ValueError):
        config.load_webhook_config()


def test_load_webhook_config_skips_empty_values(monkeypatch, caplog):
    """値が空(空白のみを含む)のキーは読み飛ばされ、設定済みのチャンネルのみが返る。"""
    # 設定済み1件と、空値・空白のみのキーを用意する
    monkeypatch.setenv("DISCORD_WEBHOOK_NEWS", _VALID_URL)
    monkeypatch.setenv("DISCORD_WEBHOOK_FX", "")
    monkeypatch.setenv("DISCORD_WEBHOOK_ALERT", "   ")

    with caplog.at_level(logging.WARNING, logger="notification_mcp.config"):
        result = config.load_webhook_config()

    # 空値のキーはエラーにならず、設定済みのチャンネルのみが返ることを確認する
    assert result == {"news": _VALID_URL}

    # 読み飛ばしたチャンネル名が警告ログに記録されることを確認する
    assert "'fx'" in caplog.text
    assert "'alert'" in caplog.text


def test_load_webhook_config_skips_invalid_entries(monkeypatch, caplog):
    """形式不正のURL・不正なチャンネル名は読み飛ばされ、URLの前後の空白は除去される。"""
    # 前後に空白を含む正しいURL、形式不正のURL、不正な形式のチャンネル名を用意する
    monkeypatch.setenv("DISCORD_WEBHOOK_NEWS", f"  {_VALID_URL}  ")
    monkeypatch.setenv("DISCORD_WEBHOOK_FX", _INVALID_URL)
    monkeypatch.setenv("DISCORD_WEBHOOK_", _VALID_URL)
    monkeypatch.setenv("DISCORD_WEBHOOK_MY.CHAN", _VALID_URL)

    with caplog.at_level(logging.WARNING, logger="notification_mcp.config"):
        result = config.load_webhook_config()

    # 正しいチャンネルのみが空白を除いたURLで返ることを確認する
    assert result == {"news": _VALID_URL}

    # 読み飛ばした理由が警告ログに記録され、URL本体は含まれないことを確認する
    assert "'fx'" in caplog.text
    assert "チャンネル名の形式が不正" in caplog.text
    assert "my.chan" not in caplog.text
    assert _INVALID_URL not in caplog.text


def test_load_webhook_config_raises_when_all_entries_skipped(monkeypatch):
    """キーはあっても全件が空値・形式不正で読み飛ばされた場合はValueErrorになる。"""
    # 空値と形式不正のキーのみを設定する
    monkeypatch.setenv("DISCORD_WEBHOOK_NEWS", "")
    monkeypatch.setenv("DISCORD_WEBHOOK_FX", _INVALID_URL)

    # 使用できる設定がないためValueErrorになることを確認する
    with pytest.raises(ValueError, match="空・形式不正でないか確認") as exc_info:
        config.load_webhook_config()

    # 例外メッセージにURL本体が含まれないことを確認する
    assert _INVALID_URL not in str(exc_info.value)


def test_load_webhook_config_reflects_dotenv_changes(monkeypatch):
    """.envの内容が変わると次回の読み込みで反映され、OS環境変数が優先される。"""
    # 1回目と2回目で内容が異なる.env(名称変更・追加)を返すようにする
    dotenv_contents = [
        {"DISCORD_WEBHOOK_GENERAL": _VALID_URL},
        {"DISCORD_WEBHOOK_NEWS": _VALID_URL, "DISCORD_WEBHOOK_FX": None},
    ]
    monkeypatch.setattr(config, "dotenv_values", lambda: dotenv_contents.pop(0))

    # 1回目は変更前の.envの内容が読み込まれることを確認する
    assert config.load_webhook_config() == {"general": _VALID_URL}

    # OS環境変数にも同じキーを設定し、OS環境変数が優先されるかを確認する
    os_url = "https://discord.com/api/webhooks/987654321098765432/os-token"
    monkeypatch.setenv("DISCORD_WEBHOOK_NEWS", os_url)

    # 2回目は名称変更が反映され、削除されたgeneralと値のないfxは含まれないことを確認する
    assert config.load_webhook_config() == {"news": os_url}


def test_load_webhook_config_accepts_lowercase_dotenv_keys(monkeypatch):
    """.envのキーが小文字で書かれていても、Webhookの設定として読み込まれる。"""
    # 小文字のキーのみを含む.envの内容を返すようにする
    monkeypatch.setattr(
        config, "dotenv_values", lambda: {"discord_webhook_news": _VALID_URL}
    )

    # 小文字のキーもチャンネルとして読み込まれることを確認する
    assert config.load_webhook_config() == {"news": _VALID_URL}


def test_load_webhook_config_exports_non_webhook_settings(monkeypatch):
    """.envのWebhook以外の設定は既存値を上書きせず環境変数へ反映され、Webhookは反映されない。"""
    # 終了時に元の状態へ戻るよう、検証用の環境変数を登録してから取り除く
    monkeypatch.setenv("NOTIFICATION_MCP_TEST_NEW", "placeholder")
    monkeypatch.delenv("NOTIFICATION_MCP_TEST_NEW")
    monkeypatch.setenv("NOTIFICATION_MCP_TEST_EXISTING", "os-value")

    # Webhook以外の新規・既存の設定とWebhookの設定を含む.envの内容を返すようにする
    dotenv_content = {
        "NOTIFICATION_MCP_TEST_NEW": "dotenv-value",
        "NOTIFICATION_MCP_TEST_EXISTING": "dotenv-value",
        "DISCORD_WEBHOOK_NEWS": _VALID_URL,
    }
    monkeypatch.setattr(config, "dotenv_values", lambda: dotenv_content)

    config.load_webhook_config()

    # 新規の設定は反映され、既存の環境変数は上書きされないことを確認する
    assert os.environ["NOTIFICATION_MCP_TEST_NEW"] == "dotenv-value"
    assert os.environ["NOTIFICATION_MCP_TEST_EXISTING"] == "os-value"

    # Webhookの設定は環境変数へ反映されないことを確認する
    assert "DISCORD_WEBHOOK_NEWS" not in os.environ


@pytest.mark.parametrize(
    "url",
    [
        "https://discord.com/api/webhooks/123456789012345678/abc'secret",
        'https://discord.com/api/webhooks/123456789012345678/abc"secret',
        "https://discord.com/api/webhooks/123456789012345678/abc token",
    ],
)
def test_validate_webhook_url_rejects_unsafe_token(url):
    """トークンに引用符・空白等を含むURLは、伏せ字漏れを防ぐため不正と判定される。"""
    # URLセーフでない文字を含むトークンはValueErrorになることを確認する
    with pytest.raises(ValueError):
        config.validate_webhook_url(url)

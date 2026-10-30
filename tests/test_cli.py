"""cli.pyのユニットテスト。"""

from notification_mcp import cli
from notification_mcp.exceptions import SendFailedError


def test_parse_args_returns_channel_and_message():
    """--channelと--messageが解析結果の属性として取得できる。"""
    # '-'で始まる本文も--message=形式で渡せることを含めて解析する
    args = cli.parse_args(["--channel", "general", "--message=--- 完了 ---"])

    # 指定した値がそのまま取得できることを確認する
    assert args.channel == "general"
    assert args.message == "--- 完了 ---"


def test_main_returns_zero_on_success(monkeypatch):
    """送信に成功した場合、終了コード0を返し、引数の値でnotifyが呼ばれる。"""
    # ログ初期化をno-op化し、送信処理をモック化して呼び出し内容を記録する
    monkeypatch.setattr(cli, "setup_logging", lambda: None)
    calls: list[tuple[str, str]] = []

    async def fake_notify(channel: str, message: str) -> None:
        calls.append((channel, message))

    monkeypatch.setattr(cli, "notify", fake_notify)

    # CLIを実行する
    exit_code = cli.main(["--channel", "general", "--message", "test"])

    # 終了コード0が返り、指定した値で送信されたことを確認する
    assert exit_code == 0
    assert calls == [("general", "test")]


def test_main_returns_one_on_failure(monkeypatch):
    """送信に失敗した場合、例外を送出せず終了コード1を返す。"""
    # ログ初期化をno-op化し、送信失敗を模した例外を送出させる
    monkeypatch.setattr(cli, "setup_logging", lambda: None)

    async def fake_notify(channel: str, message: str) -> None:
        raise SendFailedError("'general' への送信に失敗しました(HTTPステータス: 404)")

    monkeypatch.setattr(cli, "notify", fake_notify)

    # CLIを実行する
    exit_code = cli.main(["--channel", "general", "--message", "test"])

    # 終了コード1が返ることを確認する
    assert exit_code == 1

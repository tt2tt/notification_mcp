"""cli.pyのユニットテスト。"""

from notification_mcp import cli


def test_parse_args_returns_channel_and_message():
    """--channelと--messageが解析結果の属性として取得できる。"""
    # '-'で始まる本文も--message=形式で渡せることを含めて解析する
    args = cli.parse_args(["--channel", "general", "--message=--- 完了 ---"])

    # 指定した値がそのまま取得できることを確認する
    assert args.channel == "general"
    assert args.message == "--- 完了 ---"

"""コマンドラインから通知を送信するためのエントリポイント。

使用例:
    python -m notification_mcp.cli --channel general --message "処理が完了しました"
"""

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """コマンドライン引数を解析する。

    Args:
        argv: 解析する引数のリスト。`None`の場合は`sys.argv[1:]`を解析する。

    Returns:
        `channel`と`message`を属性に持つ解析結果。
    """
    # 送信先チャンネルとメッセージ本文をいずれも必須引数として定義する
    parser = argparse.ArgumentParser(
        prog="python -m notification_mcp.cli",
        description="Discord Webhookへ指定チャンネル宛にテキスト通知を送信する。",
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="送信先のチャンネル名(.envのDISCORD_WEBHOOK_<チャンネル名>に対応)",
    )
    parser.add_argument(
        "--message",
        required=True,
        help="送信するメッセージ本文(2000文字以内)",
    )

    # 引数を解析して返す(不正な引数の場合はargparseが使い方を表示して終了する)
    return parser.parse_args(argv)

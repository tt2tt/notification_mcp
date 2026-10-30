"""コマンドラインから通知を送信するためのエントリポイント。

使用例:
    python -m notification_mcp.cli --channel news --message "処理が完了しました"

終了コードは成功時0、送信失敗時1、引数不正時2(argparseの仕様)となる。
"""

import argparse
import asyncio
import sys

from notification_mcp.error_handlers import return_exit_code
from notification_mcp.logging_config import setup_logging
from notification_mcp.notifier import notify


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
        help=(
            "送信するメッセージ本文(2000文字以内)。"
            "'-'で始まる本文は --message=\"-本文\" の形式で指定する"
        ),
    )

    # 引数を解析して返す(不正な引数の場合はargparseが使い方を表示して終了する)
    return parser.parse_args(argv)


@return_exit_code
def main(argv: list[str] | None = None) -> int:
    """CLIのメイン処理。引数で指定されたチャンネルへ通知を送信する。

    Args:
        argv: コマンドライン引数のリスト。`None`の場合は`sys.argv[1:]`を使用する。

    Returns:
        終了コード。成功時は0、失敗時はデコレータにより1が返る。
    """
    # 引数を先に解析し、--help等で終了する場合はログファイルを作成しない
    args = parse_args(argv)

    # ログを標準エラー出力とログファイルへ出力するよう初期化する
    setup_logging()

    # サービス層で通知を送信する(失敗時の例外はデコレータで終了コードへ変換される)
    coroutine = notify(args.channel, args.message)
    asyncio.run(coroutine)

    # 送信成功を表す終了コードを返す
    return 0


if __name__ == "__main__":
    # 終了コードを呼び出し元(シェル・バッチ等)へ返す
    exit_code = main()
    sys.exit(exit_code)

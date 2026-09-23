"""MCPサーバーのエントリポイント。"""

from mcp.server.mcpserver import MCPServer

from notification_mcp.logging_config import setup_logging
from notification_mcp.tools import send_notification


def main() -> None:
    """MCPサーバーを初期化し、ツールを登録してstdioで起動する。"""
    # ロギングをツール登録・起動より先に初期化する
    setup_logging()

    # MCPサーバーを作成し、通知送信ツールを登録する
    server = MCPServer(name="notification-mcp")
    server.add_tool(
        send_notification,
        description="Discord Webhookへ指定チャンネル宛にテキスト通知を送信する。",
    )

    # stdioトランスポートでサーバーを起動する(サブプロセスとして呼び出される想定)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

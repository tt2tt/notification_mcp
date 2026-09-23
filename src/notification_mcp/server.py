"""MCPサーバーのエントリポイント。"""

from mcp.server.mcpserver import MCPServer

from notification_mcp.tools import send_notification


def main() -> None:
    """MCPサーバーを初期化し、ツールを登録してstdioで起動する。"""
    server = MCPServer(name="notification-mcp")
    server.add_tool(
        send_notification,
        description="Discord Webhookへ指定チャンネル宛にテキスト通知を送信する。",
    )
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

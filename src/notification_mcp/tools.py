"""MCPツールとして公開する処理をまとめたモジュール。"""

from notification_mcp.error_handlers import return_error_message
from notification_mcp.notifier import notify


@return_error_message
async def send_notification(channel: str, message: str) -> str:
    """指定チャンネルのWebhookへ通知を送信するMCPツール本体。

    Args:
        channel: 送信先のチャンネル名。
        message: 送信するメッセージ本文。

    Returns:
        送信結果メッセージ。失敗時はデコレータにより`"エラー: ..."`形式の文字列が返る。
    """
    # サービス層で送信し、成功時の結果メッセージをAIへ返す
    await notify(channel, message)
    return f"'{channel}' へ通知を送信しました。"

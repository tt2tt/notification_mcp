"""通知処理で発生する例外を定義するモジュール。

例外メッセージは利用者へそのまま表示するため日本語で記述し、
Webhook URL等の機密情報は含めない。
"""

import logging


class NotificationError(Exception):
    """通知処理で発生したエラーの基底クラス。

    Attributes:
        log_level: 境界層(MCPツール・CLI)でログ出力する際のログレベル。
    """

    log_level: int = logging.ERROR


class WebhookConfigError(NotificationError):
    """Webhook設定の読み込み・検証に失敗したことを表す例外。"""


class ChannelNotConfiguredError(NotificationError):
    """指定されたチャンネルのWebhook URLが設定されていないことを表す例外。"""

    # 利用者の指定ミスであり、システム異常ではないため警告扱いとする
    log_level: int = logging.WARNING


class MessageRejectedError(NotificationError):
    """メッセージが送信条件(文字数上限等)を満たさず送信を中止したことを表す例外。"""

    # 利用者の入力ミスであり、システム異常ではないため警告扱いとする
    log_level: int = logging.WARNING


class SendFailedError(NotificationError):
    """Webhookへの送信に失敗したことを表す例外(HTTPエラー・通信エラー)。"""

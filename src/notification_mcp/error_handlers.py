"""例外処理を共通化するデコレータをまとめたモジュール。"""

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Concatenate, ParamSpec, TypeVar

import httpx

from notification_mcp.exceptions import (
    MessageRejectedError,
    NotificationError,
    SendFailedError,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def reraise_as(
    target: type[NotificationError], *sources: type[Exception]
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """指定した例外を`target`の例外へ変換して再送出するデコレータを生成する。

    Args:
        target: 変換後に送出する例外クラス。
        *sources: 変換対象とする例外クラス。

    Returns:
        同期関数に適用するデコレータ。
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # 指定された例外のみ捕捉し、メッセージを引き継いでtargetへ変換する
            # (元例外をトレースバックへ出さないよう例外連鎖は切る)
            try:
                return func(*args, **kwargs)
            except sources as error:
                message = str(error)
                raise target(message) from None

        # 例外変換処理を付与した関数を返す
        return wrapper

    # 引数で指定した例外を変換するデコレータを返す
    return decorator


def translate_send_errors(
    func: Callable[Concatenate[str, P], Awaitable[None]],
) -> Callable[Concatenate[str, P], Awaitable[None]]:
    """送信関数で発生した例外を、チャンネル名入りの通知例外へ変換するデコレータ。

    適用する関数は第1引数にチャンネル名を受け取る必要がある。
    `httpx`の例外メッセージにはWebhook URLが含まれるため、
    変換後のメッセージには含めず、トレースバック経由の漏洩を防ぐため例外連鎖も切る。

    Args:
        func: 第1引数にチャンネル名を受け取る非同期の送信関数。

    Returns:
        例外変換処理を付与した非同期関数。

    Raises:
        SendFailedError: HTTPエラーまたは通信エラーで送信に失敗した場合。
        MessageRejectedError: メッセージが送信条件を満たさなかった場合。
    """

    @functools.wraps(func)
    async def wrapper(channel: str, *args: P.args, **kwargs: P.kwargs) -> None:
        try:
            await func(channel, *args, **kwargs)
        except httpx.HTTPStatusError as error:
            # ステータスコードのみを利用者向けメッセージに含める
            status_code = error.response.status_code
            raise SendFailedError(
                f"'{channel}' への送信に失敗しました(HTTPステータス: {status_code})"
            ) from None
        except httpx.HTTPError:
            # 接続エラー・タイムアウト等はURLを含めず通信エラーとしてまとめる
            raise SendFailedError(
                f"'{channel}' への送信に失敗しました(通信エラー)"
            ) from None
        except httpx.InvalidURL:
            # HTTPErrorを継承しないURL解析エラーも、URLを含めず送信失敗として扱う
            raise SendFailedError(
                f"'{channel}' への送信に失敗しました(Webhook URLの形式が不正です)"
            ) from None
        except ValueError as error:
            # 文字数超過等、送信前に検出した入力エラーはメッセージを引き継ぐ
            message = str(error)
            raise MessageRejectedError(message) from None

    # 例外変換処理を付与した送信関数を返す
    return wrapper


def _log_failure(error: Exception) -> None:
    """境界層で捕捉した例外をログ出力する。

    `NotificationError`は例外ごとのログレベルでメッセージを記録する。
    想定外の例外はメッセージにWebhook URLを含み得るため、型名のみを記録する。

    Args:
        error: 境界層で捕捉した例外。
    """
    # 通知例外はURLを含まないメッセージのため、そのまま記録する
    if isinstance(error, NotificationError):
        logger.log(error.log_level, "通知処理に失敗しました: %s", error)
        return

    # 想定外の例外は内容を出さず、型名のみ記録する
    error_type = type(error).__name__
    logger.error("通知処理で想定外のエラーが発生しました: %s", error_type)


def return_error_message(
    func: Callable[P, Awaitable[str]],
) -> Callable[P, Awaitable[str]]:
    """`NotificationError`をログ出力し、エラーメッセージ文字列として返すデコレータ。

    MCPツールは例外ではなく結果文字列をAIへ返すため、境界層で例外を文字列へ変換する。
    想定外の例外はメッセージにWebhook URLを含み得るため、
    型名のみを記録し汎用メッセージを返す。

    Args:
        func: 結果メッセージを返す非同期のMCPツール関数。

    Returns:
        例外を`"エラー: ..."`形式の文字列へ変換する非同期関数。
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        try:
            return await func(*args, **kwargs)
        except NotificationError as error:
            # 失敗を記録し、URLを含まない通知例外のメッセージをAIへ返す
            _log_failure(error)
            return f"エラー: {error}"
        except Exception as error:
            # 想定外の例外は内容を出さず、汎用メッセージを返す
            _log_failure(error)
            return "エラー: 通知処理で想定外のエラーが発生しました。"

    # 例外を結果メッセージへ変換する関数を返す
    return wrapper

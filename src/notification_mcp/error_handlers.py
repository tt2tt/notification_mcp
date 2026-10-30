"""例外処理を共通化するデコレータをまとめたモジュール。"""

import functools
from collections.abc import Awaitable, Callable
from typing import Concatenate, ParamSpec, TypeVar

import httpx

from notification_mcp.exceptions import (
    MessageRejectedError,
    NotificationError,
    SendFailedError,
)

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
            try:
                return func(*args, **kwargs)
            except sources as error:
                message = str(error)
                raise target(message) from error

        return wrapper

    return decorator


def translate_send_errors(
    func: Callable[Concatenate[str, P], Awaitable[None]],
) -> Callable[Concatenate[str, P], Awaitable[None]]:
    """送信関数で発生した例外を、チャンネル名入りの通知例外へ変換するデコレータ。

    適用する関数は第1引数にチャンネル名を受け取る必要がある。
    `httpx`の例外メッセージにはWebhook URLが含まれるため、
    変換後のメッセージには含めない。

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
            ) from error
        except httpx.HTTPError as error:
            # 接続エラー・タイムアウト等はURLを含めず通信エラーとしてまとめる
            raise SendFailedError(
                f"'{channel}' への送信に失敗しました(通信エラー)"
            ) from error
        except ValueError as error:
            # 文字数超過等、送信前に検出した入力エラーはメッセージを引き継ぐ
            message = str(error)
            raise MessageRejectedError(message) from error

    return wrapper

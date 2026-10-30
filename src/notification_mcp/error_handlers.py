"""例外処理を共通化するデコレータをまとめたモジュール。"""

import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from notification_mcp.exceptions import NotificationError

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

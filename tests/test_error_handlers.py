"""error_handlers.pyのユニットテスト。"""

import pytest

from notification_mcp.error_handlers import (
    reraise_as,
)
from notification_mcp.exceptions import (
    WebhookConfigError,
)


def test_reraise_as_converts_exception():
    """指定した例外がメッセージを引き継いだtargetの例外へ変換され、連鎖は切られる。"""

    # ValueErrorを送出する関数にデコレータを適用する
    @reraise_as(WebhookConfigError, ValueError)
    def load() -> None:
        raise ValueError("設定がありません")

    # WebhookConfigErrorへ変換されることを確認する
    with pytest.raises(WebhookConfigError) as exc_info:
        load()

    # メッセージが引き継がれ、元例外がトレースバックに表示されないことを確認する
    assert str(exc_info.value) == "設定がありません"
    assert exc_info.value.__suppress_context__

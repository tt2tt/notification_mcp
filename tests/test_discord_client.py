"""discord_client.pyのユニットテスト。"""

import json

import httpx
import pytest
import respx

from notification_mcp.discord_client import (
    send_webhook_message,
    send_webhook_message_with_retry,
)

_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789012345678/dummy-token"


@respx.mock
async def test_send_webhook_message_posts_content_successfully():
    """正常系ではWebhookへcontentがJSON POSTされる。"""
    route = respx.post(_WEBHOOK_URL).mock(return_value=httpx.Response(204))

    await send_webhook_message(_WEBHOOK_URL, "テストメッセージ")

    assert route.called
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body == {"content": "テストメッセージ"}


async def test_send_webhook_message_raises_when_message_too_long():
    """2000文字を超えるメッセージはHTTPリクエストを送らずValueErrorになる。"""
    with pytest.raises(ValueError):
        await send_webhook_message(_WEBHOOK_URL, "あ" * 2001)


@respx.mock
async def test_send_webhook_message_with_retry_succeeds_after_retryable_error():
    """429応答の後に成功すれば、最終的に成功扱いになる。"""
    route = respx.post(_WEBHOOK_URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(204),
        ]
    )

    await send_webhook_message_with_retry(_WEBHOOK_URL, "リトライ確認", max_retries=2)

    assert route.call_count == 2


@respx.mock
async def test_send_webhook_message_with_retry_raises_on_non_retryable_error():
    """400等リトライ対象外のエラーは即座に例外が伝播し、リトライされない。"""
    route = respx.post(_WEBHOOK_URL).mock(return_value=httpx.Response(400))

    with pytest.raises(httpx.HTTPStatusError):
        await send_webhook_message_with_retry(_WEBHOOK_URL, "test", max_retries=2)

    assert route.call_count == 1


@respx.mock
async def test_send_webhook_message_with_retry_raises_after_max_retries():
    """リトライ対象のエラーが続く場合、上限到達後に例外が送出される。"""
    route = respx.post(_WEBHOOK_URL).mock(
        return_value=httpx.Response(503, headers={"Retry-After": "0"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await send_webhook_message_with_retry(_WEBHOOK_URL, "test", max_retries=2)

    # 初回 + リトライ2回 = 合計3回試行する
    assert route.call_count == 3

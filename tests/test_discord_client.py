"""discord_client.pyのユニットテスト。"""

import asyncio
import json
import logging

import httpx
import pytest
import respx

from notification_mcp.discord_client import (
    _WebhookUrlRedactingFilter,
    send_webhook_message,
    send_webhook_message_with_retry,
)

_WEBHOOK_URL = "https://discord.com/api/webhooks/123456789012345678/dummy-token"


@respx.mock
async def test_send_webhook_message_posts_content_successfully():
    """正常系ではWebhookへcontentとメンション無効化設定がJSON POSTされる。"""
    route = respx.post(_WEBHOOK_URL).mock(return_value=httpx.Response(204))

    await send_webhook_message(_WEBHOOK_URL, "テストメッセージ")

    assert route.called
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body == {
        "content": "テストメッセージ",
        "allowed_mentions": {"parse": ["users", "roles"]},
    }


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


@respx.mock
async def test_send_webhook_message_with_retry_gives_up_when_retry_after_too_long(
    monkeypatch,
):
    """Retry-Afterが待機上限を超える場合、待機・リトライせず即座に例外が送出される。"""
    # 上限判定が壊れた場合にテストが長時間止まらないよう、待機処理を記録のみに置き換える
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # 上限(60秒)を超えるRetry-Afterを返す429応答を用意する
    response = httpx.Response(429, headers={"Retry-After": "300"})
    route = respx.post(_WEBHOOK_URL)
    route.mock(return_value=response)

    # リトライせずにHTTPStatusErrorが送出されることを確認する
    with pytest.raises(httpx.HTTPStatusError):
        await send_webhook_message_with_retry(_WEBHOOK_URL, "test", max_retries=3)

    # 待機せず、初回の1回のみ送信した(早すぎる再送をしていない)ことを確認する
    assert sleeps == []
    assert route.call_count == 1


@respx.mock
async def test_httpx_request_log_redacts_webhook_url(caplog):
    """httpxのログをINFOで出力しても、WebhookのID・トークンは伏せ字になる。"""
    # 正常応答を返すようモック化する
    route = respx.post(_WEBHOOK_URL)
    route.mock(return_value=httpx.Response(204))

    # 呼び出し側がhttpxのログをINFOで出力する設定にした状態で送信する
    with caplog.at_level(logging.INFO, logger="httpx"):
        await send_webhook_message(_WEBHOOK_URL, "ログ確認")

    # リクエストログは出力されるが、ID・トークンは含まれないことを確認する
    assert "/api/webhooks/***" in caplog.text
    assert "123456789012345678" not in caplog.text
    assert "dummy-token" not in caplog.text


@pytest.mark.parametrize(
    "url",
    [
        "https://discord.com/api/v10/webhooks/123456789012345678/dummy-token",
        "https://discord.com/api/webhooks/123456789012345678/dummy-token?wait=true",
    ],
)
def test_redacting_filter_redacts_versioned_webhook_url(url):
    """バージョン付き・クエリ付きのURLも伏せ字になり、URLを含まないレコードは変わらない。"""
    redacting_filter = _WebhookUrlRedactingFilter()

    # Webhook URLを引数に含むレコードを伏せ字にする
    url_record = logging.LogRecord(
        "httpx", logging.INFO, __file__, 0, "HTTP Request: POST %s", (url,), None
    )
    redacting_filter.filter(url_record)
    redacted_message = url_record.getMessage()

    # ID・トークンが取り除かれ、パスの接頭辞は残ることを確認する
    assert "webhooks/***" in redacted_message
    assert "123456789012345678" not in redacted_message
    assert "dummy-token" not in redacted_message

    # Webhook URLを含まないレコードはmsg・argsとも変更されないことを確認する
    other_record = logging.LogRecord(
        "httpx", logging.INFO, __file__, 0, "接続数: %d", (3,), None
    )
    redacting_filter.filter(other_record)
    assert other_record.msg == "接続数: %d"
    assert other_record.args == (3,)

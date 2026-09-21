"""News WebSocket channel — a separate connection from market data.

See docs/specs/2026-08-15-sdk-contract-fix-design.md §4.

Note: news **pushes** could not be captured — the audit key has no news
entitlement, so the gateway rejects the handshake with HTTP 401. That 401 path
is exactly what these tests pin down; the push assertions below only cover
envelope unwrapping, using the field names the protocol documents.
"""

import json

import pytest
from unittest.mock import AsyncMock

from infoway._types import WsCode
from infoway.exceptions import InfowayAuthError
from infoway.ws.news import InfowayNewsWebSocket


@pytest.fixture
def news():
    return InfowayNewsWebSocket(api_key="test-key")


# --------------------------------------------------------------------------
# URL — /news?apikey=..., NOT /ws?business=...
# --------------------------------------------------------------------------

def test_news_url_has_no_business_param(news):
    assert news._url == "wss://data.infoway.io/news?apikey=test-key"
    assert "business=" not in news._url
    assert "/ws?" not in news._url


# --------------------------------------------------------------------------
# subscribe frame — 10020 with a language
# --------------------------------------------------------------------------

def test_build_subscribe_message(news):
    parsed = json.loads(news._build_subscribe_message("en"))
    assert parsed["code"] == 10020
    assert parsed["data"] == {"lang": "en"}
    assert "trace" in parsed


async def test_subscribe_sends_10020(news):
    news._ws = AsyncMock()
    await news.subscribe("zh-Hans")
    sent = json.loads(news._ws.send.call_args.args[0])
    assert sent["code"] == WsCode.SUB_NEWS
    assert sent["data"]["lang"] == "zh-Hans"
    assert news._lang == "zh-Hans"


def test_rejects_unsupported_language(news):
    with pytest.raises(ValueError):
        news._build_subscribe_message("klingon")


# --------------------------------------------------------------------------
# frame dispatch
# --------------------------------------------------------------------------

async def test_welcome_frame_is_not_an_error(news):
    news.on_error = AsyncMock()
    news.on_news = AsyncMock()
    await news._dispatch('{"code":200,"msg":"ws connect success"}')
    news.on_error.assert_not_awaited()
    news.on_news.assert_not_awaited()


async def test_non_json_frame_is_skipped(news):
    news.on_error = AsyncMock()
    news.on_news = AsyncMock()
    await news._dispatch("You have permission to subscribe to all market data")
    news.on_error.assert_not_awaited()
    news.on_news.assert_not_awaited()


async def test_ack_10021_does_not_reach_on_news(news):
    news.on_news = AsyncMock()
    await news._dispatch('{"code":10021,"trace":"t","msg":"ok","data":{"lang":"en"}}')
    news.on_news.assert_not_awaited()


async def test_push_10022_is_unwrapped_to_data(news):
    news.on_news = AsyncMock()
    await news._dispatch(json.dumps({
        "code": 10022,
        "data": {
            "dk": "1f0c1c5e", "country": "US", "lang": "en", "route": "US|en",
            "title": "Apple announces buyback", "published": 1786775220,
            "urgency": 2, "provider": "Reuters", "symbols": ["AAPL.US"],
            "link": "https://example.com/a", "content": "...", "sd": "summary",
        },
    }))
    payload = news.on_news.call_args.args[0]
    assert "code" not in payload
    assert payload["dk"] == "1f0c1c5e"
    assert payload["symbols"] == ["AAPL.US"]
    assert payload["published"] == 1786775220  # seconds, untouched when parse=False


async def test_push_10022_published_is_parsed_when_requested():
    from datetime import datetime, timezone

    w = InfowayNewsWebSocket(api_key="k", parse=True)
    w.on_news = AsyncMock()
    await w._dispatch(json.dumps({"code": 10022, "data": {"dk": "x", "published": 1786775220}}))
    payload = w.on_news.call_args.args[0]
    assert payload["published"] == datetime.fromtimestamp(1786775220, tz=timezone.utc)


async def test_on_news_parsed(news):
    news.on_news_parsed = AsyncMock()
    await news._dispatch(json.dumps({
        "code": 10022,
        "data": {"dk": "x", "title": "T", "published": 1786775220},
    }))
    news.on_news_parsed.assert_awaited()


async def test_unsubscribe_sends_11020(news):
    news._ws = AsyncMock()
    await news.unsubscribe()
    sent = json.loads(news._ws.send.call_args.args[0])
    assert sent["code"] == WsCode.UNSUB_NEWS


async def test_permission_error_frame_reaches_on_error(news):
    """519 = 'no news permission' delivered as a frame rather than a handshake reject."""
    news.on_error = AsyncMock()
    await news._dispatch('{"code":519,"msg":"no news permission"}')
    news.on_error.assert_awaited()


# --------------------------------------------------------------------------
# handshake 401 → explicit "no news permission", and NO reconnect loop
# --------------------------------------------------------------------------

async def test_handshake_401_raises_explicit_permission_error(monkeypatch):
    from websockets.datastructures import Headers
    from websockets.exceptions import InvalidStatus
    from websockets.http11 import Response

    attempts = []

    def fake_connect(url, **kwargs):
        attempts.append(url)
        raise InvalidStatus(
            Response(401, "Unauthorized", Headers([("www-authenticate", 'apikey realm="key"')]))
        )

    monkeypatch.setattr("infoway.ws.news.websockets.connect", fake_connect)
    w = InfowayNewsWebSocket(api_key="no-news-entitlement")
    with pytest.raises(InfowayAuthError) as exc:
        await w.connect()
    message = str(exc.value).lower()
    assert "news" in message
    assert "permission" in message or "not authorised" in message or "not authorized" in message
    assert len(attempts) == 1, "a 401 must not trigger the reconnect loop"
    assert w._running is False

"""WebSocket client — protocol codes, frame dispatch, handshake auth.

All frames replayed here come from tests/fixtures/ws/*.jsonl, which are verbatim
captures of live sessions against wss://data.infoway.io/ws.
See docs/specs/2026-08-15-sdk-contract-fix-design.md §3.
"""

import json

import pytest
from unittest.mock import AsyncMock

from infoway._types import KlineType, WsCode
from infoway.exceptions import InfowayAuthError
from infoway.ws.client import InfowayWebSocket, join_codes
from tests.conftest import load_text, load_ws_frames


def _frames(name):
    return load_ws_frames(f"ws/{name}")


def _first_push(name, code):
    for raw in _frames(name):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if msg.get("code") == code:
            return raw
    raise AssertionError(f"no code={code} frame in {name}")


@pytest.fixture
def ws():
    return InfowayWebSocket(api_key="test-key", business="crypto")


# --------------------------------------------------------------------------
# URL / message building
# --------------------------------------------------------------------------

def test_build_url():
    w = InfowayWebSocket(api_key="test-key", business="stock")
    assert w._url == "wss://data.infoway.io/ws?business=stock&apikey=test-key"


def test_build_subscribe_message():
    w = InfowayWebSocket(api_key="test-key", business="stock")
    parsed = json.loads(w._build_codes_message(WsCode.SUB_TRADE, "AAPL.US,TSLA.US"))
    assert parsed["code"] == 10000
    assert parsed["data"]["codes"] == "AAPL.US,TSLA.US"
    assert "trace" in parsed


def test_build_heartbeat_message():
    w = InfowayWebSocket(api_key="test-key", business="stock")
    parsed = json.loads(w._build_codes_message(WsCode.HEARTBEAT, None))
    assert parsed["code"] == 10010
    assert "data" not in parsed


def test_build_kline_subscribe_message_has_arr_with_type():
    w = InfowayWebSocket(api_key="test-key", business="stock")
    parsed = json.loads(w._build_kline_message(WsCode.SUB_KLINE, "AAPL.US,TSLA.US", KlineType.MIN_5))
    assert parsed["code"] == 10006
    assert parsed["data"]["arr"] == [{"codes": "AAPL.US,TSLA.US", "type": 2}]


def test_wscode_values_match_server():
    assert WsCode.SUB_TRADE == 10000
    assert WsCode.SUB_TRADE_ACK == 10001
    assert WsCode.PUSH_TRADE == 10002
    assert WsCode.SUB_DEPTH == 10003
    assert WsCode.SUB_DEPTH_ACK == 10004
    assert WsCode.PUSH_DEPTH == 10005
    assert WsCode.SUB_KLINE == 10006
    assert WsCode.SUB_KLINE_ACK == 10007
    assert WsCode.PUSH_KLINE == 10008
    assert WsCode.HEARTBEAT == 10010
    assert WsCode.HEART_APPLY == 10011
    assert WsCode.UNSUB_TRADE == 11000
    assert WsCode.UNSUB_DEPTH == 11001
    assert WsCode.UNSUB_KLINE == 11002
    assert WsCode.UNSUB_ACK == 11010
    assert WsCode.SUB_NEWS == 10020
    assert WsCode.SUB_NEWS_ACK == 10021
    assert WsCode.PUSH_NEWS == 10022


# --------------------------------------------------------------------------
# §3.5 unsubscribe_kline must carry klineTypes
# --------------------------------------------------------------------------

def test_build_kline_unsubscribe_message_carries_kline_types():
    """Without klineTypes the server drops EVERY interval for those codes."""
    w = InfowayWebSocket(api_key="test-key", business="crypto")
    parsed = json.loads(
        w._build_kline_unsub_message(WsCode.UNSUB_KLINE, "BTCUSDT", KlineType.DAY)
    )
    assert parsed["code"] == 11002
    assert parsed["data"]["codes"] == "BTCUSDT"
    assert parsed["data"]["klineTypes"] == "8"


async def test_unsubscribe_kline_sends_kline_types():
    w = InfowayWebSocket(api_key="test-key", business="crypto")
    w._ws = AsyncMock()
    await w.subscribe_kline("BTCUSDT", KlineType.DAY)
    await w.unsubscribe_kline("BTCUSDT", KlineType.DAY)
    sent = json.loads(w._ws.send.call_args_list[-1].args[0])
    assert sent["code"] == 11002
    assert sent["data"]["klineTypes"] == "8"
    assert ("kline", "BTCUSDT", 8) not in w._subscriptions


# --------------------------------------------------------------------------
# §3.8 codes must be merged into one comma-joined message
# --------------------------------------------------------------------------

async def test_subscribe_accepts_iterable_and_merges_into_one_frame():
    w = InfowayWebSocket(api_key="test-key", business="crypto")
    w._ws = AsyncMock()
    await w.subscribe_trade(["BTCUSDT", "ETHUSDT"])
    assert w._ws.send.call_count == 1
    sent = json.loads(w._ws.send.call_args.args[0])
    assert sent["data"]["codes"] == "BTCUSDT,ETHUSDT"


def test_join_codes():
    assert join_codes("BTCUSDT,ETHUSDT") == "BTCUSDT,ETHUSDT"
    assert join_codes(["BTCUSDT", " ETHUSDT "]) == "BTCUSDT,ETHUSDT"
    assert join_codes(("AAPL.US",)) == "AAPL.US"


# --------------------------------------------------------------------------
# §3.1 non-JSON greeting frame must not blow up
# --------------------------------------------------------------------------

async def test_dispatch_skips_plaintext_permission_frame(ws):
    raw = _frames("stock_trade_closed.jsonl")[0]
    assert raw == "You have permission to subscribe to all market data"
    ws.on_trade = AsyncMock()
    ws.on_error = AsyncMock()
    await ws._dispatch(raw)  # must not raise
    ws.on_trade.assert_not_awaited()
    ws.on_error.assert_not_awaited()


# --------------------------------------------------------------------------
# §3.2 welcome frame is not an error
# --------------------------------------------------------------------------

async def test_dispatch_welcome_frame_is_not_an_error(ws):
    raw = '{"code":200,"msg":"ws connect success"}'
    assert raw in _frames("crypto_trade.jsonl")
    ws.on_error = AsyncMock()
    ws.on_trade = AsyncMock()
    await ws._dispatch(raw)
    ws.on_error.assert_not_awaited()
    ws.on_trade.assert_not_awaited()


# --------------------------------------------------------------------------
# §3.4 callbacks receive msg["data"], aligned with the REST layer
# --------------------------------------------------------------------------

async def test_trade_callback_receives_unwrapped_data(ws):
    raw = _first_push("crypto_trade.jsonl", WsCode.PUSH_TRADE)
    ws.on_trade = AsyncMock()
    await ws._dispatch(raw)
    payload = ws.on_trade.call_args.args[0]
    assert "code" not in payload, "callbacks must get msg['data'], not the envelope"
    assert payload["s"] == "BTCUSDT"
    assert payload["p"] == "63039"
    assert payload["v"] == "0.07933"
    assert payload["td"] == 1
    assert isinstance(payload["t"], int)


async def test_depth_callback_receives_unwrapped_data(ws):
    raw = _first_push("crypto_depth.jsonl", WsCode.PUSH_DEPTH)
    ws.on_depth = AsyncMock()
    await ws._dispatch(raw)
    payload = ws.on_depth.call_args.args[0]
    assert "code" not in payload
    assert payload["s"] == "BTCUSDT"
    # real keys are a/b, column-major [[prices],[qtys]] — never asks/bids
    assert "asks" not in payload and "bids" not in payload
    assert payload["a"][0][0] == "63039.00000000"
    assert payload["b"][0][0] == "63038.99000000"


async def test_kline_callback_receives_unwrapped_data_with_ty(ws):
    raw = _first_push("crypto_kline.jsonl", WsCode.PUSH_KLINE)
    ws.on_kline = AsyncMock()
    await ws._dispatch(raw)
    payload = ws.on_kline.call_args.args[0]
    assert "code" not in payload
    assert payload["ty"] == 1, "the kline interval must survive unwrapping"
    assert payload["s"] == "BTCUSDT"
    assert payload["c"] == "63039.00000"
    assert payload["pfr"] == "-0.01%"   # WS names it pfr; REST names it pc
    assert payload["t"] == "1786775220"  # kline t is a STRING in SECONDS


async def test_multi_interval_kline_pushes_keep_their_ty(ws):
    seen = []

    async def cb(payload):
        seen.append((payload["s"], payload["ty"]))

    ws.on_kline = cb
    for raw in _frames("probe_multi_kline.jsonl"):
        await ws._dispatch(raw)
    assert ("ETHUSDT", 1) in seen
    assert ("BTCUSDT", 8) in seen


async def test_subscribe_ack_does_not_reach_data_callbacks(ws):
    ws.on_trade = AsyncMock()
    await ws._dispatch('{"code":10001,"trace":"abc","msg":"ok"}')
    ws.on_trade.assert_not_awaited()


async def test_server_error_frames_reach_on_error(ws):
    """507 'Param lost' and 506 'code out of range', replayed from probe_malformed.jsonl."""
    errors = []

    async def cb(exc):
        errors.append(exc)

    ws.on_error = cb
    for raw in _frames("probe_malformed.jsonl"):
        await ws._dispatch(raw)
    assert [e.ret for e in errors] == [507, 506]
    assert errors[0].msg.startswith("Param lost")
    assert errors[0].trace_id == "408e395555214a2e91b596e351b83c97"
    assert errors[0].error_name == "PARAM_LOST"


async def test_ws_508_is_apikey_expired_not_product_missing(ws):
    ws.on_error = AsyncMock()
    await ws._dispatch('{"code":508,"msg":"expired","traceId":"t8"}')
    err = ws.on_error.call_args.args[0]
    assert err.error_name == "APIKEY_EXPIRED"
    assert "[508 APIKEY_EXPIRED]" in str(err)


async def test_heart_apply_is_not_an_error(ws):
    ws.on_error = AsyncMock()
    await ws._dispatch('{"code":10011,"msg":"ok"}')
    ws.on_error.assert_not_awaited()


async def test_subscribe_trade_include_ty():
    w = InfowayWebSocket(api_key="test-key", business="stock")
    w._ws = AsyncMock()
    await w.subscribe_trade("AAPL.US", include_ty=True)
    sent = json.loads(w._ws.send.call_args.args[0])
    assert sent["data"]["includeTy"] is True


def test_ws_reads_env_key(monkeypatch):
    monkeypatch.setenv("INFOWAY_API_KEY", "from-env")
    w = InfowayWebSocket(business="crypto")
    assert "apikey=from-env" in w._url


def test_ws_requires_key(monkeypatch):
    monkeypatch.delenv("INFOWAY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="apiKey"):
        InfowayWebSocket(business="crypto")


async def test_unknown_protocol_code_is_not_reported_as_an_error(ws):
    """Unknown 5-digit protocol codes must not be mistaken for 5xx rejections."""
    ws.on_error = AsyncMock()
    ws.on_trade = AsyncMock()
    await ws._dispatch('{"code":11020,"trace":"t","msg":"ok"}')
    ws.on_error.assert_not_awaited()
    ws.on_trade.assert_not_awaited()


async def test_wrong_business_is_acked_then_silent(ws):
    """§3.7 — subscribing AAPL.US on business=crypto is acked and never pushes."""
    frames = _frames("probe_wrong_business.jsonl")
    codes = [json.loads(f)["code"] for f in frames if f.startswith("{")]
    assert codes == [200, 10001], "server acked the bad subscription and sent no data"
    ws.on_trade = AsyncMock()
    ws.on_error = AsyncMock()
    for raw in frames:
        await ws._dispatch(raw)
    ws.on_trade.assert_not_awaited()
    ws.on_error.assert_not_awaited()


async def test_heartbeat_gets_no_acknowledgement(ws):
    """§3.6 — the server never answers 10010; do not wait for an ack."""
    sent = [
        json.loads(f) for f in load_ws_frames("ws/probe_hb_unsub.jsonl", "send")
    ]
    recv = [
        json.loads(f) for f in load_ws_frames("ws/probe_hb_unsub.jsonl", "recv")
        if f.startswith("{")
    ]
    assert sum(1 for f in sent if f["code"] == WsCode.HEARTBEAT) == 2
    assert not [f for f in recv if f.get("code") == WsCode.HEARTBEAT]
    # the unsubscribe, by contrast, IS acked with 11010
    assert any(f.get("code") == WsCode.UNSUB_ACK for f in recv)


async def test_user_callback_exception_does_not_kill_connection(ws):
    async def boom(_payload):
        raise RuntimeError("user bug")

    ws.on_trade = boom
    await ws._dispatch(_first_push("crypto_trade.jsonl", WsCode.PUSH_TRADE))  # must not raise


# --------------------------------------------------------------------------
# §3.3 handshake 401 → InfowayAuthError, and NO reconnect loop
# --------------------------------------------------------------------------

def test_captured_bad_key_session_shows_a_handshake_level_401():
    """probe_badkey.jsonl: the rejection is HTTP 401 at the handshake, not a WS frame."""
    notes = [
        json.loads(line)["_note"]
        for line in load_text("ws/probe_badkey.jsonl").splitlines()
        if line.strip()
    ]
    assert any("Handshake status 401 Unauthorized" in n for n in notes)
    assert any("www-authenticate" in n and "apikey" in n for n in notes)
    assert not load_ws_frames("ws/probe_badkey.jsonl"), "no data frame is ever delivered"


async def test_handshake_401_raises_auth_error_and_stops_reconnecting(monkeypatch):
    from websockets.datastructures import Headers
    from websockets.exceptions import InvalidStatus
    from websockets.http11 import Response

    attempts = []

    def fake_connect(url, **kwargs):
        attempts.append(url)
        raise InvalidStatus(
            Response(401, "Unauthorized", Headers([("www-authenticate", 'apikey realm="key"')]))
        )

    monkeypatch.setattr("infoway.ws.client.websockets.connect", fake_connect)
    w = InfowayWebSocket(api_key="bad-key", business="crypto")
    with pytest.raises(InfowayAuthError):
        await w.connect()
    assert len(attempts) == 1, "a rejected API key must not be retried"
    assert w._running is False


async def test_on_reconnect_not_fired_on_first_connect(monkeypatch):
    import asyncio
    from contextlib import asynccontextmanager

    class _FakeWS:
        def __init__(self):
            self._q: asyncio.Queue = asyncio.Queue()

        async def send(self, _msg):
            return None

        def __aiter__(self):
            return self

        async def __anext__(self):
            item = await self._q.get()
            if item is StopAsyncIteration:
                raise StopAsyncIteration
            return item

        async def close(self):
            await self._q.put(StopAsyncIteration)

    @asynccontextmanager
    async def fake_connect(*_a, **_k):
        yield _FakeWS()

    monkeypatch.setattr("infoway.ws.client.websockets.connect", fake_connect)
    w = InfowayWebSocket(api_key="k", business="crypto")
    w.on_reconnect = AsyncMock()
    await w.subscribe_trade("BTCUSDT")
    task = asyncio.create_task(w.connect())
    await asyncio.sleep(0.05)
    await w.close()
    await asyncio.wait_for(task, timeout=1)
    w.on_reconnect.assert_not_awaited()


async def test_close_cancels_reconnect_backoff(monkeypatch):
    import asyncio
    from websockets.datastructures import Headers
    from websockets.exceptions import InvalidStatus
    from websockets.http11 import Response

    def fake_connect(url, **kwargs):
        raise InvalidStatus(Response(503, "Service Unavailable", Headers()))

    monkeypatch.setattr("infoway.ws.client.websockets.connect", fake_connect)
    w = InfowayWebSocket(api_key="k", business="crypto")
    w._backoff = 30
    task = asyncio.create_task(w.connect())
    await asyncio.sleep(0.05)
    await w.close()
    await asyncio.wait_for(task, timeout=1)


async def test_handshake_non_401_reconnects_then_gives_up(monkeypatch):
    """A 503 is transient — retry, but honour max_reconnect_attempts (no infinite loop)."""
    import asyncio as _asyncio

    from websockets.datastructures import Headers
    from websockets.exceptions import InvalidStatus
    from websockets.http11 import Response

    attempts = []

    def fake_connect(url, **kwargs):
        attempts.append(url)
        raise InvalidStatus(Response(503, "Service Unavailable", Headers()))

    monkeypatch.setattr("infoway.ws.client.websockets.connect", fake_connect)
    w = InfowayWebSocket(api_key="k", business="crypto", max_reconnect_attempts=2)
    w._backoff = 0  # keep the backoff sleeps instantaneous
    await _asyncio.wait_for(w.connect(), timeout=10)
    assert 2 <= len(attempts) <= 3


# --------------------------------------------------------------------------
# misc
# --------------------------------------------------------------------------

async def test_callbacks_registered(ws):
    handler = AsyncMock()
    ws.on_trade = handler
    assert ws.on_trade is handler


def test_subscription_tracking(ws):
    ws._subscriptions.add(("trade", "AAPL.US", 0))
    ws._subscriptions.add(("depth", "AAPL.US", 0))
    assert len(ws._subscriptions) == 2

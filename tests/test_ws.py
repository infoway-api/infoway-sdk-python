import json
import pytest
from unittest.mock import AsyncMock
from infoway.ws.client import InfowayWebSocket
from infoway._types import KlineType, WsCode


def test_build_url():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    assert ws._url == "wss://data.infoway.io/ws?business=stock&apikey=test-key"


def test_build_url_crypto():
    ws = InfowayWebSocket(api_key="k1", business="crypto")
    assert "business=crypto" in ws._url
    assert "apikey=k1" in ws._url


def test_subscription_tracking():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    ws._subscriptions.add(("trade", "AAPL.US", 0))
    ws._subscriptions.add(("depth", "AAPL.US", 0))
    assert len(ws._subscriptions) == 2


def test_build_subscribe_message():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    msg = ws._build_codes_message(WsCode.SUB_TRADE, "AAPL.US,TSLA.US")
    parsed = json.loads(msg)
    assert parsed["code"] == 10000
    assert parsed["data"]["codes"] == "AAPL.US,TSLA.US"
    assert "trace" in parsed


def test_build_unsubscribe_message():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    msg = ws._build_codes_message(WsCode.UNSUB_TRADE, "AAPL.US")
    parsed = json.loads(msg)
    assert parsed["code"] == 11000  # server-side UNSUB code is 11000, not 10002


def test_build_heartbeat_message():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    msg = ws._build_codes_message(WsCode.HEARTBEAT, None)
    parsed = json.loads(msg)
    assert parsed["code"] == 10010
    assert "data" not in parsed


def test_build_kline_subscribe_message_has_arr_with_type():
    """Kline subscribe must use data.arr=[{codes,type}], not data.codes."""
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    msg = ws._build_kline_message(WsCode.SUB_KLINE, "AAPL.US,TSLA.US", KlineType.MIN_5)
    parsed = json.loads(msg)
    assert parsed["code"] == 10006
    assert parsed["data"]["arr"] == [{"codes": "AAPL.US,TSLA.US", "type": 2}]


def test_wscode_values_match_server():
    """The codes must match what the server actually uses, not the originally-guessed scheme."""
    assert WsCode.SUB_TRADE == 10000
    assert WsCode.SUB_TRADE_ACK == 10001
    assert WsCode.PUSH_TRADE == 10002       # was wrongly 10001
    assert WsCode.SUB_DEPTH == 10003
    assert WsCode.SUB_DEPTH_ACK == 10004
    assert WsCode.PUSH_DEPTH == 10005       # was wrongly 10004
    assert WsCode.SUB_KLINE == 10006
    assert WsCode.SUB_KLINE_ACK == 10007
    assert WsCode.PUSH_KLINE == 10008       # was wrongly 10007
    assert WsCode.HEARTBEAT == 10010
    assert WsCode.UNSUB_TRADE == 11000
    assert WsCode.UNSUB_DEPTH == 11001
    assert WsCode.UNSUB_KLINE == 11002
    assert WsCode.UNSUB_ACK == 11010


@pytest.mark.asyncio
async def test_callbacks_registered():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    handler = AsyncMock()
    ws.on_trade = handler
    assert ws.on_trade is handler

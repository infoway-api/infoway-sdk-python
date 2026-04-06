import json
import pytest
from unittest.mock import AsyncMock
from infoway.ws.client import InfowayWebSocket
from infoway._types import WsCode


def test_build_url():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    assert ws._url == "wss://data.infoway.io/ws?business=stock&apikey=test-key"


def test_build_url_crypto():
    ws = InfowayWebSocket(api_key="k1", business="crypto")
    assert "business=crypto" in ws._url
    assert "apikey=k1" in ws._url


def test_subscription_tracking():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    ws._subscriptions.add(("trade", "AAPL.US"))
    ws._subscriptions.add(("depth", "AAPL.US"))
    assert len(ws._subscriptions) == 2


def test_build_subscribe_message():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    msg = ws._build_message(WsCode.SUB_TRADE, "AAPL.US,TSLA.US")
    parsed = json.loads(msg)
    assert parsed["code"] == 10000
    assert parsed["data"]["codes"] == "AAPL.US,TSLA.US"
    assert "trace" in parsed


def test_build_unsubscribe_message():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    msg = ws._build_message(WsCode.UNSUB_TRADE, "AAPL.US")
    parsed = json.loads(msg)
    assert parsed["code"] == 10002


def test_build_heartbeat_message():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    msg = ws._build_message(WsCode.HEARTBEAT)
    parsed = json.loads(msg)
    assert parsed["code"] == 10010


@pytest.mark.asyncio
async def test_callbacks_registered():
    ws = InfowayWebSocket(api_key="test-key", business="stock")
    handler = AsyncMock()
    ws.on_trade = handler
    assert ws.on_trade is handler

"""Live contract tests — run against the real API to catch server-side drift.

These are **opt-in**: they need a real key and network access, so they are
skipped unless ``INFOWAY_API_KEY`` is set. Run them with::

    INFOWAY_API_KEY=... pytest tests/test_live_contract.py -m live -v

The crypto channel is used wherever possible because it trades 24x7, so the
assertions hold outside equity market hours too.
See docs/specs/2026-08-15-sdk-contract-fix-design.md §6.3.
"""

import asyncio
import os

import pytest

from infoway import InfowayClient, PeriodType, ScheduleType, SymbolType
from infoway.exceptions import InfowayAPIError, InfowayAuthError
from infoway.ws.client import InfowayWebSocket
from infoway.ws.news import InfowayNewsWebSocket

API_KEY = os.getenv("INFOWAY_API_KEY")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not API_KEY, reason="INFOWAY_API_KEY not set — live tests skipped"),
]


@pytest.fixture(scope="module")
def client():
    with InfowayClient(api_key=API_KEY) as c:
        yield c


# --------------------------------------------------------------------------
# REST market data
# --------------------------------------------------------------------------

def test_live_crypto_trade_field_names(client):
    [row] = client.crypto.get_trade("BTCUSDT")
    assert set(row) >= {"s", "t", "p", "v", "vw", "td"}
    assert row["s"] == "BTCUSDT"
    assert isinstance(row["p"], str)
    assert isinstance(row["t"], int)


def test_live_crypto_depth_is_column_major(client):
    [row] = client.crypto.get_depth("BTCUSDT")
    assert "a" in row and "b" in row
    assert "asks" not in row and "bids" not in row
    assert len(row["a"]) == 2 and len(row["a"][0]) == len(row["a"][1])


def test_live_crypto_kline_uses_resplist(client):
    [row] = client.crypto.get_kline("BTCUSDT", kline_type=1, count=2)
    assert "respList" in row and "kline" not in row
    candle = row["respList"][0]
    assert set(candle) >= {"t", "o", "h", "l", "c", "v", "vw", "pc"}
    assert isinstance(candle["t"], str), "kline t is a string of SECONDS"
    assert candle["pc"].endswith("%")


def test_live_crypto_kline_parsed(client):
    from datetime import datetime
    from decimal import Decimal

    candles = client.crypto.get_kline("BTCUSDT", kline_type=1, count=2, parse=True)
    assert len(candles) == 2
    assert all("respList" not in c for c in candles)
    assert isinstance(candles[0]["c"], Decimal)
    assert isinstance(candles[0]["t"], datetime)
    assert isinstance(candles[0]["turnover"], Decimal)


# --------------------------------------------------------------------------
# REST basic.*
# --------------------------------------------------------------------------

def test_live_get_symbols(client):
    result = client.basic.get_symbols("STOCK_US", symbols="AAPL.US")
    assert result[0]["symbol"] == "AAPL.US"
    assert set(result[0]) >= {"symbol", "name_cn", "name_hk", "name_en", "index"}


def test_live_get_symbol_info(client):
    result = client.basic.get_symbol_info("STOCK_US", "AAPL.US")
    assert result[0]["symbol"] == "AAPL.US"
    assert set(result[0]) >= {"market", "exchange", "currency", "lot_size", "total_shares"}


def test_live_get_adjustment_factors(client):
    result = client.basic.get_adjustment_factors("AAPL.US", "US", "20260801", "20260814")
    assert result, "expected at least one adjustment factor row"
    assert set(result[0]) >= {"symbol", "market", "trade_date", "forward_factor"}


def test_live_get_trading_days(client):
    result = client.basic.get_trading_days("US", "20260801", "20260831")
    assert "trade_days" in result and "half_trade_days" in result
    assert all(len(d) == 8 for d in result["trade_days"])  # YYYYMMDD


def test_live_get_trading_schedule(client):
    result = client.basic.get_trading_schedule(type="METAL")
    assert result and all(row["type"] == "METAL" for row in result)
    assert set(result[0]) >= {"symbol", "timezone", "trading_hours", "holidays"}


def test_live_schedule_rejects_equity_type():
    with InfowayClient(api_key=API_KEY) as c:
        with pytest.raises(ValueError, match="ENERGY/FOREX"):
            c.basic.get_trading_schedule_by_type(SymbolType.STOCK_US)
        rows = c.basic.get_trading_schedule_by_type(ScheduleType.ENERGY)
        assert rows is not None


def test_live_korea_taiwan_packages_financial(client):
    kr = client.korea.get_trade("005930.KS")
    assert kr
    tw = client.taiwan.get_trade("2330.TW")
    assert tw
    pkg = client.packages.get_info()
    assert pkg and ("packageName" in pkg or "package_name" in pkg)
    earn = client.financial.get_earning_status("AAPL.US", SymbolType.STOCK_US)
    assert earn is not None
    income = client.financial.get_income_statement("AAPL.US", SymbolType.STOCK_US, PeriodType.FQ)
    assert income is not None
    cats = client.market.get_rank_categories("US")
    assert cats is not None


# --------------------------------------------------------------------------
# error envelopes
# --------------------------------------------------------------------------

def test_live_missing_suffix_raises_not_none(client):
    with pytest.raises(InfowayAPIError) as exc:
        client.stock.get_trade("AAPL")
    assert exc.value.ret == 500


def test_live_bad_symbol_type_raises(client):
    with pytest.raises(InfowayAPIError) as exc:
        client.basic.get_symbols("NOT_A_TYPE")
    assert exc.value.ret in (400, 500)


def test_live_no_data_key_envelope_is_returned(client):
    result = client.plate.get_intro("IN20293.HK")
    assert result is not None
    assert result["plate"] == "IN20293.HK"
    assert result["intro"]


def test_live_bad_key_raises_auth_error():
    with InfowayClient(api_key="not-a-real-key", max_retries=1) as bad:
        with pytest.raises(InfowayAuthError):
            bad.stock.get_trade("AAPL.US")


# --------------------------------------------------------------------------
# WebSocket
# --------------------------------------------------------------------------

async def test_live_ws_crypto_trade_push():
    received: list[dict] = []
    ws = InfowayWebSocket(api_key=API_KEY, business="crypto")

    async def on_trade(payload):
        received.append(payload)

    ws.on_trade = on_trade
    await ws.subscribe_trade("BTCUSDT")
    task = asyncio.create_task(ws.connect())
    try:
        for _ in range(150):
            if received:
                break
            await asyncio.sleep(0.2)
    finally:
        await ws.close()
        task.cancel()

    assert received, "no trade push received within 30s on the 24x7 crypto channel"
    row = received[0]
    assert "code" not in row, "the callback must receive msg['data']"
    assert set(row) >= {"s", "t", "p", "v", "vw"}
    assert row["s"] == "BTCUSDT"


async def test_live_ws_bad_key_raises_auth_error_immediately():
    ws = InfowayWebSocket(api_key="not-a-real-key", business="crypto")
    with pytest.raises(InfowayAuthError):
        await asyncio.wait_for(ws.connect(), timeout=20)


async def test_live_news_channel_permission():
    """401 if the key has no news entitlement; otherwise a handshake is enough."""
    received: list = []
    news = InfowayNewsWebSocket(api_key=API_KEY)

    async def on_news(item):
        received.append(item)

    news.on_news = on_news
    await news.subscribe("en")
    task = asyncio.create_task(news.connect())
    try:
        done, _ = await asyncio.wait({task}, timeout=15)
        if task.done() and task.exception():
            exc = task.exception()
            if isinstance(exc, InfowayAuthError):
                assert "news" in str(exc).lower() or "401" in str(exc)
            else:
                raise exc
    finally:
        await news.close()
        task.cancel()

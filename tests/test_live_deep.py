"""Production deep probe — happy paths, bad params, forged key.

Opt-in::

    INFOWAY_API_KEY=... pytest tests/test_live_deep.py -m live -o addopts= -v
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import pytest

from infoway import (
    InfowayClient,
    InfowayNewsWebSocket,
    InfowayWebSocket,
    KlineType,
    PeriodType,
    ScheduleType,
    SymbolType,
)
from infoway.exceptions import InfowayAPIError, InfowayAuthError

API_KEY = os.getenv("INFOWAY_API_KEY")
BAD_KEY = os.getenv("INFOWAY_BAD_API_KEY") or "invalid-key-sdk-deep-test-000000-infoway"

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not API_KEY, reason="INFOWAY_API_KEY not set — live tests skipped"),
]


@dataclass
class Row:
    name: str
    expect: str
    ok: bool
    detail: str


def _clip(value, n: int = 80) -> str:
    text = str(value)
    return text if len(text) <= n else text[:n] + "..."


def _nonempty(data):
    if data is None:
        raise AssertionError("null data")
    if isinstance(data, list) and not data:
        raise AssertionError("empty array")
    return _clip(data)


def _present(data):
    if data is None:
        raise AssertionError("null data")
    return _clip(data)


def _auth_like(exc: Exception) -> bool:
    if isinstance(exc, InfowayAuthError):
        return True
    if isinstance(exc, InfowayAPIError):
        msg = (exc.msg or "").lower()
        return exc.ret == 401 or any(s in msg for s in ("apikey", "token", "unauthorized", "not exists"))
    return False


class Probe:
    def __init__(self, good: str, bad: str):
        self.good = good
        self.bad = bad
        self.rows: list[Row] = []

    def expect_ok(self, name: str, action) -> None:
        try:
            detail = action()
            self.rows.append(Row(name, "OK", True, detail or ""))
        except Exception as e:
            self.rows.append(Row(name, "OK", False, f"{type(e).__name__}: {e}"))

    def expect_api(self, name: str, action) -> None:
        try:
            action()
            self.rows.append(Row(name, "API_ERROR", False, "succeeded unexpectedly"))
        except InfowayAuthError as e:
            self.rows.append(Row(name, "API_ERROR", False, f"got AUTH: {e}"))
        except InfowayAPIError as e:
            self.rows.append(Row(name, "API_ERROR", True, str(e)))
        except Exception as e:
            self.rows.append(Row(name, "API_ERROR", False, f"{type(e).__name__}: {e}"))

    def expect_auth(self, name: str, action) -> None:
        try:
            action()
            self.rows.append(Row(name, "AUTH", False, "succeeded unexpectedly"))
        except Exception as e:
            self.rows.append(Row(name, "AUTH", _auth_like(e), str(e)))

    def expect_client(self, name: str, exc_type: type[Exception], action) -> None:
        try:
            action()
            self.rows.append(Row(name, exc_type.__name__, False, "succeeded unexpectedly"))
        except Exception as e:
            self.rows.append(Row(name, exc_type.__name__, isinstance(e, exc_type), str(e)))

    def happy_rest(self) -> None:
        with InfowayClient(api_key=self.good, max_retries=2) as c:
            self.expect_ok("REST crypto.trade BTCUSDT", lambda: _nonempty(c.crypto.get_trade("BTCUSDT")))
            self.expect_ok("REST crypto.depth BTCUSDT", lambda: _nonempty(c.crypto.get_depth("BTCUSDT")))
            self.expect_ok(
                "REST crypto.kline MIN_1 x2",
                lambda: _nonempty(c.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 2)),
            )
            self.expect_ok(
                "REST crypto.kline + timestamp",
                lambda: _nonempty(c.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 2, timestamp=1_700_000_000)),
            )
            self.expect_ok("REST stock.trade AAPL.US", lambda: _nonempty(c.stock.get_trade("AAPL.US")))
            self.expect_ok("REST stock.trade 00700.HK", lambda: _nonempty(c.stock.get_trade("00700.HK")))
            self.expect_ok("REST stock.trade 600519.SH", lambda: _nonempty(c.stock.get_trade("600519.SH")))
            self.expect_ok("REST japan.trade 7203.JP", lambda: _nonempty(c.japan.get_trade("7203.JP")))
            self.expect_ok("REST india.trade RELIANCE.IN", lambda: _nonempty(c.india.get_trade("RELIANCE.IN")))
            self.expect_ok("REST korea.trade 005930.KS", lambda: _nonempty(c.korea.get_trade("005930.KS")))
            self.expect_ok("REST taiwan.trade 2330.TW", lambda: _nonempty(c.taiwan.get_trade("2330.TW")))
            self.expect_ok("REST common.trade USDJPY", lambda: _nonempty(c.common.get_trade("USDJPY")))

            self.expect_ok("REST basic.symbols CRYPTO", lambda: _nonempty(c.basic.get_symbols(SymbolType.CRYPTO)))
            self.expect_ok(
                "REST basic.symbols STOCK_TW",
                lambda: _nonempty(c.basic.get_symbols(SymbolType.STOCK_TW, "2330.TW")),
            )
            self.expect_ok(
                "REST basic.symbolInfo AAPL.US",
                lambda: _nonempty(c.basic.get_symbol_info(SymbolType.STOCK_US, "AAPL.US")),
            )
            self.expect_ok(
                "REST basic.stockDetail AAPL.US",
                lambda: _present(c.basic.get_stock_detail(SymbolType.STOCK_US, "AAPL.US")),
            )
            self.expect_ok("REST basic.markets", lambda: _present(c.basic.get_markets()))
            self.expect_ok(
                "REST basic.tradingDays US",
                lambda: _present(c.basic.get_trading_days("US", "20260801", "20260815")),
            )
            self.expect_ok("REST basic.tradingSchedule", lambda: _present(c.basic.get_trading_schedule()))
            self.expect_ok(
                "REST basic.tradingSchedule ENERGY",
                lambda: _present(c.basic.get_trading_schedule_by_type(ScheduleType.ENERGY)),
            )
            self.expect_ok("REST packages.info", lambda: _present(c.packages.get_info()))
            self.expect_ok("REST market.temperature HK,US", lambda: _present(c.market.get_temperature("HK,US")))
            self.expect_ok("REST market.breadth US", lambda: _present(c.market.get_breadth("US")))
            self.expect_ok("REST market.turnover US", lambda: _present(c.market.get_turnover("US")))
            self.expect_ok("REST market.indexes", lambda: _present(c.market.get_indexes()))
            self.expect_ok("REST market.overview US", lambda: _present(c.market.get_overview("US", "en")))
            self.expect_ok(
                "REST market.rank US",
                lambda: _present(c.market.get_rank("US", "all", "chg", "desc", 5, 0, "en")),
            )
            self.expect_ok("REST plate.industry HK", lambda: _present(c.plate.get_industry("HK", 10)))
            self.expect_ok(
                "REST stockInfo.company zh-CN",
                lambda: _present(c.stock_info.get_company("AAPL.US", "zh-CN")),
            )
            self.expect_ok("REST stockInfo.valuation", lambda: _present(c.stock_info.get_valuation("AAPL.US")))
            self.expect_ok(
                "REST financial.earningStatus",
                lambda: _present(c.financial.get_earning_status("AAPL.US", SymbolType.STOCK_US)),
            )
            self.expect_ok(
                "REST financial.income fq",
                lambda: _present(c.financial.get_income_statement("AAPL.US", SymbolType.STOCK_US, PeriodType.FQ)),
            )
            self.expect_ok(
                "REST financial.dividend",
                lambda: _present(c.financial.get_dividend("AAPL.US", SymbolType.STOCK_US)),
            )

    def bad_params(self) -> None:
        with InfowayClient(api_key=self.good, max_retries=1) as c:
            self.expect_client(
                "CLIENT scheduleByType STOCK_US",
                ValueError,
                lambda: c.basic.get_trading_schedule_by_type(SymbolType.STOCK_US),
            )
            self.expect_client(
                "CLIENT scheduleByType string STOCK_US",
                ValueError,
                lambda: c.basic.get_trading_schedule_by_type("STOCK_US"),
            )
            self.expect_api("REST trade unknown symbol", lambda: c.crypto.get_trade("NOPE_SYMBOL_XYZ_NOT_LISTED"))
            self.expect_api("REST stock trade NOPE.US", lambda: c.stock.get_trade("NOPE.US"))
            self.expect_api("REST korea trade AAPL.US (wrong market)", lambda: c.korea.get_trade("AAPL.US"))
            self.expect_api("REST kline type 99", lambda: c.crypto.get_kline("BTCUSDT", 99, 2))
            self.expect_api("REST kline empty codes", lambda: c.crypto.get_kline("", KlineType.MIN_1, 2))
            self.expect_api(
                "REST kline timestamp milliseconds",
                lambda: c.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 2, timestamp=1_700_000_000_000),
            )
            self.expect_api(
                "REST kline timestamp year-2000",
                lambda: c.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 2, timestamp=946_684_800),
            )
            self.expect_api("REST kline count 9999", lambda: c.crypto.get_kline("BTCUSDT", KlineType.DAY, 9999))
            self.expect_api("REST symbols type=US", lambda: c.basic.get_symbols("US"))
            self.expect_api("REST symbols type=STOCK_XX", lambda: c.basic.get_symbols("STOCK_XX"))
            self.expect_api(
                "REST tradingDays bad date format",
                lambda: c.basic.get_trading_days("US", "2026-08-01", "2026-08-15"),
            )
            self.expect_api(
                "REST tradingDays missing beginDay",
                lambda: c.basic.get_trading_days("US", "", "20260815"),
            )
            self.expect_api(
                "REST adjustmentFactors market=STOCK_US",
                lambda: c.basic.get_adjustment_factors("AAPL.US", "STOCK_US", "20260801", "20260815"),
            )
            self.expect_ok("REST stockDetail type=CRYPTO → data null", lambda: _crypto_detail(c))
            self.expect_ok("REST financial type=US uses .US suffix", lambda: _income_type_us(c))
            self.expect_ok("REST financial period_type=xx → empty", lambda: _income_period_xx(c))

    def bad_key_rest(self) -> None:
        with InfowayClient(api_key=self.bad, max_retries=1) as c:
            self.expect_auth("REST bad-key crypto.trade", lambda: c.crypto.get_trade("BTCUSDT"))
            self.expect_auth("REST bad-key packages.info", lambda: c.packages.get_info())
            self.expect_auth("REST bad-key basic.symbols", lambda: c.basic.get_symbols(SymbolType.CRYPTO))
            self.expect_auth(
                "REST bad-key financial",
                lambda: c.financial.get_earning_status("AAPL.US", SymbolType.STOCK_US),
            )

    async def websocket(self) -> None:
        await self._ws_tick("WS crypto trade BTCUSDT", self.good, "crypto", "BTCUSDT", 25)
        await self._ws_error("WS bad-key crypto handshake", self.bad, "crypto", 8)
        await self._ws_news("WS news handshake good key", self.good, 12)
        await self._ws_news_auth("WS bad-key news handshake", self.bad, 8)

    async def _ws_tick(self, name: str, key: str, business: str, codes: str, wait: int) -> None:
        received: list = []
        ws = InfowayWebSocket(api_key=key, business=business, max_reconnect_attempts=1)
        ws.on_trade = received.append
        await ws.subscribe_trade(codes)
        task = asyncio.create_task(ws.connect())
        try:
            for _ in range(wait * 5):
                if received:
                    break
                await asyncio.sleep(0.2)
            if received:
                self.rows.append(Row(name, "WS_TICK", True, "tick received"))
            else:
                self.rows.append(Row(name, "WS_TICK", False, f"no push in {wait}s"))
        except Exception as e:
            self.rows.append(Row(name, "WS_TICK", False, str(e)))
        finally:
            await ws.close()
            task.cancel()

    async def _ws_error(self, name: str, key: str, business: str, wait: int) -> None:
        ws = InfowayWebSocket(api_key=key, business=business, max_reconnect_attempts=1)
        try:
            await asyncio.wait_for(ws.connect(), timeout=wait)
            self.rows.append(Row(name, "InfowayAuthError", False, "succeeded unexpectedly"))
        except InfowayAuthError as e:
            self.rows.append(Row(name, "InfowayAuthError", True, str(e)))
        except Exception as e:
            self.rows.append(Row(name, "InfowayAuthError", False, f"{type(e).__name__}: {e}"))
        finally:
            await ws.close()

    async def _ws_news(self, name: str, key: str, wait: int) -> None:
        news = InfowayNewsWebSocket(api_key=key, max_reconnect_attempts=1, lang="zh-Hans")
        task = asyncio.create_task(news.connect())
        try:
            done, _ = await asyncio.wait({task}, timeout=wait)
            if task.done() and task.exception():
                exc = task.exception()
                self.rows.append(Row(name, "WS_NEWS", False, str(exc)))
            else:
                self.rows.append(Row(name, "WS_NEWS", True, "connected"))
        finally:
            await news.close()
            task.cancel()

    async def _ws_news_auth(self, name: str, key: str, wait: int) -> None:
        news = InfowayNewsWebSocket(api_key=key, max_reconnect_attempts=1)
        try:
            await asyncio.wait_for(news.connect(), timeout=wait)
            self.rows.append(Row(name, "InfowayAuthError", False, "succeeded unexpectedly"))
        except InfowayAuthError as e:
            self.rows.append(Row(name, "InfowayAuthError", True, str(e)))
        except Exception as e:
            self.rows.append(Row(name, "InfowayAuthError", False, f"{type(e).__name__}: {e}"))
        finally:
            await news.close()


def _crypto_detail(c: InfowayClient) -> str:
    data = c.basic.get_stock_detail(SymbolType.CRYPTO, "BTCUSDT")
    if data not in (None, {}):
        raise AssertionError(f"expected null/empty, got {_clip(data)}")
    return "server 200 data=null"


def _income_type_us(c: InfowayClient) -> str:
    data = c.financial.get_income_statement("AAPL.US", "US", "fq")
    if not data:
        raise AssertionError(f"expected rows, got {data}")
    return "server ignored type=US and returned AAPL rows"


def _income_period_xx(c: InfowayClient) -> str:
    data = c.financial.get_income_statement("AAPL.US", "STOCK_US", "xx")
    if data is None or (isinstance(data, list) and len(data) > 0):
        raise AssertionError(f"expected empty array, got {data}")
    return "server 200 empty list"


async def test_live_deep_probe():
    probe = Probe(API_KEY, BAD_KEY)
    probe.happy_rest()
    probe.bad_params()
    probe.bad_key_rest()
    await probe.websocket()
    failed = [r for r in probe.rows if not r.ok]
    report = "\n".join(f"{'OK' if r.ok else 'FAIL'}  {r.name}  ({r.expect}) {r.detail}" for r in probe.rows)
    print(report)
    assert not failed, f"{len(failed)} live cases failed\n" + report

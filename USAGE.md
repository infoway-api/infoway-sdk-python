# Infoway Python SDK usage

Python 3.9+ guide for quotes, fundamentals and live sockets. Install notes and changelog live in [README.md](README.md). Official API reference: [docs.infoway.io](https://docs.infoway.io). Chinese twin: [USAGE_CN.md](USAGE_CN.md).

- Package: `infoway-sdk==0.3.0`
- REST: `https://data.infoway.io`
- Quotes WebSocket: `wss://data.infoway.io/ws`
- News WebSocket: `wss://data.infoway.io/news`

---

## Contents

1. [Install and client](#1-install-and-client)
2. [Symbol conventions](#2-symbol-conventions)
3. [REST: market data](#3-rest-market-data)
4. [REST: basics](#4-rest-basics)
5. [REST: market overview](#5-rest-market-overview)
6. [REST: plates](#6-rest-plates)
7. [REST: stock info](#7-rest-stock-info)
8. [REST: financials](#8-rest-financials)
9. [Typed models](#9-typed-models)
10. [WebSocket: quotes](#10-websocket-quotes)
11. [WebSocket: news](#11-websocket-news)
12. [Errors and limits](#12-errors-and-limits)
13. [Full example](#13-full-example)

---

## 1. Install and client

```bash
pip install infoway-sdk==0.3.0
```

If you omit `api_key`, both REST and WebSocket read `INFOWAY_API_KEY`. `InfowayClient` is a context manager — close it when you are done.

```python
import os

from infoway import InfowayClient


def main() -> None:
    with InfowayClient(
        api_key=os.environ.get("INFOWAY_API_KEY"),
        base_url="https://data.infoway.io",  # optional
        timeout=15,                          # seconds, default 15
        max_retries=3,                       # default 3, exponential backoff
        parse=False,                         # default False: raw payloads
    ) as client:
        print(client.crypto.get_trade("BTCUSDT"))


if __name__ == "__main__":
    main()
```

| Argument | Default | Meaning |
|----------|---------|---------|
| `api_key` | `INFOWAY_API_KEY` | API key |
| `base_url` | `https://data.infoway.io` | REST root |
| `timeout` | `15` | Per-request timeout (seconds) |
| `max_retries` | `3` | Retries |
| `parse` | `False` | Normalise trade / depth / kline |

| Entry | Use |
|-------|-----|
| `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common` | Trade, depth, kline |
| `basic` | Symbols, calendar, single-name profile |
| `packages` | Quota for the current key |
| `market` | Sentiment, breadth, turnover, ranks |
| `plate` | Industry / concept sectors |
| `stock_info` | Valuation, ratings, company |
| `financial` | Statements, dividends, earnings |

String overloads still work. Prefer enums so you cannot send a value the server rejects:

| Enum | Wire values | Used by |
|------|-------------|---------|
| `KlineType` | `MIN_1`…`YEAR` (1–12) | K-line REST / WS |
| `SymbolType` | `STOCK_US` / `STOCK_CN` / `CRYPTO`… | `basic` / `financial` / stock detail |
| `Market` | `HK` `US` `CN` `JP` `KS` `TW` `IN` | Overview, plates, calendar; `Market.join` |
| `Lang` | `EN`=`en`, `ZH_CN`=`zh-CN` | REST `lang` |
| `NewsLang` | `EN` `ZH_HANS` `ZH_HANT` `JA` `KO`… | News WS |
| `PeriodType` | `FQ` / `FY` / `FH` | Financials |
| `Business` / `WsBusiness` | `STOCK` `CRYPTO` `KOREA` `TAIWAN`… | Quote WS `business` (`WsBusiness` is an alias) |
| `RankSort` | `CHG` `LAST_DONE` `VOLUME`… | Rank `sort` |
| `SortOrder` | `ASC` `DESC` | Rank `order` |
| `ScheduleType` | `ENERGY` `FOREX` `FUTURES` `METAL` `INDICES` | Trading-schedule filter |
| `WsCode` / `WsErrorCode` / `RestErrorCode` | Protocol / WS 5xx / REST `ret` | Frames and errors |

---

## 2. Symbol conventions

| Market | Form | Good | Bad |
|--------|------|------|-----|
| US | `.US` | `AAPL.US` | `AAPL` |
| HK | `.HK`, 5-digit pad | `00700.HK` | `700.HK` |
| Shanghai | `.SH` | `600519.SH` | `600519.CN` |
| Shenzhen | `.SZ` | `000001.SZ` | `000001.CN` |
| Japan | `.JP` | `7203.JP` | |
| Korea | `.KS` | `005930.KS` | |
| India | `.IN` | `RELIANCE.IN` | |
| Taiwan | `.TW` | `2330.TW` | |
| Crypto | pair | `BTCUSDT` | |
| FX / metals | pair | `USDJPY` | |

`basic` / `financial` / `get_stock_detail` take a **product type**, not a market code `US`:

`STOCK_US` `STOCK_CN` `STOCK_HK` `STOCK_JP` `STOCK_KS` `STOCK_IN` `STOCK_TW`  
`CRYPTO` `FOREX` `FUTURES` `ENERGY` `METAL` `INDICES`

`get_symbols` with `market=US` returns HTTP 400 `Required parameter 'type' is not present.`

---

## 3. REST: market data

Seven market clients share the same methods; only the path prefix changes. Join codes with commas.

```python
from infoway import InfowayClient, KlineType


def print_first_bar(data) -> None:
    entry = data[0]
    bar = entry["respList"][0]
    print(f"t={bar['t']} o={bar['o']} h={bar['h']} l={bar['l']} c={bar['c']}")


def main() -> None:
    with InfowayClient() as client:
        us = client.stock.get_trade("AAPL.US,TSLA.US")
        btc = client.crypto.get_trade("BTCUSDT")
        kr = client.korea.get_trade("005930.KS")
        tw = client.taiwan.get_trade("2330.TW")

        tick = btc[0]
        print(tick["s"], tick["p"])

        depth = client.crypto.get_depth("BTCUSDT")

        latest = client.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 100)
        historical = client.crypto.get_kline(
            "BTCUSDT", KlineType.MIN_1, 100, timestamp=1_700_000_000
        )
        print_first_bar(latest)


if __name__ == "__main__":
    main()
```

Trade fields: `s` symbol, `p` price, `v` size, `vw` turnover, `t` milliseconds, `td` side (0 default / 1 buy / 2 sell).  
K-lines are wrapped per symbol; bars sit in `respList`; `t` is a **seconds** string. `timestamp` only applies to minute / hour bars.

| Enum | Value | Interval |
|------|-------|----------|
| `MIN_1` / `MIN_5` / `MIN_15` / `MIN_30` | 1–4 | Minutes |
| `HOUR_1` / `HOUR_2` / `HOUR_4` | 5–7 | Hours |
| `DAY` / `WEEK` / `MONTH` / `QUARTER` / `YEAR` | 8–12 | Day and above |

At most **500** bars per symbol. Multi-symbol kline requests are capped at 2 bars each.

SDK always uses `POST /{market}/v2/batch_kline` (Japan / India / Korea / Taiwan have no GET kline).

---

## 4. REST: basics

Dates are always `YYYYMMDD`.

```python
from infoway import InfowayClient, Market, ScheduleType, SymbolType


def main() -> None:
    with InfowayClient() as client:
        client.basic.get_symbols(SymbolType.STOCK_US)
        client.basic.get_symbols(SymbolType.STOCK_TW, "2330.TW")
        client.basic.get_symbol_info(SymbolType.STOCK_US, "AAPL.US")
        client.basic.get_stock_detail(SymbolType.STOCK_US, "AAPL.US")
        client.basic.get_adjustment_factors("AAPL.US", Market.US, "20260801", "20260815")
        client.basic.get_trading_days(Market.US, "20260801", "20260815")
        client.basic.get_trading_schedule()
        client.basic.get_trading_schedule_by_type(ScheduleType.ENERGY)
        client.basic.get_markets()
        print(client.packages.get_info())


if __name__ == "__main__":
    main()
```

`get_trading_hours` is deprecated — use `get_trading_schedule`. The schedule endpoint has **no market filter**; `get_trading_schedule("US")` is the same as the no-arg call. Filter by product with `ScheduleType` (`ENERGY` / `FOREX` / `FUTURES` / `METAL` / `INDICES`). Passing `SymbolType.STOCK_US` to `get_trading_schedule_by_type` raises `ValueError` before the request.

`packages.get_info()` is `GET /package/info`: `packageName`, `expireTime`, `apiNumPerSec`, `maxWsConNum`, `maxNum`, `maxYearHisData`, `allWsNum`.

---

## 5. REST: market overview

Use `Market` and `Lang`. Temperature accepts several markets at once (`Market.join` or a comma string).

```python
from infoway import InfowayClient, Lang, Market, RankSort, SortOrder


def main() -> None:
    with InfowayClient() as client:
        client.market.get_temperature(Market.join(Market.HK, Market.US), Lang.ZH_CN)
        client.market.get_breadth(Market.US, Lang.ZH_CN)
        client.market.get_turnover(Market.US)
        client.market.get_indexes(Lang.EN)
        client.market.get_leaders(Market.US, 10)
        client.market.get_overview(Market.US, Lang.ZH_CN)
        client.market.get_rank_categories(Market.US)
        client.market.get_rank(
            Market.US, "all", RankSort.CHG, SortOrder.DESC, 30, 0, Lang.EN
        )


if __name__ == "__main__":
    main()
```

Rank `key` values come from `get_rank_categories`. `get_rank_config` is deprecated (HTTP 404).

---

## 6. REST: plates

```python
from infoway import InfowayClient, Market


def main() -> None:
    with InfowayClient() as client:
        client.plate.get_industry(Market.HK, 200)
        client.plate.get_concept("HK", 100)
        client.plate.get_members("IN20293.HK", 0, 50)
        client.plate.get_intro("IN20293.HK")
        client.plate.get_chart("HK", 50)


if __name__ == "__main__":
    main()
```

---

## 7. REST: stock info

Optional `lang`: `en` or `zh-CN`.

```python
from infoway import InfowayClient, Lang


def main() -> None:
    with InfowayClient() as client:
        symbol = "AAPL.US"
        client.stock_info.get_valuation(symbol)
        client.stock_info.get_ratings(symbol)
        client.stock_info.get_company(symbol, Lang.ZH_CN)
        client.stock_info.get_panorama(symbol)
        client.stock_info.get_concepts(symbol)
        client.stock_info.get_events(symbol, 20)
        client.stock_info.get_drivers(symbol)


if __name__ == "__main__":
    main()
```

---

## 8. REST: financials

Every method needs `symbol` plus `type`. Statement-style methods accept `period_type`:

| Value | Meaning |
|-------|---------|
| `fq` | Quarter |
| `fy` | Year |
| `fh` | Half-year |

```python
from infoway import InfowayClient, PeriodType, SymbolType


def main() -> None:
    with InfowayClient() as client:
        symbol = "AAPL.US"
        typ = SymbolType.STOCK_US

        client.financial.get_earning_status(symbol, typ)
        client.financial.get_income_statement(symbol, typ, PeriodType.FQ)
        client.financial.get_revenue(symbol, typ)
        client.financial.get_cash_flow(symbol, typ, PeriodType.FY)
        client.financial.get_balance_sheet(symbol, typ)
        client.financial.get_statistics(symbol, typ)
        client.financial.get_dividend(symbol, typ)
        client.financial.get_dividend_payout(symbol, typ)
        client.financial.get_earnings(symbol, typ, PeriodType.FQ)


if __name__ == "__main__":
    main()
```

HK example: `client.financial.get_dividend("00700.HK", SymbolType.STOCK_HK)`.

Production is lenient on a few financial filters: `type=US` still returns rows for `AAPL.US` (suffix wins); `period_type=xx` returns HTTP 200 and an empty list. `get_stock_detail(..., CRYPTO)` returns `data: null` with HTTP 200.

---

## 9. Typed models

Default return is the raw server payload (`list` / `dict`). Pass `parse=True` on the client or on `get_trade` / `get_depth` / `get_kline` when you want quirks absorbed.

```python
from infoway import InfowayClient, KlineType


def main() -> None:
    with InfowayClient(parse=True) as client:
        trades = client.crypto.get_trade("BTCUSDT")
        books = client.crypto.get_depth("BTCUSDT")
        bars = client.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 20)

        tick = trades[0]
        print(tick["s"], tick["p"], tick["t"])

        bar = bars[0]
        print(bar["o"], "->", bar["c"], "chg=", bar["change_percent"])

        # Per-call override still works when the client stays raw:
        raw_client = InfowayClient()
        parsed = raw_client.crypto.get_trade("BTCUSDT", parse=True)
        print(parsed[0]["p"])


if __name__ == "__main__":
    main()
```

| On the wire | After normalize |
|-------------|-----------------|
| Prices / sizes as `"305.771"` | `Decimal` |
| Trade / depth `t` milliseconds; kline `t` seconds string | timezone-aware `datetime` |
| REST `pc` / WS `pfr` = `"0.03%"` | `change_percent = 0.0003` |
| K-lines nested in `respList` | flat `list` of candles |
| Depth `a`/`b` = `[[prices…],[qtys…]]` | `[(price, qty), …]` |
| `vw` is turnover, not VWAP | `turnover` |

---

## 10. WebSocket: quotes

Separate from the REST client. `business` must match the market; a wrong channel acks and then pushes nothing.

`print_frames` defaults to **false**. Frames are DEBUG only unless you turn printing on or assign `on_frame`. REST and WebSocket both fall back to `INFOWAY_API_KEY`. `connect()` blocks until `close()` — run it as a task.

Quote callbacks (`on_trade` / `on_depth` / `on_kline` / `on_error`) must be **async**; the client `await`s them.

```python
import asyncio
import os

from infoway import Business, InfowayWebSocket, KlineType


async def main() -> None:
    ws = InfowayWebSocket(
        api_key=os.environ.get("INFOWAY_API_KEY"),
        business=Business.CRYPTO,  # stock / japan / india / korea / taiwan / crypto / common
        print_frames=True,         # optional; default False
        parse=False,
    )

    async def on_trade(data):
        print("TRADE", data["s"], data["p"])

    async def on_depth(data):
        print("DEPTH", data["s"])

    async def on_kline(data):
        print("KLINE", data)

    async def on_error(err):
        print(err)

    async def on_reconnect():
        print("reconnected")

    async def on_disconnect():
        print("disconnected")

    ws.on_trade = on_trade
    ws.on_depth = on_depth
    ws.on_kline = on_kline
    ws.on_frame = print
    ws.on_error = on_error
    ws.on_reconnect = on_reconnect
    ws.on_disconnect = on_disconnect

    await ws.subscribe_trade("BTCUSDT,ETHUSDT")
    await ws.subscribe_depth("BTCUSDT,ETHUSDT")
    await ws.subscribe_kline("BTCUSDT", KlineType.MIN_1)

    runner = asyncio.create_task(ws.connect())
    await asyncio.sleep(30)

    await ws.unsubscribe_kline("BTCUSDT", KlineType.MIN_1)
    await ws.unsubscribe_trade("BTCUSDT,ETHUSDT")
    await ws.close()
    await runner


if __name__ == "__main__":
    asyncio.run(main())
```

Equity trade types (odd lots, auctions, …) need `include_ty=True`. Crypto still omits `ty`.

```python
import asyncio

from infoway import Business, InfowayWebSocket


async def main() -> None:
    ws = InfowayWebSocket(business=Business.STOCK)

    async def on_trade(data):
        print(data["s"], "ty=", data.get("ty"))

    ws.on_trade = on_trade
    await ws.subscribe_trade("AAPL.US,TSLA.US", include_ty=True)
    runner = asyncio.create_task(ws.connect())
    await asyncio.sleep(15)
    await ws.close()
    await runner


if __name__ == "__main__":
    asyncio.run(main())
```

Callbacks receive **`data`**, not `{"code":10002,"data":{...}}`. Subscribe before `connect()`; the client replays on open.

Lifecycle (reconnect / subscribe / close):

- Heartbeat `10010` every 30s, **one task per live session**. A drop schedules **at most one** reconnect (1s → 30s backoff).
- `on_reconnect` fires only after a later successful open, never on the first `connect()`.
- `on_disconnect` fires on an unexpected drop, including a clean server close. `close()` does **not** fire it and does **not** reconnect; it also cancels a pending backoff so close returns immediately.
- The client keeps the **desired** subscription set. Unsubscribe is forgotten and is **not** replayed. Subscribe while reconnecting is flushed on the next open. Unsubscribing one kline interval leaves the others.
- HTTP 401 still stops reconnecting.

| Symptom | Cause |
|---------|-------|
| First frame is plain text `You have permission...` | `business=stock` greeting; SDK skips it |
| `{"code":200,"msg":"ws connect success"}` | Welcome, not an error |
| ack `ok` then silence | Wrong business, unknown code, or closed market |
| No heartbeat reply | Server does not answer `10010`; do not reconnect on missing ack |
| Dropped after many frames | **60 frames/minute/connection** (sub + unsub + heartbeat); merge codes |
| HTTP 401 | Bad key or no channel entitlement; `InfowayAuthError`, no reconnect |

Protocol:

| Dir | Code | Meaning |
|-----|------|---------|
| out | 10000 / 10003 / 10006 | Subscribe trade / depth / kline |
| out | 11000 / 11001 / 11002 | Unsubscribe |
| out | 10010 | Heartbeat (30s; `ack=1` yields 10011) |
| in | 10001 / 10004 / 10007 | Subscribe ack |
| in | 10002 / 10005 / 10008 | Push |
| in | 10011 | Heartbeat ack (optional) |
| in | 11010 | Unsubscribe ack (quotes + news) |
| in | 200 | Welcome |
| in | 500–521 | Server error → `on_error` (501/502 rate limit; see `WsErrorCode`) |

---

## 11. WebSocket: news

`wss://data.infoway.io/news`, separate entitlement. One news connection per key.

```python
import asyncio
import os

from infoway import InfowayNewsWebSocket, NewsLang


async def main() -> None:
    news = InfowayNewsWebSocket(
        api_key=os.environ.get("INFOWAY_API_KEY"),
        lang=NewsLang.ZH_HANS,
        print_frames=True,
    )

    async def on_news(item):
        print(item["title"], item.get("sd"))

    async def on_news_parsed(item):
        print(item.get("title"))

    async def on_error(err):
        print(err)

    news.on_news = on_news
    news.on_news_parsed = on_news_parsed
    news.on_error = on_error

    runner = asyncio.create_task(news.connect())
    await asyncio.sleep(60)

    await news.unsubscribe()  # 11020
    await news.subscribe(NewsLang.EN)  # replaces language
    await news.close()
    await runner


if __name__ == "__main__":
    asyncio.run(main())
```

Push fields: `dk` (dedup), `country`, `lang`, `route`, `title`, `published` (**seconds**), `urgency` (lower = hotter), `provider`, `symbols[]`, `link`, `content`, `sd` (summary).

`on_news_parsed` always converts `published` to a timezone-aware `datetime`. `on_news` stays raw unless you construct with `parse=True`.

| Dir | Code | Meaning |
|-----|------|---------|
| out | 10020 / 11020 | Subscribe / unsubscribe |
| in | 10021 / 10022 | Ack / push |

A key without news access fails the handshake with HTTP 401. The current `lang` is replayed on reconnect; `unsubscribe()` clears it so reconnect will not resubscribe. `on_reconnect` / `on_disconnect` follow the same rules as the quotes socket.

---

## 12. Errors and limits

```python
from infoway import (
    InfowayAPIError,
    InfowayAuthError,
    InfowayClient,
    InfowayIoError,
    InfowayRateLimitError,
    InfowayTimeoutError,
)


def main() -> None:
    try:
        with InfowayClient() as client:
            client.stock.get_trade("INVALID")
    except InfowayAuthError as e:
        print("auth:", e.msg)
    except InfowayRateLimitError as e:
        print(f"rate [{e.ret} {e.error_name}] {e.msg}")
    except InfowayTimeoutError as e:
        print("timeout:", e)
    except InfowayIoError as e:
        print("io:", e)
    except InfowayAPIError as e:
        # HTTP → RestErrorCode; WS → WsErrorCode. 508–514 collide.
        print(e)
        print(f"ret={e.ret} name={e.error_name} msg={e.msg} trace={e.trace_id}")


if __name__ == "__main__":
    main()
```

`InfowayRateLimitError` extends `InfowayAPIError`. REST budget is about **1200 calls/minute/key**. HTTP 429, REST `ret` 501/502, or `{"detail":"Rate limit exceeded"}` are retried with backoff.

`str(e)` includes the code and enum name, e.g. REST `[508 PRODUCT_NOT_EXISTS] All product not exists` vs WebSocket `[508 APIKEY_EXPIRED] …`. Do not decode REST `ret` with `WsErrorCode`.

A forged key is `InfowayAuthError` `[401] Token invalid` on REST, and handshake HTTP 401 (no reconnect) on both sockets.

### REST `ret` (`RestErrorCode`)

| Code | Name | Meaning |
|------|------|---------|
| 200 | SUCCESS | OK |
| 400 | BAD_REQUEST | commonApi bad params (HTTP 400 too) |
| 500 | SERVER_ERROR | Uncaught error, **or** production quote errors that still use 500 + the enum text |
| 501 / 502 | REQUEST_EXCEED_LIMIT / REQUEST_FOR_DAY_LIMIT | Rate limit → `InfowayRateLimitError` |
| 503 | KLINE_EXCEEDS_LIMIT | Too many bars |
| 505 | PRODUCTS_EXCEEDS_LIMIT | Too many symbols |
| 506 / 507 | PARAM_ERROR / PARAM_LOST | Bad / missing field |
| **508** | **PRODUCT_NOT_EXISTS** | **Unknown product** (not WS key expiry) |
| 509 | TOKEN_PERMISSION_EXPIRED | Token permission expired |
| 513 | TIME_LIMIT_ERROR | K-line `timestamp` older than the package |
| **514** | **NO_PERMISSION** | **No market entitlement** (not WS URL error) |

`/common/basic/*` only uses 200 / 400 / 500.

Verified against production (2026-09-21): quote-service business errors still arrive as **HTTP 200 + `ret=500`** with the English template (`All product not exists`, `Param error：klineType`, `Timestamp limit error…`, `Kline quantity exceeds the limit：500`). The SDK surfaces the **message**.

### WebSocket `code` (`WsErrorCode`)

| Code | Name | Meaning |
|------|------|---------|
| 501 / 502 | REQUEST_FREQUENCY_MIN_EXCEED / DAY | 60 frames/min → `InfowayRateLimitError` |
| 505 / 516 | PRODUCTS_QUANTITY_EXCEED | Per connection / all connections |
| 506 / 507 | PARAM_ERROR / PARAM_LOST | Bad or missing fields |
| **508–511** | **APIKEY_*** | **Expired / invalid / empty / blacklist** |
| 512 / 513 / 514 | Conn cap / heartbeat timeout / bad URL | 513 then close |
| 515 | PARAM_NOT_JSON | Inbound text was not JSON |
| 517–521 | Handshake | Missing key / no entitlement; 519/520 differ on Korea, Taiwan, news |

---

## 13. Full example

Pull a REST snapshot, then hang a live trade for 15 seconds.

```python
import asyncio
import os

from infoway import (
    InfowayAPIError,
    InfowayClient,
    InfowayWebSocket,
    KlineType,
    SymbolType,
)


async def main() -> None:
    api_key = os.environ.get("INFOWAY_API_KEY")
    if not api_key:
        raise SystemExit("Set INFOWAY_API_KEY")

    try:
        with InfowayClient(api_key=api_key) as client:
            trades = client.crypto.get_trade("BTCUSDT", parse=True)
            print("REST last:", trades[0]["p"])

            print("company:", client.stock_info.get_company("AAPL.US", "zh-CN"))
            print(
                "earnings:",
                client.financial.get_earning_status("AAPL.US", SymbolType.STOCK_US),
            )
            print("day kline:", client.crypto.get_kline("BTCUSDT", KlineType.DAY, 5))
            print("quota:", client.packages.get_info())
    except InfowayAPIError as e:
        print(e)
        return

    first_tick = asyncio.Event()
    ws = InfowayWebSocket(api_key=api_key, business="crypto")

    async def on_trade(data):
        print("WS trade:", data)
        first_tick.set()

    async def on_error(err):
        print(err)

    ws.on_trade = on_trade
    ws.on_error = on_error
    await ws.subscribe_trade("BTCUSDT,ETHUSDT")

    runner = asyncio.create_task(ws.connect())
    try:
        await asyncio.wait_for(first_tick.wait(), 45)
    except asyncio.TimeoutError:
        print("no trade push in 45s")
    finally:
        await ws.close()
        await runner


if __name__ == "__main__":
    asyncio.run(main())
```

```bash
export INFOWAY_API_KEY=your-key
python infoway_quickstart.py
```

Live contract (opt-in):

```bash
cd sdks/python
INFOWAY_API_KEY=your-key pytest tests/test_live_contract.py -m live
```

---

## Appendix: REST paths

Quotes (`{market}` = `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common`):

- `GET /{market}/batch_trade/{codes}`
- `GET /{market}/batch_depth/{codes}`
- `POST /{market}/v2/batch_kline`

Basics / financials / quota:

- `GET /common/basic/symbols`
- `GET /common/basic/symbols/info`
- `GET /common/basic/symbols/adjustment_factors`
- `GET /common/basic/markets/trading_days`
- `GET /common/basic/markets/trading_schedule`
- `GET /common/basic/markets`
- `GET /common/basic/stock/detail`
- `GET /common/basic/financial/{earning_status|income_statement|revenue|cash_flow|balance_sheet|statistics|dividend|dividend_payout|earnings}`
- `GET /package/info`

Market / plate / stock:

- `GET /common/v2/basic/market/{temperature|indexes}`
- `GET /common/v2/basic/market/{breadth|turnover|leaders|overview|rank/categories}/{market}`
- `GET /common/v2/basic/market/rank/{market}/{key}`
- `GET /common/v2/basic/plate/{industry|concept|chart}/{market}`
- `GET /common/v2/basic/plate/{members|intro}/{plateSymbol}`
- `GET /common/v2/basic/stock/{valuation|ratings|company|panorama|concepts|events|drivers}/{symbol}`

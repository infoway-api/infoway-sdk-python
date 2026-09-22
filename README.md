# Infoway Python SDK

[![PyPI version](https://img.shields.io/pypi/v/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**English** | [中文](README_CN.md)

Official Infoway Python SDK for REST market data, fundamentals, and WebSocket streams.

| Item | Description |
| --- | --- |
| Package | [`infoway-sdk==0.4.0`](https://pypi.org/project/infoway-sdk/) |
| Runtime | Python 3.9+ |
| REST | `https://data.infoway.io` |
| Quotes WebSocket | `wss://data.infoway.io/ws` |
| News WebSocket | `wss://data.infoway.io/news` |
| Rate limits | [REST](https://docs.infoway.io/en-docs/getting-started/api-limitation/rest-api-limitation) · [WebSocket](https://docs.infoway.io/en-docs/getting-started/api-limitation/websocket-limitation) |
| Error codes | [REST](https://docs.infoway.io/en-docs/getting-started/error-codes/rest-api-error-codes) · [WebSocket](https://docs.infoway.io/en-docs/getting-started/error-codes/websocket-error-codes) |
| Endpoints | [Endpoints](https://docs.infoway.io/en-docs/getting-started/endpoints) |

If `api_key` is omitted, the SDK reads `INFOWAY_API_KEY`. `InfowayClient` is a context manager.

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Symbols](#symbols)
- [Client](#client)
- [REST](#rest)
- [Typed results](#typed-results)
- [WebSocket](#websocket)
- [Error codes](#error-codes)
- [REST paths](#rest-paths)

## Install

```bash
pip install infoway-sdk==0.4.0
```

## Quick start

```python
from infoway import InfowayClient, KlineType

with InfowayClient() as client:
    print(client.stock.get_trade("AAPL.US"))
    print(client.crypto.get_kline("BTCUSDT", KlineType.DAY, 30))
    print(client.packages.get_info())
```

## Symbols

| Market | Format | Valid | Invalid |
| --- | --- | --- | --- |
| US | `{code}.US` | `AAPL.US` | `AAPL` |
| Hong Kong | 5-digit + `.HK` | `00700.HK` | `700.HK` |
| Shanghai | `{code}.SH` | `600519.SH` | `600519.CN` |
| Shenzhen | `{code}.SZ` | `000001.SZ` | `000001.CN` |
| Japan | `{code}.JP` | `7203.JP` | |
| Korea | `{code}.KS` | `005930.KS` | |
| India | `{code}.IN` | `RELIANCE.IN` | |
| Taiwan | `{code}.TW` | `2330.TW` | |
| Crypto | Pair | `BTCUSDT` | |
| FX | Pair | `USDJPY` | |

`basic` / `financial` take a product `type` such as `STOCK_US` or `CRYPTO`, not a market code like `US`.

## Client

| Parameter | Default | Description |
| --- | --- | --- |
| `api_key` | `INFOWAY_API_KEY` | API key |
| `base_url` | `https://data.infoway.io` | REST base URL |
| `timeout` | `15` | Per-request timeout (seconds) |
| `max_retries` | `3` | Retry count |
| `parse` | `False` | Normalize trades / depth / candles |

| Client | Use |
| --- | --- |
| `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common` | Trade, depth, candles |
| `basic` / `packages` | Symbols, calendar, plan |
| `market` / `plate` | Overview, sectors |
| `stock_info` / `financial` | Fundamentals, statements |

Prefer enums: `KlineType`, `SymbolType`, `Market`, `Lang`, `NewsLang`, `PeriodType`, `Business`, `RankSort`, `SortOrder`, `ScheduleType`.

## REST

Join symbols with commas. Rate limits: [REST API Limitation](https://docs.infoway.io/en-docs/getting-started/api-limitation/rest-api-limitation).

### Quotes

| Method | Description |
| --- | --- |
| `get_trade(codes)` | Latest trade |
| `get_depth(codes)` | Order book |
| `get_kline(codes, kline_type, count, timestamp=None)` | Candles |

Trade fields: `s` symbol, `p` price, `v` volume, `vw` turnover, `t` milliseconds, `td` side. Candles are under `respList`; `t` is seconds. Up to 500 bars per symbol; multi-symbol calls return 2 bars each.

```python
client.stock.get_trade("AAPL.US,TSLA.US")
client.crypto.get_depth("BTCUSDT")
client.korea.get_trade("005930.KS")
client.taiwan.get_trade("2330.TW")
client.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 100)
```

| Enum | Value | Interval |
| --- | --- | --- |
| `MIN_1` / `MIN_5` / `MIN_15` / `MIN_30` | 1–4 | Minutes |
| `HOUR_1` / `HOUR_2` / `HOUR_4` | 5–7 | Hours |
| `DAY` / `WEEK` / `MONTH` / `QUARTER` / `YEAR` | 8–12 | Daily and above |

### Basic info

Dates use `YYYYMMDD`. `get_trading_hours` is deprecated; use `get_trading_schedule`.

```python
from infoway import Market, ScheduleType, SymbolType

client.basic.get_symbols(SymbolType.STOCK_US)
client.basic.get_symbol_info(SymbolType.STOCK_US, "AAPL.US")
client.basic.get_stock_detail(SymbolType.STOCK_US, "AAPL.US")
client.basic.get_adjustment_factors("AAPL.US", Market.US, "20260801", "20260815")
client.basic.get_trading_days(Market.US, "20260801", "20260815")
client.basic.get_trading_schedule()
client.basic.get_trading_schedule_by_type(ScheduleType.ENERGY)
client.basic.get_markets()
client.packages.get_info()
```

### Overview / sectors / stock info / financials

```python
from infoway import Lang, Market, PeriodType, RankSort, SortOrder, SymbolType

client.market.get_temperature(Market.join(Market.HK, Market.US), Lang.ZH_CN)
client.market.get_breadth(Market.US, Lang.ZH_CN)
client.market.get_turnover(Market.US)
client.market.get_indexes(Lang.EN)
client.market.get_leaders(Market.US, 10)
client.market.get_overview(Market.US, Lang.ZH_CN)
client.market.get_rank_categories(Market.US)
client.market.get_rank(Market.US, "all", sort=RankSort.CHG, order=SortOrder.DESC, limit=30)

client.plate.get_industry("HK", limit=200)
client.plate.get_concept("HK", limit=100)
client.plate.get_members("IN20293.HK")
client.plate.get_intro("IN20293.HK")
client.plate.get_chart("HK", limit=50)

client.stock_info.get_valuation("AAPL.US")
client.stock_info.get_ratings("AAPL.US")
client.stock_info.get_company("AAPL.US", lang="zh-CN")
client.stock_info.get_panorama("AAPL.US")
client.stock_info.get_concepts("AAPL.US")
client.stock_info.get_events("AAPL.US", limit=20)
client.stock_info.get_drivers("AAPL.US")

client.financial.get_earning_status("AAPL.US", SymbolType.STOCK_US)
client.financial.get_income_statement("AAPL.US", SymbolType.STOCK_US, PeriodType.FQ)
client.financial.get_revenue("AAPL.US", SymbolType.STOCK_US)
client.financial.get_cash_flow("AAPL.US", SymbolType.STOCK_US, PeriodType.FY)
client.financial.get_balance_sheet("AAPL.US", SymbolType.STOCK_US)
client.financial.get_statistics("AAPL.US", SymbolType.STOCK_US)
client.financial.get_dividend("00700.HK", SymbolType.STOCK_HK)
client.financial.get_dividend_payout("AAPL.US", SymbolType.STOCK_US)
client.financial.get_earnings("AAPL.US", SymbolType.STOCK_US, PeriodType.FQ)
```

Rank `key` values come from `get_rank_categories`. Financial methods require `symbol` and `type`. `period_type`: `fq` quarter, `fy` year, `fh` half-year.

## Typed results

Set `parse=True` on the client or per call.

```python
client = InfowayClient(parse=True)
bars = client.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 100)
bars[0]["c"]               # Decimal
bars[0]["t"]               # datetime (UTC)
bars[0]["turnover"]        # renamed from vw
bars[0]["change_percent"]  # 0.0003
```

| Raw | Normalized |
| --- | --- |
| Price / volume as strings | `Decimal` |
| Trade / depth `t` in ms; candle `t` in seconds | timezone-aware `datetime` |
| REST `pc` / WS `pfr` | `change_percent` |
| Candle `respList` | flattened list |
| Book `a`/`b` columns | `(price, qty)` |
| `vw` | `turnover` |

## WebSocket

### Quotes

`business` must match the symbol market. `connect()` blocks — run it as a task. 60 frames per minute per connection. See [WebSocket Limitation](https://docs.infoway.io/en-docs/getting-started/api-limitation/websocket-limitation).

```python
import asyncio
from infoway import KlineType
from infoway.ws import InfowayWebSocket

async def main():
    ws = InfowayWebSocket(business="crypto")
    ws.on_trade = lambda data: print(data["s"], data["p"])
    ws.on_error = lambda err: print(err)

    task = asyncio.create_task(ws.connect())
    await ws.subscribe_trade("BTCUSDT,ETHUSDT")
    await ws.subscribe_kline("BTCUSDT", KlineType.MIN_1)
    await asyncio.sleep(30)
    await ws.unsubscribe_kline("BTCUSDT", KlineType.MIN_1)
    await ws.close()
    await task

asyncio.run(main())
```

Equity trade types: `subscribe_trade(codes, include_ty=True)`.

| Behavior | Description |
| --- | --- |
| Heartbeat | `10010` every 30 seconds; server does not reply |
| Reconnect | Replays the current subscription set |
| `on_reconnect` | After a later successful open |
| `on_disconnect` | Unexpected drop only. `close()` does not fire it |
| HTTP 401 | Stops reconnecting |

| Dir | Code | Description |
| --- | --- | --- |
| out | 10000 / 10003 / 10006 | Subscribe trade / depth / kline |
| out | 11000 / 11001 / 11002 | Unsubscribe |
| out | 10010 | Heartbeat |
| in | 10002 / 10005 / 10008 | Push |
| in | 11010 | Unsubscribe ack |
| in | 200 | Connected |

An ack means the request was accepted. Merge symbols into one comma-separated string.

### News

`wss://data.infoway.io/news` requires a separate entitlement. One news connection per key.

```python
from infoway.ws import InfowayNewsWebSocket

news = InfowayNewsWebSocket(lang="zh-Hans")
news.on_news = lambda item: print(item["title"])
```

Subscribe `10020`, unsubscribe `11020`, push `10022`. A later subscribe replaces the language.

## Error codes

REST uses `ret`. WebSocket uses `code`. `508`–`514` mean different things on each side. Full tables: [REST API Error Codes](https://docs.infoway.io/en-docs/getting-started/error-codes/rest-api-error-codes) and [WebSocket Error Codes](https://docs.infoway.io/en-docs/getting-started/error-codes/websocket-error-codes).

```python
from infoway import InfowayAPIError, InfowayAuthError, InfowayRateLimitError

try:
    client.stock.get_trade("INVALID")
except InfowayAuthError as e:
    print(e.msg)
except InfowayRateLimitError as e:
    print(e.ret, e.msg)
except InfowayAPIError as e:
    print(e, e.trace_id)
```

REST budget is about 1200 calls/minute/key. An invalid key raises `InfowayAuthError` on REST; WebSocket handshake HTTP 401 does not reconnect.

| REST `ret` | Description |
| --- | --- |
| 200 | Success |
| 400 | Bad request |
| 500 | Server error |
| 501 / 502 | Rate limit |
| 503 | Candle count exceeded |
| 505 | Symbol count exceeded |
| 506 / 507 | Invalid / missing parameter |
| 508 | Symbol not found |
| 509 | Permission expired |
| 513 | Timestamp outside plan history |
| 514 | No permission |

| WebSocket `code` | Description |
| --- | --- |
| 501 / 502 | Rate limit |
| 505 / 516 | Subscription count exceeded |
| 506 / 507 | Invalid / missing parameter |
| 508–511 | API key expired / invalid / empty / blacklisted |
| 512 | Connection count exceeded |
| 513 | Heartbeat timeout |
| 515 | Not JSON |
| 517–521 | Handshake failed |

## REST paths

`{market}` = `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common`. Full list: [Endpoints](https://docs.infoway.io/en-docs/getting-started/endpoints).

| API | Path |
| --- | --- |
| Latest trade | `GET /{market}/batch_trade/{codes}` |
| Order book | `GET /{market}/batch_depth/{codes}` |
| Candles | `POST /{market}/v2/batch_kline` |
| Symbols / calendar / financials | `GET /common/basic/*` |
| Overview / sectors / stock info | `GET /common/v2/basic/*` |
| Package | `GET /package/info` |

## License

MIT. API key: [infoway.io](https://infoway.io).

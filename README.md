# Infoway SDK

[![PyPI version](https://img.shields.io/pypi/v/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**English** | [中文](README_CN.md)

Official Python SDK for [Infoway](https://infoway.io) real-time financial data API. Full documentation at [docs.infoway.io](https://docs.infoway.io).

Walkthrough with copy-paste examples: [USAGE.md](USAGE.md) · [使用说明](USAGE_CN.md). Version **0.3.0**.

## Installation

```bash
pip install infoway-sdk
```

## Quick Start

```python
from infoway import InfowayClient, KlineType

client = InfowayClient(api_key="YOUR_API_KEY")

# Real-time trades
trades = client.stock.get_trade("AAPL.US")

# Daily K-lines for crypto
klines = client.crypto.get_kline("BTCUSDT", kline_type=KlineType.DAY, count=30)

# Instrument list for a market
symbols = client.basic.get_symbols("STOCK_US")

# Market temperature
temp = client.market.get_temperature(market="HK,US")

# Sector/plate rankings
plates = client.plate.get_industry("HK", limit=10)
```

### Symbol codes

| Market | Format | Example |
|--------|--------|---------|
| US equities | `TICKER.US` | `AAPL.US` |
| Hong Kong | `NNNNN.HK` — **zero-padded to 5 digits** | `00700.HK` (not `700.HK`) |
| China A-shares | `NNNNNN.SH` / `NNNNNN.SZ` | `600519.SH`, `000001.SZ` |
| Japan / India / Korea | `CODE.JP` / `.IN` / `.KS` | `7203.JP`, `RELIANCE.IN` |
| Crypto | pair | `BTCUSDT` |
| Forex / metals | pair | `USDJPY`, `XAUUSD` |

A missing or wrong suffix is answered with `[500] All product not exists`.

## Response fields

The API returns short field names and string-encoded numbers. These are the real names:

| Endpoint | Shape |
|----------|-------|
| `get_trade` | `[{"s","t","p","v","vw","td"}]` — `t` is epoch **milliseconds**, `vw` is **turnover** (not a VWAP) |
| `get_depth` | `[{"s","t","a","b"}]` — `a`/`b` are **column-major** `[[price...],[qty...]]`, not `asks`/`bids` |
| `get_kline` | `[{"s","respList":[{"t","o","h","l","c","v","vw","pc","pca"}]}]` — candles are nested under `respList`, and `t` is a **string in seconds** |

### Optional normalisation (`parse=True`)

Off by default, so raw payloads keep flowing to existing code. Turn it on per call
or client-wide to get `Decimal`s, timezone-aware `datetime`s, flattened K-lines and
`(price, qty)` depth pairs:

```python
client = InfowayClient(api_key="YOUR_API_KEY", parse=True)

candles = client.crypto.get_kline("BTCUSDT", kline_type=KlineType.MIN_1, count=100)
candles[0]["c"]               # Decimal("63039.00000")
candles[0]["t"]               # datetime(2026, 8, 15, 6, 27, tzinfo=timezone.utc)
candles[0]["turnover"]        # Decimal — renamed from "vw"
candles[0]["change_percent"]  # Decimal("-0.0001") — from "pc" (REST) / "pfr" (WS)

book = client.crypto.get_depth("BTCUSDT")
book[0]["a"][0]               # (Decimal("63039.00"), Decimal("45.06"))

# per-call override
raw = client.crypto.get_trade("BTCUSDT", parse=False)
```

## WebSocket Streaming

```python
import asyncio
from infoway.ws import InfowayWebSocket

async def main():
    ws = InfowayWebSocket(api_key="YOUR_API_KEY", business="crypto")

    async def on_trade(data):
        # `data` is the unwrapped payload: {"s","t","p","v","vw","td"}
        print(data["s"], data["p"])

    ws.on_trade = on_trade
    # merge every symbol into ONE subscribe frame
    await ws.subscribe_trade("BTCUSDT,ETHUSDT")   # a list works too
    await ws.connect()

asyncio.run(main())
```

### Choose the channel that matches your instruments

| `business` | Instruments |
|------------|-------------|
| `stock` | US / HK / CN equities |
| `japan` | `.JP` |
| `india` | `.IN` |
| `korea` | `.KS` (KOSPI + KOSDAQ) |
| `crypto` | `BTCUSDT`, ... (24x7) |
| `common` | forex / metals / futures, e.g. `XAUUSD` |

The server acknowledges a subscription with `10001 ok` **even when the channel is
wrong or the code does not exist** — and then never pushes anything. If you get an
ack but no data, check the `business` first.

### WebSocket behaviour

- **Callbacks receive `msg["data"]`**, matching what the REST methods return. The
  K-line callback keeps `ty` (the interval).
- **Auto-reconnect** with exponential backoff (1s to 30s cap), **except on HTTP 401** —
  a rejected API key raises `InfowayAuthError` and stops, instead of hammering the gateway.
  One drop schedules one reconnect; `close()` cancels backoff and does not fire
  `on_disconnect`. `on_reconnect` is only after a later successful open.
- **Auto-resubscribe** on reconnect of the **desired** set. Unsubscribe is not replayed;
  subscribe while offline is flushed on the next open.
- **Heartbeat** every 30s (**one task per live session**). The server sends **no reply**
  to heartbeats; never treat a missing heartbeat ack as a dead connection.
- **Rate limit: 60 frames per minute per connection**, heartbeats included. Always
  merge codes into a single subscribe frame rather than one frame per symbol.
- Non-JSON frames (the plaintext `You have permission to subscribe to all market data`
  greeting on `business=stock`) and the `{"code":200,"msg":"ws connect success"}`
  welcome frame are handled internally.
- `unsubscribe_kline(codes, kline_type)` sends `klineTypes` so only that interval is
  dropped — without it the server would clear every interval for those instruments.

```python
await ws.subscribe_kline("BTCUSDT", KlineType.DAY)
await ws.unsubscribe_kline("BTCUSDT", KlineType.DAY)   # other intervals stay subscribed
```

## Real-time news

News is a **separate connection** on its own path (`wss://data.infoway.io/news`) and
needs a separate entitlement on your API key.

```python
import asyncio
from infoway import InfowayNewsWebSocket, InfowayAuthError

async def main():
    news = InfowayNewsWebSocket(api_key="YOUR_API_KEY")

    async def on_news(item):
        # dk, country, lang, route, title, published (Unix SECONDS),
        # urgency (lower = more urgent), provider, symbols[], link, content, sd
        print(item["title"], item["symbols"])

    news.on_news = on_news
    await news.subscribe("en")   # en, zh-Hans, zh-Hant, ja, ko, de, fr, es, pt, ru, tr
    try:
        await news.connect()
    except InfowayAuthError as e:
        print("news channel unavailable:", e)

asyncio.run(main())
```

Notes: subscribing again **replaces** the previous language (there is no per-item
unsubscribe), and **one connection per API key** is allowed. Without the news
entitlement the handshake is rejected with HTTP 401 and `InfowayAuthError` is raised
immediately rather than reconnecting forever.

## REST API Modules

| Module | Accessor | Description |
|--------|----------|-------------|
| Stock | `client.stock` | HK, US, CN equities -- trade, depth, K-line |
| Crypto | `client.crypto` | Cryptocurrency pairs -- trade, depth, K-line |
| Japan | `client.japan` | Japan market data -- trade, depth, K-line |
| India | `client.india` | India market data -- trade, depth, K-line |
| Korea | `client.korea` | Korea (`.KS`) -- trade, depth, K-line |
| Taiwan | `client.taiwan` | Taiwan (`.TW`) -- trade, depth, K-line |
| Common | `client.common` | Cross-market data -- trade, depth, K-line |
| Basic | `client.basic` | Symbol lists, static info, adjustment factors, trading calendar |
| Packages | `client.packages` | Quota for the current key (`GET /package/info`) |
| Market | `client.market` | Temperature, breadth, turnover, indexes, leaders, ranks |
| Plate | `client.plate` | Sector/industry/concept plates, members, charts |
| Stock Info | `client.stock_info` | Fundamentals -- valuation, ratings, company, panorama, events |
| Financial | `client.financial` | Statements, dividends, earnings |

### `client.basic`

```python
# instrument list — `type` is required
# STOCK_US STOCK_CN STOCK_HK STOCK_JP STOCK_KS STOCK_IN CRYPTO FOREX FUTURES
client.basic.get_symbols("STOCK_US")
client.basic.get_symbols("STOCK_US", symbols="AAPL.US,TSLA.US")

# static/reference info (max 500 symbols)
client.basic.get_symbol_info("STOCK_US", "AAPL.US")

# forward adjustment factors — dates are YYYYMMDD strings
client.basic.get_adjustment_factors("AAPL.US", "US", "20260801", "20260814")

# trading calendar → {"trade_days": [...], "half_trade_days": [...]}
client.basic.get_trading_days("US", "20260801", "20260831")

# sessions/holidays for non-equity instruments
# type: ENERGY | FOREX | FUTURES | METAL | INDICES
client.basic.get_trading_schedule(type="METAL")
```

`get_trading_hours()` is a deprecated alias of `get_trading_schedule()` and emits a
`DeprecationWarning`; the old `/markets/trading_hours` path does not exist on the server.

## Configuration

You can pass `api_key` directly or set it via environment variable:

```bash
export INFOWAY_API_KEY="YOUR_API_KEY"
```

```python
# Reads INFOWAY_API_KEY from environment automatically
client = InfowayClient()
```

### Client Options

```python
client = InfowayClient(
    api_key="YOUR_API_KEY",
    base_url="https://data.infoway.io",  # default
    timeout=15.0,                         # request timeout in seconds
    max_retries=3,                        # retries (connection errors, timeouts, rate limits)
    parse=False,                          # normalise market-data payloads
)
```

## Error Handling

```python
from infoway import (
    InfowayClient, InfowayAPIError, InfowayAuthError,
    InfowayRateLimitError, InfowayTimeoutError,
)

client = InfowayClient(api_key="YOUR_API_KEY")

try:
    trades = client.stock.get_trade("AAPL.US")
except InfowayAuthError:
    print("Invalid API key")
except InfowayRateLimitError:
    print("Rate limited — back off and retry")
except InfowayTimeoutError:
    print("Request timed out")
except InfowayAPIError as e:
    print(f"API error [{e.ret}]: {e.msg}")
```

`InfowayRateLimitError` subclasses `InfowayAPIError`. Rate limiting is also served with
**HTTP 200** and a body of `{"detail": "Rate limit exceeded"}`, which older SDK versions
silently turned into `None`; it is now raised (and retried with backoff) properly.

## License

MIT

---

Get your free API key at [infoway.io](https://infoway.io) -- 7-day free trial, no credit card required.

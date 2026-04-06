# Infoway SDK

[![PyPI version](https://img.shields.io/pypi/v/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**English** | [中文](README_CN.md)

Official Python SDK for [Infoway](https://infoway.io) real-time financial data API. Full documentation at [docs.infoway.io](https://docs.infoway.io).

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

# Market temperature
temp = client.market.get_temperature(market="HK,US")

# Sector/plate rankings
plates = client.plate.get_industry("HK", limit=10)
```

## WebSocket Streaming

```python
import asyncio
from infoway.ws import InfowayWebSocket

async def main():
    ws = InfowayWebSocket(api_key="YOUR_API_KEY", business="stock")

    async def on_trade(msg):
        print(f"Trade: {msg}")

    ws.on_trade = on_trade
    await ws.subscribe_trade("AAPL.US,TSLA.US")
    await ws.connect()

asyncio.run(main())
```

### WebSocket Features

- **Auto-reconnect** with exponential backoff (1s to 30s cap)
- **Heartbeat keepalive** at 30-second intervals
- **Auto-resubscribe** on reconnect -- no manual re-subscription needed
- Event callbacks: `on_trade`, `on_depth`, `on_kline`, `on_error`, `on_reconnect`, `on_disconnect`

## REST API Modules

| Module | Accessor | Description |
|--------|----------|-------------|
| Stock | `client.stock` | HK, US, CN equities -- trade, depth, K-line |
| Crypto | `client.crypto` | Cryptocurrency pairs -- trade, depth, K-line |
| Japan | `client.japan` | Japan market data -- trade, depth, K-line |
| India | `client.india` | India market data -- trade, depth, K-line |
| Common | `client.common` | Cross-market data -- trade, depth, K-line |
| Basic | `client.basic` | Symbol lists, trading days, trading hours, adjustment factors |
| Market | `client.market` | Market temperature, breadth, indexes, leaders, rank config |
| Plate | `client.plate` | Sector/industry/concept plates, members, charts |
| Stock Info | `client.stock_info` | Fundamentals -- valuation, ratings, company, panorama, events |

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
    max_retries=3,                        # retry count for failed requests
)
```

## Error Handling

```python
from infoway import InfowayClient, InfowayAPIError, InfowayAuthError, InfowayTimeoutError

client = InfowayClient(api_key="YOUR_API_KEY")

try:
    trades = client.stock.get_trade("AAPL.US")
except InfowayAuthError:
    print("Invalid API key")
except InfowayTimeoutError:
    print("Request timed out")
except InfowayAPIError as e:
    print(f"API error [{e.ret}]: {e.msg}")
```

## License

MIT

---

Get your free API key at [infoway.io](https://infoway.io) -- 7-day free trial, no credit card required.


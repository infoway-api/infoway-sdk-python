# Infoway SDK (中文)

[![PyPI version](https://img.shields.io/pypi/v/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | **中文**

[Infoway](https://infoway.io) 实时金融数据 API 的官方 Python SDK。完整文档请访问 [docs.infoway.io](https://docs.infoway.io)。

完整示例与分接口用法：[使用说明](USAGE_CN.md) · [USAGE.md](USAGE.md)。当前版本 **0.3.0**。

## 安装

```bash
pip install infoway-sdk
```

## 快速开始

```python
from infoway import InfowayClient, KlineType

client = InfowayClient(api_key="YOUR_API_KEY")

# 实时成交数据
trades = client.stock.get_trade("AAPL.US")

# 加密货币日K线
klines = client.crypto.get_kline("BTCUSDT", kline_type=KlineType.DAY, count=30)

# 标的列表
symbols = client.basic.get_symbols("STOCK_US")

# 市场温度
temp = client.market.get_temperature(market="HK,US")

# 板块排行
plates = client.plate.get_industry("HK", limit=10)
```

### 标的代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| 美股 | `TICKER.US` | `AAPL.US` |
| 港股 | `NNNNN.HK` —— **必须补零到 5 位** | `00700.HK`（不是 `700.HK`） |
| A 股 | `NNNNNN.SH` / `NNNNNN.SZ` | `600519.SH`、`000001.SZ` |
| 日/印/韩 | `CODE.JP` / `.IN` / `.KS` | `7203.JP`、`RELIANCE.IN` |
| 加密货币 | 交易对 | `BTCUSDT` |
| 外汇 / 贵金属 | 交易对 | `USDJPY`、`XAUUSD` |

后缀写错或缺失，服务端返回 `[500] All product not exists`。

## 返回字段

服务端字段名很短、数值多为字符串。以下是真实字段：

| 接口 | 结构 |
|------|------|
| `get_trade` | `[{"s","t","p","v","vw","td"}]` —— `t` 是**毫秒**时间戳，`vw` 是**成交额**（不是 VWAP） |
| `get_depth` | `[{"s","t","a","b"}]` —— `a`/`b` 是**转置的列式** `[[价格...],[量...]]`，不是 `asks`/`bids` |
| `get_kline` | `[{"s","respList":[{"t","o","h","l","c","v","vw","pc","pca"}]}]` —— K 线套在 `respList` 里，`t` 是**秒级字符串** |

### 可选归一化（`parse=True`）

默认关闭，保持原始返回不变。按需开启后得到 `Decimal`、带时区的 `datetime`、展平的 K 线、
以及 `(价格, 数量)` 形式的盘口：

```python
client = InfowayClient(api_key="YOUR_API_KEY", parse=True)

candles = client.crypto.get_kline("BTCUSDT", kline_type=KlineType.MIN_1, count=100)
candles[0]["c"]               # Decimal("63039.00000")
candles[0]["t"]               # datetime(2026, 8, 15, 6, 27, tzinfo=timezone.utc)
candles[0]["turnover"]        # Decimal —— 由 "vw" 改名
candles[0]["change_percent"]  # Decimal("-0.0001") —— 来自 "pc"(REST) / "pfr"(WS)

book = client.crypto.get_depth("BTCUSDT")
book[0]["a"][0]               # (Decimal("63039.00"), Decimal("45.06"))

# 单次调用覆盖
raw = client.crypto.get_trade("BTCUSDT", parse=False)
```

## WebSocket 实时推送

```python
import asyncio
from infoway.ws import InfowayWebSocket

async def main():
    ws = InfowayWebSocket(api_key="YOUR_API_KEY", business="crypto")

    async def on_trade(data):
        # data 是已解包的业务数据：{"s","t","p","v","vw","td"}
        print(data["s"], data["p"])

    ws.on_trade = on_trade
    # 所有代码必须合并成一条订阅报文
    await ws.subscribe_trade("BTCUSDT,ETHUSDT")   # 也可以传 list
    await ws.connect()

asyncio.run(main())
```

### 按标的选择正确的 business 频道

| `business` | 覆盖标的 |
|------------|----------|
| `stock` | 美股 / 港股 / A 股 |
| `japan` | `.JP` |
| `india` | `.IN` |
| `korea` | `.KS`（KOSPI + KOSDAQ） |
| `crypto` | `BTCUSDT` 等（7×24） |
| `common` | 外汇 / 贵金属 / 期货，如 `XAUUSD` |

**频道选错或代码不存在，服务端同样回 `10001 ok`，然后永远静默。** 收到 ack 却没有数据时，
请先检查 `business` 是否与标的匹配。

### WebSocket 行为说明

- **回调收到的是 `msg["data"]`**，与 REST 返回口径一致；K 线回调保留 `ty`（周期）字段。
- **自动重连**（指数退避 1 秒→30 秒上限），但 **HTTP 401 除外** —— API Key 被拒时抛
  `InfowayAuthError` 并停止重连，不会一直冲击网关（避免被判恶意流量封禁）。
  一次掉线只安排一次重连；`close()` 会打断退避且不触发 `on_disconnect`。
  `on_reconnect` 只在再次连上时触发。
- **重连后自动重新订阅目标集合**。已退订的内容不会回放；断线窗口里的新订阅会在下一跳补发。
- **心跳** 每 30 秒一次（**每个存活会话一个任务**）。服务端对心跳**不回任何响应**，不要用"等心跳 ack 超时"判断断线。
- **限流：每连接 60 条报文/分钟**（含心跳）。务必合并 codes 成一条订阅，不要一个 symbol 发一条。
- 非 JSON 帧（`business=stock` 首帧的纯文本 `You have permission to subscribe to all market data`）
  与欢迎帧 `{"code":200,"msg":"ws connect success"}` 由 SDK 内部处理。
- `unsubscribe_kline(codes, kline_type)` 会带上 `klineTypes`，只退订该周期；
  不带的话服务端会清掉这些标的的**所有**周期。

```python
await ws.subscribe_kline("BTCUSDT", KlineType.DAY)
await ws.unsubscribe_kline("BTCUSDT", KlineType.DAY)   # 其他周期仍保持订阅
```

## 实时新闻

新闻是**独立连接**，走独立路径（`wss://data.infoway.io/news`），且需要单独开通权限。

```python
import asyncio
from infoway import InfowayNewsWebSocket, InfowayAuthError

async def main():
    news = InfowayNewsWebSocket(api_key="YOUR_API_KEY")

    async def on_news(item):
        # dk(去重键)、country、lang、route、title、published(Unix 秒)、
        # urgency(越小越急)、provider、symbols[]、link、content、sd
        print(item["title"], item["symbols"])

    news.on_news = on_news
    await news.subscribe("zh-Hans")  # en, zh-Hans, zh-Hant, ja, ko, de, fr, es, pt, ru, tr
    try:
        await news.connect()
    except InfowayAuthError as e:
        print("新闻频道不可用：", e)

asyncio.run(main())
```

说明：重复订阅会**覆盖**上一次的语言（没有单条退订）；**一个 API Key 只允许一条新闻连接**。
Key 未开通新闻权限时握手返回 HTTP 401，SDK 立即抛 `InfowayAuthError`，不会无限重连。

## REST API 模块

| 模块 | 访问方式 | 说明 |
|------|----------|------|
| Stock | `client.stock` | 港股、美股、A股 -- 成交、深度、K线 |
| Crypto | `client.crypto` | 加密货币 -- 成交、深度、K线 |
| Japan | `client.japan` | 日本市场 -- 成交、深度、K线 |
| India | `client.india` | 印度市场 -- 成交、深度、K线 |
| Korea | `client.korea` | 韩股（`.KS`）-- 成交、深度、K线 |
| Taiwan | `client.taiwan` | 台股（`.TW`）-- 成交、深度、K线 |
| Common | `client.common` | 跨市场数据 -- 成交、深度、K线 |
| Basic | `client.basic` | 标的列表、基础信息、复权因子、交易日历 |
| Packages | `client.packages` | 当前 Key 套餐额度 |
| Market | `client.market` | 温度、宽度、成交额、指数、龙头、排行 |
| Plate | `client.plate` | 行业/概念板块、成分股、板块图表 |
| Stock Info | `client.stock_info` | 基本面 -- 估值、评级、公司概况、全景、事件 |
| Financial | `client.financial` | 财报、分红、盈利 |

### `client.basic` 用法

```python
# 标的列表 —— type 必填
# STOCK_US STOCK_CN STOCK_HK STOCK_JP STOCK_KS STOCK_IN CRYPTO FOREX FUTURES
client.basic.get_symbols("STOCK_US")
client.basic.get_symbols("STOCK_US", symbols="AAPL.US,TSLA.US")

# 标的基础信息（最多 500 个）
client.basic.get_symbol_info("STOCK_US", "AAPL.US")

# 前复权因子 —— 日期为 YYYYMMDD 字符串
client.basic.get_adjustment_factors("AAPL.US", "US", "20260801", "20260814")

# 交易日历 → {"trade_days": [...], "half_trade_days": [...]}
client.basic.get_trading_days("US", "20260801", "20260831")

# 非股票品种的交易时段/假期
# type: ENERGY | FOREX | FUTURES | METAL | INDICES
client.basic.get_trading_schedule(type="METAL")
```

`get_trading_hours()` 是 `get_trading_schedule()` 的废弃别名，调用会产生 `DeprecationWarning`；
旧的 `/markets/trading_hours` 路径在服务端并不存在。

## 环境变量

```bash
export INFOWAY_API_KEY="YOUR_API_KEY"
```

```python
# 自动从环境变量读取 INFOWAY_API_KEY
client = InfowayClient()
```

### 客户端配置

```python
client = InfowayClient(
    api_key="YOUR_API_KEY",
    base_url="https://data.infoway.io",  # 默认值
    timeout=15.0,                         # 请求超时（秒）
    max_retries=3,                        # 重试次数（连接错误、超时、限流）
    parse=False,                          # 是否归一化行情返回
)
```

## 错误处理

```python
from infoway import (
    InfowayClient, InfowayAPIError, InfowayAuthError,
    InfowayRateLimitError, InfowayTimeoutError,
)

client = InfowayClient(api_key="YOUR_API_KEY")

try:
    trades = client.stock.get_trade("AAPL.US")
except InfowayAuthError:
    print("API Key 无效")
except InfowayRateLimitError:
    print("触发限流，请退避后重试")
except InfowayTimeoutError:
    print("请求超时")
except InfowayAPIError as e:
    print(f"API 错误 [{e.ret}]: {e.msg}")
```

`InfowayRateLimitError` 继承自 `InfowayAPIError`。限流也可能以 **HTTP 200** 下发，
body 为 `{"detail": "Rate limit exceeded"}` —— 旧版本会把它静默变成 `None`，
现在会正确抛出并按退避策略重试。

## 许可证

MIT

---

在 [infoway.io](https://infoway.io) 获取免费 API Key -- 7天免费试用，无需信用卡。

# Infoway SDK (中文)

[![PyPI version](https://img.shields.io/pypi/v/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | **中文**

[Infoway](https://infoway.io) 实时金融数据 API 的官方 Python SDK。完整文档请访问 [docs.infoway.io](https://docs.infoway.io)。

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

# 市场温度
temp = client.market.get_temperature(market="HK,US")

# 板块排行
plates = client.plate.get_industry("HK", limit=10)
```

## WebSocket 实时推送

```python
import asyncio
from infoway.ws import InfowayWebSocket

async def main():
    ws = InfowayWebSocket(api_key="YOUR_API_KEY", business="stock")

    async def on_trade(msg):
        print(f"成交: {msg}")

    ws.on_trade = on_trade
    await ws.subscribe_trade("AAPL.US,TSLA.US")
    await ws.connect()

asyncio.run(main())
```

### 特性

- **自动重连** -- 指数退避策略（1秒至30秒上限）
- **心跳保活** -- 每30秒自动发送心跳
- **自动重新订阅** -- 重连后自动恢复所有订阅，无需手动处理
- 事件回调：`on_trade`、`on_depth`、`on_kline`、`on_error`、`on_reconnect`、`on_disconnect`

## REST API 模块

| 模块 | 访问方式 | 说明 |
|------|----------|------|
| Stock | `client.stock` | 港股、美股、A股 -- 成交、深度、K线 |
| Crypto | `client.crypto` | 加密货币 -- 成交、深度、K线 |
| Japan | `client.japan` | 日本市场 -- 成交、深度、K线 |
| India | `client.india` | 印度市场 -- 成交、深度、K线 |
| Common | `client.common` | 跨市场数据 -- 成交、深度、K线 |
| Basic | `client.basic` | 标的列表、交易日、交易时间、复权因子 |
| Market | `client.market` | 市场温度、市场宽度、指数、龙头股、排行配置 |
| Plate | `client.plate` | 行业/概念板块、成分股、板块图表 |
| Stock Info | `client.stock_info` | 基本面 -- 估值、评级、公司概况、全景、事件 |

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
    max_retries=3,                        # 失败重试次数
)
```

## 错误处理

```python
from infoway import InfowayClient, InfowayAPIError, InfowayAuthError, InfowayTimeoutError

client = InfowayClient(api_key="YOUR_API_KEY")

try:
    trades = client.stock.get_trade("AAPL.US")
except InfowayAuthError:
    print("API Key 无效")
except InfowayTimeoutError:
    print("请求超时")
except InfowayAPIError as e:
    print(f"API 错误 [{e.ret}]: {e.msg}")
```

## 许可证

MIT

---

在 [infoway.io](https://infoway.io) 获取免费 API Key -- 7天免费试用，无需信用卡。

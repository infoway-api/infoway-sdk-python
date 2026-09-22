# Infoway Python SDK

[![PyPI version](https://img.shields.io/pypi/v/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/infoway-sdk.svg)](https://pypi.org/project/infoway-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | **中文**

Infoway 官方 Python SDK。覆盖 REST 行情、基础信息、市场概览、板块、个股、财务，以及行情 / 新闻 WebSocket。

| 项目 | 说明 |
| --- | --- |
| 包 | [`infoway-sdk==0.4.0`](https://pypi.org/project/infoway-sdk/) |
| 运行环境 | Python 3.9+ |
| REST | `https://data.infoway.io` |
| 行情 WebSocket | `wss://data.infoway.io/ws` |
| 新闻 WebSocket | `wss://data.infoway.io/news` |
| 接口频率 | [HTTP](https://docs.infoway.io/getting-started/api-limitation/http) · [WebSocket](https://docs.infoway.io/getting-started/api-limitation/websocket) |
| 错误码 | [HTTP](https://docs.infoway.io/getting-started/error-codes/http) · [WebSocket](https://docs.infoway.io/getting-started/error-codes/websocket) |
| 地址 | [行情地址](https://docs.infoway.io/getting-started/api-endpoints) |

未传入 `api_key` 时读取环境变量 `INFOWAY_API_KEY`。`InfowayClient` 是上下文管理器。

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [标的代码](#标的代码)
- [客户端](#客户端)
- [REST](#rest)
- [类型化结果](#类型化结果)
- [WebSocket](#websocket)
- [错误码](#错误码)
- [REST 路径](#rest-路径)

## 安装

```bash
pip install infoway-sdk==0.4.0
```

## 快速开始

```python
from infoway import InfowayClient, KlineType

with InfowayClient() as client:
    print(client.stock.get_trade("AAPL.US"))
    print(client.crypto.get_kline("BTCUSDT", KlineType.DAY, 30))
    print(client.packages.get_info())
```

## 标的代码

| 市场 | 格式 | 正确 | 错误 |
| --- | --- | --- | --- |
| 美股 | `{代码}.US` | `AAPL.US` | `AAPL` |
| 港股 | 5 位 + `.HK` | `00700.HK` | `700.HK` |
| A 股上海 | `{代码}.SH` | `600519.SH` | `600519.CN` |
| A 股深圳 | `{代码}.SZ` | `000001.SZ` | `000001.CN` |
| 日股 | `{代码}.JP` | `7203.JP` | |
| 韩股 | `{代码}.KS` | `005930.KS` | |
| 印股 | `{代码}.IN` | `RELIANCE.IN` | |
| 台股 | `{代码}.TW` | `2330.TW` | |
| 加密货币 | 交易对 | `BTCUSDT` | |
| 外汇 | 货币对 | `USDJPY` | |

`basic` / `financial` 的 `type` 用品种类型（`STOCK_US`、`STOCK_CN`、`CRYPTO` 等），不要传市场码 `US`。

## 客户端

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `api_key` | `INFOWAY_API_KEY` | API Key |
| `base_url` | `https://data.infoway.io` | REST 根地址 |
| `timeout` | `15` | 单次超时（秒） |
| `max_retries` | `3` | 失败重试 |
| `parse` | `False` | 是否归一化成交 / 盘口 / K 线 |

| 入口 | 用途 |
| --- | --- |
| `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common` | 成交、盘口、K 线 |
| `basic` / `packages` | 标的、日历、套餐 |
| `market` / `plate` | 市场概览、板块 |
| `stock_info` / `financial` | 个股资料、财务 |

推荐枚举：`KlineType`、`SymbolType`、`Market`、`Lang`、`NewsLang`、`PeriodType`、`Business`、`RankSort`、`SortOrder`、`ScheduleType`。

## REST

多个标的用英文逗号分隔。频率见 [HTTP接口限制](https://docs.infoway.io/getting-started/api-limitation/http)。

### 行情

| 方法 | 说明 |
| --- | --- |
| `get_trade(codes)` | 最新成交 |
| `get_depth(codes)` | 盘口 |
| `get_kline(codes, kline_type, count, timestamp=None)` | K 线 |

成交字段：`s` 代码、`p` 价格、`v` 量、`vw` 成交额、`t` 毫秒、`td` 方向。K 线在 `respList` 中，`t` 为秒。单标的最多 500 根；多标的时每个返回最近 2 根。

```python
client.stock.get_trade("AAPL.US,TSLA.US")
client.crypto.get_depth("BTCUSDT")
client.korea.get_trade("005930.KS")
client.taiwan.get_trade("2330.TW")
client.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 100)
```

| 枚举 | 值 | 周期 |
| --- | --- | --- |
| `MIN_1` / `MIN_5` / `MIN_15` / `MIN_30` | 1–4 | 分钟 |
| `HOUR_1` / `HOUR_2` / `HOUR_4` | 5–7 | 小时 |
| `DAY` / `WEEK` / `MONTH` / `QUARTER` / `YEAR` | 8–12 | 日及以上 |

### 基础信息

日期 `YYYYMMDD`。`get_trading_hours` 已弃用，请用 `get_trading_schedule`。

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

### 市场 / 板块 / 个股 / 财务

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

排行 `key` 来自 `get_rank_categories`。财务需要 `symbol` + `type`。`period_type`：`fq` 季报、`fy` 年报、`fh` 中报。

## 类型化结果

构造时 `parse=True`，或单次调用传入 `parse=True`。

```python
client = InfowayClient(parse=True)
bars = client.crypto.get_kline("BTCUSDT", KlineType.MIN_1, 100)
bars[0]["c"]               # Decimal
bars[0]["t"]               # datetime (UTC)
bars[0]["turnover"]        # 由 vw 改名
bars[0]["change_percent"]  # 0.0003
```

| 原样 | 归一化 |
| --- | --- |
| 价格 / 量为字符串 | `Decimal` |
| 成交 / 盘口 `t` 毫秒；K 线 `t` 秒 | 带时区的 `datetime` |
| REST `pc` / WS `pfr` | `change_percent` |
| K 线 `respList` | 展平列表 |
| 盘口 `a`/`b` 列式 | `(价格, 数量)` |
| `vw` | `turnover` |

## WebSocket

### 行情

`business` 必须与标的市场一致。`connect()` 会阻塞，请放到 Task 中。单连接每分钟最多 60 帧，见 [WebSocket限制](https://docs.infoway.io/getting-started/api-limitation/websocket)。

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

股票成交类型：`subscribe_trade(codes, include_ty=True)`。

| 行为 | 说明 |
| --- | --- |
| 心跳 | 每 30 秒发送 `10010`，服务端不回包 |
| 重连 | 断线后自动重连并补发当前订阅 |
| `on_reconnect` | 再次连上时触发 |
| `on_disconnect` | 仅意外掉线。`close()` 不触发 |
| HTTP 401 | 停止重连 |

| 方向 | 协议号 | 说明 |
| --- | --- | --- |
| 出 | 10000 / 10003 / 10006 | 订阅成交 / 盘口 / K 线 |
| 出 | 11000 / 11001 / 11002 | 退订 |
| 出 | 10010 | 心跳 |
| 入 | 10002 / 10005 / 10008 | 推送 |
| 入 | 11010 | 退订确认 |
| 入 | 200 | 连接成功 |

ack 只表示请求被接受。多个代码必须合并成一个逗号串。

### 新闻

地址 `wss://data.infoway.io/news`，需单独授权。每个 Key 仅允许一条新闻连接。

```python
from infoway.ws import InfowayNewsWebSocket

news = InfowayNewsWebSocket(lang="zh-Hans")
news.on_news = lambda item: print(item["title"])
```

订阅 `10020`，退订 `11020`，推送 `10022`。再次订阅覆盖语言。

## 错误码

REST 看 `ret`，WebSocket 看 `code`。`508`–`514` 两套含义不同。完整列表见 [HTTP错误码](https://docs.infoway.io/getting-started/error-codes/http) 与 [WebSocket错误码](https://docs.infoway.io/getting-started/error-codes/websocket)。

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

REST 限额约 1200 次/分钟/Key。无效 Key：REST 抛 `InfowayAuthError`；WebSocket 握手 HTTP 401 且不重连。

| REST `ret` | 说明 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 500 | 服务端错误 |
| 501 / 502 | 频率超限 |
| 503 | K 线数量超限 |
| 505 | 标的数量超限 |
| 506 / 507 | 参数错误 / 缺失 |
| 508 | 标的不存在 |
| 509 | 权限过期 |
| 513 | 历史时间超出套餐 |
| 514 | 无权限 |

| WebSocket `code` | 说明 |
| --- | --- |
| 501 / 502 | 频率超限 |
| 505 / 516 | 订阅数量超限 |
| 506 / 507 | 参数错误 / 缺失 |
| 508–511 | API Key 过期 / 无效 / 为空 / 黑名单 |
| 512 | 连接数超限 |
| 513 | 心跳超时 |
| 515 | 非 JSON |
| 517–521 | 握手失败 |

## REST 路径

`{market}` = `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common`。完整列表见 [行情地址](https://docs.infoway.io/getting-started/api-endpoints)。

| 接口 | 路径 |
| --- | --- |
| 最新成交 | `GET /{market}/batch_trade/{codes}` |
| 盘口 | `GET /{market}/batch_depth/{codes}` |
| K 线 | `POST /{market}/v2/batch_kline` |
| 品种 / 日历 / 财务 | `GET /common/basic/*` |
| 市场 / 板块 / 个股 | `GET /common/v2/basic/*` |
| 套餐 | `GET /package/info` |

## 许可证

MIT。API Key：[infoway.io](https://infoway.io)。

# Infoway Python SDK 使用说明

面向量化、行情接入和基本面查询的 Python 3.9+ 使用指南。安装说明与版本变更见 [README_CN.md](README_CN.md)，官方接口定义见 [docs.infoway.io](https://docs.infoway.io)。英文对照：[USAGE.md](USAGE.md)。

- 包名：`infoway-sdk==0.3.0`
- REST 默认地址：`https://data.infoway.io`
- 行情 WebSocket：`wss://data.infoway.io/ws`
- 新闻 WebSocket：`wss://data.infoway.io/news`

---

## 目录

1. [安装与客户端](#1-安装与客户端)
2. [标的代码约定](#2-标的代码约定)
3. [REST：多市场行情](#3-rest多市场行情)
4. [REST：基础信息](#4-rest基础信息)
5. [REST：市场概览](#5-rest市场概览)
6. [REST：板块](#6-rest板块)
7. [REST：个股资料](#7-rest个股资料)
8. [REST：财务](#8-rest财务)
9. [类型化模型](#9-类型化模型)
10. [WebSocket：实时行情](#10-websocket实时行情)
11. [WebSocket：新闻](#11-websocket新闻)
12. [错误处理与限额](#12-错误处理与限额)
13. [完整示例](#13-完整示例)

---

## 1. 安装与客户端

```bash
pip install infoway-sdk==0.3.0
```

未显式传入 `api_key` 时，SDK 读取环境变量 `INFOWAY_API_KEY`。`InfowayClient` 是上下文管理器，用完请关闭。

```python
import os

from infoway import InfowayClient


def main() -> None:
    with InfowayClient(
        api_key=os.environ.get("INFOWAY_API_KEY"),
        base_url="https://data.infoway.io",  # 可省略
        timeout=15,                          # 秒，默认 15
        max_retries=3,                       # 默认 3，指数退避
        parse=False,                         # 默认 False：原样返回
    ) as client:
        print(client.crypto.get_trade("BTCUSDT"))


if __name__ == "__main__":
    main()
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `api_key` | `INFOWAY_API_KEY` | API Key |
| `base_url` | `https://data.infoway.io` | REST 根地址 |
| `timeout` | `15` | 单次请求超时（秒） |
| `max_retries` | `3` | 失败重试次数 |
| `parse` | `False` | 是否归一化成交 / 盘口 / K 线 |

入口按数据域拆分：

| 入口 | 用途 |
|------|------|
| `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common` | 成交、盘口、K 线 |
| `basic` | 标的、日历、个股档案 |
| `packages` | 当前 Key 的套餐额度 |
| `market` | 情绪、涨跌家数、换手、排行 |
| `plate` | 行业 / 概念板块 |
| `stock_info` | 估值、评级、公司资料 |
| `financial` | 财报、分红、盈利 |

原有的 `str` 参数都还在，下面这些推荐改用枚举，避免写错线上取值：

| 枚举 | 线上取值 | 用在 |
|------|----------|------|
| `KlineType` | `MIN_1`…`YEAR`（1–12） | K 线 REST / WS |
| `SymbolType` | `STOCK_US` / `STOCK_CN` / `CRYPTO`… | `basic` / `financial` / 个股档案 |
| `Market` | `HK` `US` `CN` `JP` `KS` `TW` `IN` | 市场概览、板块、日历；多市场用 `Market.join` |
| `Lang` | `EN`=`en`，`ZH_CN`=`zh-CN` | REST 的 `lang` |
| `NewsLang` | `EN` `ZH_HANS` `ZH_HANT` `JA` `KO`… | 新闻 WS |
| `PeriodType` | `FQ` / `FY` / `FH` | 财务报表 |
| `Business` / `WsBusiness` | `STOCK` `CRYPTO` `KOREA` `TAIWAN`… | 行情 WS 的 `business`（`WsBusiness` 是别名） |
| `RankSort` | `CHG` `LAST_DONE` `VOLUME`… | 排行 `sort` |
| `SortOrder` | `ASC` `DESC` | 排行 `order` |
| `ScheduleType` | `ENERGY` `FOREX` `FUTURES` `METAL` `INDICES` | 交易时间表过滤 |
| `WsCode` / `WsErrorCode` / `RestErrorCode` | 协议号 / WS 5xx / REST `ret` | 收发与错误 |

---

## 2. 标的代码约定

| 市场 | 后缀 / 形式 | 正确示例 | 错误示例 |
|------|-------------|----------|----------|
| 美股 | `.US` | `AAPL.US` | `AAPL` |
| 港股 | `.HK`，代码补足 5 位 | `00700.HK` | `700.HK` |
| A 股上海 | `.SH` | `600519.SH` | `600519.CN` |
| A 股深圳 | `.SZ` | `000001.SZ` | `000001.CN` |
| 日股 | `.JP` | `7203.JP` | |
| 韩股 | `.KS` | `005930.KS` | |
| 印股 | `.IN` | `RELIANCE.IN` | |
| 台股 | `.TW` | `2330.TW` | |
| 加密货币 | 交易对 | `BTCUSDT` | |
| 外汇等 | 货币对 | `USDJPY` | |

`basic` / `financial` / `get_stock_detail` 的 `type` 必须用产品类型，不能传市场码 `US`：

`STOCK_US` `STOCK_CN` `STOCK_HK` `STOCK_JP` `STOCK_KS` `STOCK_IN` `STOCK_TW`  
`CRYPTO` `FOREX` `FUTURES` `ENERGY` `METAL` `INDICES`

传 `market=US` 给 `get_symbols` 会得到 HTTP 400：`Required parameter 'type' is not present.`

---

## 3. REST：多市场行情

七个市场客户端方法相同，只是路径前缀不同。多个代码用英文逗号拼接。

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

成交字段：`s` 代码、`p` 价格、`v` 量、`vw` 成交额、`t` 毫秒时间戳、`td` 方向（0 默认 / 1 买 / 2 卖）。  
K 线外层是按品种包一层，K 线列表在 `respList`；`t` 是**秒**级字符串。`timestamp` 只对分钟 / 小时 K 有意义。

| 枚举 | 值 | 周期 |
|------|----|------|
| `MIN_1` / `MIN_5` / `MIN_15` / `MIN_30` | 1–4 | 分钟 |
| `HOUR_1` / `HOUR_2` / `HOUR_4` | 5–7 | 小时 |
| `DAY` / `WEEK` / `MONTH` / `QUARTER` / `YEAR` | 8–12 | 日及以上 |

K 线单品种最多 **500** 根；多品种请求会被服务端截成每个品种 2 根。

SDK 一律走 `POST /{market}/v2/batch_kline`。

---

## 4. REST：基础信息

日期一律 `YYYYMMDD`。

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

`get_trading_hours` 已弃用，请用 `get_trading_schedule`。交易时间表没有市场过滤；`get_trading_schedule("US")` 与无参相同。按品种过滤用 `ScheduleType`（`ENERGY` / `FOREX` / `FUTURES` / `METAL` / `INDICES`）。向 `get_trading_schedule_by_type` 传入 `SymbolType.STOCK_US` 会在发请求前抛 `ValueError`。

`packages.get_info()` 返回当前 Key 的套餐：`packageName`、`expireTime`、`apiNumPerSec`、`maxWsConNum`、`maxNum`、`maxYearHisData`、`allWsNum`。

---

## 5. REST：市场概览

`market` 用 `Market`，`lang` 用 `Lang`。温度接口可一次传多个市场（`Market.join` 或逗号串）。

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

排行榜的 `key` 来自 `get_rank_categories`。`get_rank_config` 已弃用（服务端 404）。

---

## 6. REST：板块

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

## 7. REST：个股资料

均支持可选 `lang`：`en` 或 `zh-CN`。

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

## 8. REST：财务

每个方法都要 `symbol` + `type`。报表类可带 `period_type`：

| 值 | 含义 |
|----|------|
| `fq` | 季报 |
| `fy` | 年报 |
| `fh` | 中报 |

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

港股示例：`client.financial.get_dividend("00700.HK", SymbolType.STOCK_HK)`。

---

## 9. 类型化模型

默认返回服务端原样（`list` / `dict`）。需要 SDK 消化字段差异时，在客户端或 `get_trade` / `get_depth` / `get_kline` 上设 `parse=True`。

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

        raw_client = InfowayClient()
        parsed = raw_client.crypto.get_trade("BTCUSDT", parse=True)
        print(parsed[0]["p"])


if __name__ == "__main__":
    main()
```

| 线上原样 | 归一化后 |
|----------|----------|
| 价格 / 量是字符串 `"305.771"` | `Decimal` |
| 成交 / 盘口 `t` 为毫秒数字；K 线 `t` 为秒字符串 | 带时区的 `datetime` |
| REST 涨跌幅 `pc`、WS 涨跌幅 `pfr`，值为 `"0.03%"` | `change_percent = 0.0003` |
| K 线多套 `respList` | 展平为蜡烛列表 |
| 盘口 `a`/`b` 是 `[[价格…],[数量…]]` | `[(price, qty), …]` |
| `vw` 实际是成交额 | `turnover` |

---

## 10. WebSocket：实时行情

独立于 REST 客户端。`business` 必须和市场一致，订错频道会 ack 成功但永远不推数据。

`print_frames` 默认 **false**：入站帧只写 DEBUG。调试时用 `print_frames=True`，或自己挂 `on_frame`。REST 和 WebSocket 都可以不传 `api_key`，此时读环境变量 `INFOWAY_API_KEY`。`connect()` 会阻塞到 `close()`，请放到 Task 里跑。

行情回调（`on_trade` / `on_depth` / `on_kline` / `on_error`）必须是 **async**，客户端会 `await` 它们。

```python
import asyncio
import os

from infoway import Business, InfowayWebSocket, KlineType


async def main() -> None:
    ws = InfowayWebSocket(
        api_key=os.environ.get("INFOWAY_API_KEY"),
        business=Business.CRYPTO,  # stock / japan / india / korea / taiwan / crypto / common
        print_frames=True,         # 可选：打印服务端全部回包，默认 False
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

股票成交类型（碎股、竞价等）需要 `include_ty=True`。加密货币即使打开也不会出 `ty` 字段。

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

回调拿到的是 **`data` 本体**，不是 `{"code":10002,"data":{...}}`。可在 `connect()` 之前订阅，连上后会补发。

生命周期（重连 / 订阅 / 关闭）：

- 心跳 `10010` 每 30 秒一次，**每个存活会话只启一个任务**。一次掉线最多安排 **一次** 重连（1 秒起、30 秒封顶）。
- `on_reconnect` 只在**再次**连上时触发，首次 `connect()` 不会调用。
- `on_disconnect` 只表示意外掉线（含对端干净关断）。`close()` **不**触发它、也**不**重连，并会打断退避睡眠，关闭马上返回。
- 客户端保存的是**目标订阅集**。已退订的内容重连后不会再发；重连窗口里的新订阅会在下一跳补发。K 线按周期退订，其它周期保留。
- HTTP 401 仍然停止重连。

| 现象 | 原因 |
|------|------|
| 首帧纯文本 `You have permission...` | `business=stock` 的欢迎文本，SDK 会跳过 |
| `{"code":200,"msg":"ws connect success"}` | 欢迎帧，不是错误 |
| ack `ok` 之后一直没数据 | business 订错、代码不存在或休市；ack 只表示请求被接受 |
| 心跳没有回包 | 服务端对 `10010` 不响应，不要用“等心跳超时”判断断线 |
| 发了很多帧后被踢 | 单连接 **60 帧/分钟**（订阅 + 退订 + 心跳合计），多个代码必须合并成一个逗号串 |
| HTTP 401 | Key 无效或没有该频道权限；抛 `InfowayAuthError` 并停止重连 |

协议号：

| 方向 | 码 | 含义 |
|------|----|------|
| 出 | 10000 / 10003 / 10006 | 订阅成交 / 盘口 / K 线 |
| 出 | 11000 / 11001 / 11002 | 退订 |
| 出 | 10010 | 心跳（30 秒一次；带 `ack=1` 才会收到 10011） |
| 入 | 10001 / 10004 / 10007 | 订阅确认 |
| 入 | 10002 / 10005 / 10008 | 实时推送 |
| 入 | 10011 | 心跳确认（可选） |
| 入 | 11010 | 退订确认（成交/盘口/K线/新闻共用） |
| 入 | 200 | 欢迎帧 |
| 入 | 500–521 | 服务端错误，回调 `on_error`（501/502 为限流；见 `WsErrorCode`） |

---

## 11. WebSocket：新闻

新闻走独立地址 `wss://data.infoway.io/news`，需要单独授权。一个 Key 只允许一条新闻连接。

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

    await news.unsubscribe()  # 协议号 11020
    await news.subscribe(NewsLang.EN)  # 再次订阅会覆盖语言
    await news.close()
    await runner


if __name__ == "__main__":
    asyncio.run(main())
```

推送字段：`dk`（去重）、`country`、`lang`、`route`、`title`、`published`（**秒**）、`urgency`（越小越急）、`provider`、`symbols[]`、`link`、`content`、`sd`（摘要）。

`on_news_parsed` 总会把 `published` 转成带时区的 `datetime`。`on_news` 默认是原样；构造时 `parse=True` 才会归一化。

| 方向 | 码 | 含义 |
|------|----|------|
| 出 | 10020 / 11020 | 订阅 / 退订 |
| 入 | 10021 / 10022 | 确认 / 推送 |

没有新闻权限的 Key 会在握手阶段收到 HTTP 401。当前 `lang` 会在重连时回放；`unsubscribe()` 清空语言后重连不再订阅。`on_reconnect` / `on_disconnect` 规则与行情通道相同。

---

## 12. 错误处理与限额

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
        print("认证失败:", e.msg)
    except InfowayRateLimitError as e:
        print(f"限流 [{e.ret} {e.error_name}] {e.msg}")
    except InfowayTimeoutError as e:
        print("超时:", e)
    except InfowayIoError as e:
        print("网络:", e)
    except InfowayAPIError as e:
        # HTTP: RestErrorCode；WS: WsErrorCode。508–514 同号不同义。
        print(e)
        print(f"ret={e.ret} name={e.error_name} msg={e.msg} trace={e.trace_id}")


if __name__ == "__main__":
    main()
```

`InfowayRateLimitError` 继承 `InfowayAPIError`。REST 限额约 **1200 次/分钟/Key**。HTTP 429、REST `ret` 501/502，或 body 为 `{"detail":"Rate limit exceeded"}` 时，SDK 会先退避再重试。

`str(e)` 会带上码和枚举名，例如 REST `[508 PRODUCT_NOT_EXISTS] All product not exists`，WebSocket `[508 APIKEY_EXPIRED] …`。不要用 `WsErrorCode` 去解 REST 的 `ret`。

### REST `ret`（`RestErrorCode`）

| 码 | 名称 | 说明 |
|----|------|------|
| 200 | SUCCESS | 成功 |
| 400 | BAD_REQUEST | commonApi 参数错误（HTTP 也是 400） |
| 500 | SERVER_ERROR | 未捕获异常；或旧实现把业务错误写成了 500 |
| 501 / 502 | REQUEST_EXCEED_LIMIT / REQUEST_FOR_DAY_LIMIT | 限流 → `InfowayRateLimitError` |
| 503 | KLINE_EXCEEDS_LIMIT | K 线根数超限 |
| 505 | PRODUCTS_EXCEEDS_LIMIT | 品种数超限 |
| 506 / 507 | PARAM_ERROR / PARAM_LOST | 参数错误 / 缺失 |
| **508** | **PRODUCT_NOT_EXISTS** | **品种不存在**（不是 WS 的 key 过期） |
| 509 | TOKEN_PERMISSION_EXPIRED | token 权限过期 |
| 513 | TIME_LIMIT_ERROR | K 线 `timestamp` 超出历史深度 |
| **514** | **NO_PERMISSION** | **无该市场权限**（不是 WS 的 URL 错误） |

commonApi（`/common/basic/*`）只有 200 / 400 / 500。

伪造 Key 时：REST 抛 `InfowayAuthError` `[401] Token invalid`；行情 / 新闻 WebSocket 握手 HTTP 401，**不会重连**。

对照生产（2026-09-21）：行情业务错误目前仍是 **HTTP 200 + `ret=500`**，英文模板在 `msg` 里（`All product not exists`、`Param error：klineType`、`Timestamp limit error…`、`Kline quantity exceeds the limit：500`）。SDK 会带上 **message**。生产对部分财务过滤较松：`type=US` 仍可能按后缀返回 `AAPL.US` 行；`period_type=xx` 返回 HTTP 200 + 空列表；`get_stock_detail(..., CRYPTO)` 是 HTTP 200 且 `data: null`。

### WebSocket `code`（`WsErrorCode`）

| 码 | 名称 | 说明 |
|----|------|------|
| 501 / 502 | REQUEST_FREQUENCY_MIN_EXCEED / DAY | 单连接 60 帧/分钟等 → `InfowayRateLimitError` |
| 505 / 516 | PRODUCTS_QUANTITY_EXCEED | 单连接 / 该 Key 全部连接 |
| 506 / 507 | PARAM_ERROR / PARAM_LOST | 参数错误或缺失 |
| **508–511** | **APIKEY_*** | **过期 / 无效 / 空 / 黑名单** |
| 512 / 513 / 514 | 连接超限 / 心跳超时 / URL 错误 | 513 后服务端会断开 |
| 515 | PARAM_NOT_JSON | 入站不是 JSON |
| 517–521 | 握手失败 | 缺 key / 无权限；519/520 在韩股、台股、新闻上含义不同 |

---

## 13. 完整示例

把 REST 快照和 WebSocket 推送放在同一个进程里：先拉一笔现价，再挂实时成交。

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
        raise SystemExit("请先设置环境变量 INFOWAY_API_KEY")

    try:
        with InfowayClient(api_key=api_key) as client:
            trades = client.crypto.get_trade("BTCUSDT", parse=True)
            print("REST 现价:", trades[0]["p"])

            print("公司资料:", client.stock_info.get_company("AAPL.US", "zh-CN"))
            print(
                "盈利状态:",
                client.financial.get_earning_status("AAPL.US", SymbolType.STOCK_US),
            )
            print("日K:", client.crypto.get_kline("BTCUSDT", KlineType.DAY, 5))
            print("套餐:", client.packages.get_info())
    except InfowayAPIError as e:
        print(e)
        return

    first_tick = asyncio.Event()
    ws = InfowayWebSocket(api_key=api_key, business="crypto")

    async def on_trade(data):
        print("WS 成交:", data)
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
        print("45 秒内没有成交推送")
    finally:
        await ws.close()
        await runner


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
export INFOWAY_API_KEY=your-key
python infoway_quickstart.py
```

实盘契约测试：

```bash
cd sdks/python
INFOWAY_API_KEY=your-key pytest tests/test_live_contract.py -m live
```

---

## 附录：REST 路径一览

行情（`{market}` = `stock` / `crypto` / `japan` / `india` / `korea` / `taiwan` / `common`）：

- `GET /{market}/batch_trade/{codes}`
- `GET /{market}/batch_depth/{codes}`
- `POST /{market}/v2/batch_kline`

基础 / 财务：

- `GET /common/basic/symbols`
- `GET /common/basic/symbols/info`
- `GET /common/basic/symbols/adjustment_factors`
- `GET /common/basic/markets/trading_days`
- `GET /common/basic/markets/trading_schedule`
- `GET /common/basic/markets`
- `GET /common/basic/stock/detail`
- `GET /common/basic/financial/{earning_status|income_statement|revenue|cash_flow|balance_sheet|statistics|dividend|dividend_payout|earnings}`
- `GET /package/info`

市场 / 板块 / 个股：

- `GET /common/v2/basic/market/{temperature|indexes}`
- `GET /common/v2/basic/market/{breadth|turnover|leaders|overview|rank/categories}/{market}`
- `GET /common/v2/basic/market/rank/{market}/{key}`
- `GET /common/v2/basic/plate/{industry|concept|chart}/{market}`
- `GET /common/v2/basic/plate/{members|intro}/{plateSymbol}`
- `GET /common/v2/basic/stock/{valuation|ratings|company|panorama|concepts|events|drivers}/{symbol}`

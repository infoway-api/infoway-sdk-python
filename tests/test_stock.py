"""client.stock.* — asserted against verbatim production payloads."""

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway._types import KlineType
from infoway.exceptions import InfowayAPIError
from infoway.rest.stock import StockClient
from tests.conftest import load_json


@pytest.fixture
def stock():
    return StockClient(HttpClient(api_key="test-key", max_retries=1))


@respx.mock
def test_get_trade(stock):
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_trade.json"))
    )
    [row] = stock.get_trade("AAPL.US")
    assert row["s"] == "AAPL.US"
    assert row["p"] == "305.771"     # prices arrive as STRINGS
    assert row["v"] == "1"
    assert row["vw"] == "305.771"    # turnover, despite the name
    assert row["t"] == 1786751999691  # milliseconds
    assert row["td"] == 0
    assert "price" not in row and "symbol" not in row


@respx.mock
def test_get_trade_multiple_codes_go_in_one_path_segment(stock):
    route = respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US,TSLA.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_trade.json"))
    )
    stock.get_trade("AAPL.US,TSLA.US")
    assert route.calls[0].request.url.path == "/stock/batch_trade/AAPL.US,TSLA.US"


@respx.mock
def test_get_depth_returns_column_major_a_b(stock):
    respx.get("https://data.infoway.io/stock/batch_depth/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_depth.json"))
    )
    [row] = stock.get_depth("AAPL.US")
    assert row["s"] == "AAPL.US"
    # the server sends a/b as [[prices...],[qtys...]] — NOT asks/bids
    assert "asks" not in row and "bids" not in row
    assert row["a"] == [["305.800"], ["229"]]
    assert row["b"] == [["305.770"], ["24"]]


@respx.mock
def test_get_kline_nests_candles_under_resplist(stock):
    route = respx.post("https://data.infoway.io/stock/v2/batch_kline").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_kline.json"))
    )
    [row] = stock.get_kline("AAPL.US", kline_type=KlineType.MIN_1, count=2)
    body = load_json_body(route)
    assert body == {"codes": "AAPL.US", "klineType": 1, "klineNum": 2}
    assert "kline" not in row, "the server key is respList"
    candle = row["respList"][0]
    assert candle["o"] == "305.830"
    assert candle["c"] == "305.930"
    assert candle["t"] == "1786737540"   # STRING, seconds
    assert candle["pc"] == "0.03%"       # REST names it pc (WS names it pfr)
    assert candle["vw"] == "101402874.954"


@respx.mock
def test_get_kline_accepts_plain_int(stock):
    route = respx.post("https://data.infoway.io/stock/v2/batch_kline").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_kline.json"))
    )
    stock.get_kline("AAPL.US", kline_type=8, count=5)
    assert load_json_body(route)["klineType"] == 8


@respx.mock
def test_unknown_symbol_raises(stock):
    """A missing market suffix (or a HK code not padded to 5 digits) → ret 500."""
    respx.get("https://data.infoway.io/stock/batch_trade/700.HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/envelope_ret500.json"))
    )
    with pytest.raises(InfowayAPIError) as exc:
        stock.get_trade("700.HK")
    assert exc.value.msg == "All product not exists"


def load_json_body(route):
    import json

    return json.loads(route.calls[0].request.content)

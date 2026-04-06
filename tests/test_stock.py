import httpx
import respx
import pytest
from infoway._http import HttpClient
from infoway.rest.stock import StockClient
from infoway._types import KlineType


@pytest.fixture
def stock():
    http = HttpClient(api_key="test-key")
    return StockClient(http)


@respx.mock
def test_get_trade(stock):
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "data": [
                {"s": "AAPL.US", "p": "150.00", "v": "100", "t": 1700000000000}
            ]
        })
    )
    result = stock.get_trade("AAPL.US")
    assert result[0]["s"] == "AAPL.US"


@respx.mock
def test_get_trade_multiple(stock):
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US,TSLA.US").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "data": [
                {"s": "AAPL.US", "p": "150.00"},
                {"s": "TSLA.US", "p": "250.00"},
            ]
        })
    )
    result = stock.get_trade("AAPL.US,TSLA.US")
    assert len(result) == 2


@respx.mock
def test_get_depth(stock):
    respx.get("https://data.infoway.io/stock/batch_depth/AAPL.US").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "data": [
                {"s": "AAPL.US", "asks": [], "bids": []}
            ]
        })
    )
    result = stock.get_depth("AAPL.US")
    assert result[0]["s"] == "AAPL.US"


@respx.mock
def test_get_kline(stock):
    respx.post("https://data.infoway.io/stock/v2/batch_kline").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "data": [
                {"s": "AAPL.US", "kline": [{"t": 1700000000, "o": "150"}]}
            ]
        })
    )
    result = stock.get_kline("AAPL.US", kline_type=KlineType.DAY, count=10)
    assert result[0]["kline"][0]["o"] == "150"


@respx.mock
def test_get_kline_with_int(stock):
    respx.post("https://data.infoway.io/stock/v2/batch_kline").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "success", "data": []})
    )
    result = stock.get_kline("AAPL.US", kline_type=8, count=5)
    assert result == []

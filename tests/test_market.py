import httpx, respx, pytest
from infoway._http import HttpClient
from infoway.rest.market import MarketClient

@pytest.fixture
def market():
    return MarketClient(HttpClient(api_key="test-key"))

@respx.mock
def test_get_temperature(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/temperature").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"list":[{"market":"HK","temp":"69"}]}}))
    assert market.get_temperature(market="HK") is not None

@respx.mock
def test_get_breadth(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/breadth/HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"rise_less_than_three":816}}))
    assert market.get_breadth("HK") is not None

@respx.mock
def test_get_indexes(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/indexes").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[{"name":"S&P 500"}]}))
    assert market.get_indexes()[0]["name"] == "S&P 500"

@respx.mock
def test_get_leaders(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/leaders/HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[{"name":"Banking"}]}))
    assert market.get_leaders("HK", limit=5)[0]["name"] == "Banking"

@respx.mock
def test_get_rank_config(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/rank-config/HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"market":"HK"}}))
    assert market.get_rank_config("HK")["market"] == "HK"

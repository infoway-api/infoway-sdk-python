import httpx, respx, pytest
from infoway._http import HttpClient
from infoway.rest.stock_info import StockInfoClient

@pytest.fixture
def stock_info():
    return StockInfoClient(HttpClient(api_key="test-key"))

@respx.mock
def test_get_valuation(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/valuation/700.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"symbol":"00700.HK","data":{"pe_list":[]}}}))
    assert stock_info.get_valuation("700.HK")["symbol"] == "00700.HK"

@respx.mock
def test_get_ratings(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/ratings/700.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"elist":[]}}))
    assert stock_info.get_ratings("700.HK") is not None

@respx.mock
def test_get_company(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/company/AAPL.US").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"name":"Apple Inc."}}))
    assert stock_info.get_company("AAPL.US") is not None

@respx.mock
def test_get_panorama(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/panorama/700.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"symbol":"00700.HK"}}))
    assert stock_info.get_panorama("700.HK") is not None

@respx.mock
def test_get_concepts(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/concepts/700.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"concept":{"tags":[]}}}))
    assert stock_info.get_concepts("700.HK") is not None

@respx.mock
def test_get_events(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/events/700.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[]}))
    assert stock_info.get_events("700.HK", limit=5) == []

@respx.mock
def test_get_drivers(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/drivers/700.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"drivers":[]}}))
    assert stock_info.get_drivers("700.HK") is not None

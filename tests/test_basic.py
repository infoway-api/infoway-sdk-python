import httpx, respx, pytest
from infoway._http import HttpClient
from infoway.rest.basic import BasicClient

@pytest.fixture
def basic():
    return BasicClient(HttpClient(api_key="test-key"))

@respx.mock
def test_get_symbols(basic):
    respx.get("https://data.infoway.io/common/basic/symbols").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[{"code":"AAPL.US"}]}))
    assert basic.get_symbols()[0]["code"] == "AAPL.US"

@respx.mock
def test_get_symbols_with_market(basic):
    respx.get("https://data.infoway.io/common/basic/symbols").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[]}))
    basic.get_symbols(market="US")

@respx.mock
def test_get_symbol_info(basic):
    respx.get("https://data.infoway.io/common/basic/symbols/info").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"AAPL.US":{"name":"Apple"}}}))
    result = basic.get_symbol_info(codes="AAPL.US")
    assert "AAPL.US" in str(result)

@respx.mock
def test_get_trading_days(basic):
    respx.get("https://data.infoway.io/common/basic/markets/trading_days").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[{"date":"2026-04-06"}]}))
    assert basic.get_trading_days(market="US")[0]["date"] == "2026-04-06"

@respx.mock
def test_get_trading_hours(basic):
    respx.get("https://data.infoway.io/common/basic/markets").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[{"market":"US"}]}))
    assert basic.get_trading_hours()[0]["market"] == "US"

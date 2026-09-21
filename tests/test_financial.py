import httpx
import pytest
import respx

from infoway import PeriodType, SymbolType
from infoway._http import HttpClient
from infoway.rest.financial import FinancialClient


@pytest.fixture
def financial():
    return FinancialClient(HttpClient(api_key="test-key", max_retries=1))


@respx.mock
def test_earning_status_and_income_statement(financial):
    route = respx.get("https://data.infoway.io/common/basic/financial/income_statement").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": []})
    )
    respx.get("https://data.infoway.io/common/basic/financial/earning_status").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {}})
    )
    financial.get_earning_status("AAPL.US", SymbolType.STOCK_US)
    financial.get_income_statement("AAPL.US", SymbolType.STOCK_US, PeriodType.FQ)
    params = route.calls[0].request.url.params
    assert params["symbol"] == "AAPL.US"
    assert params["type"] == "STOCK_US"
    assert params["period_type"] == "fq"


@respx.mock
def test_period_type_omitted_when_none(financial):
    route = respx.get("https://data.infoway.io/common/basic/financial/dividend").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": []})
    )
    financial.get_dividend("00700.HK", SymbolType.STOCK_HK)
    assert "period_type" not in route.calls[0].request.url.params

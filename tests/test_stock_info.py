"""client.stock_info.* — asserted against verbatim production payloads."""

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.rest.stock_info import StockInfoClient
from tests.conftest import load_json


@pytest.fixture
def stock_info():
    return StockInfoClient(HttpClient(api_key="test-key", max_retries=1))


@respx.mock
def test_get_valuation(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/valuation/02016.HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_valuation.json"))
    )
    result = stock_info.get_valuation("02016.HK")
    assert result["kline_type"] == "day"
    assert result["pe_list"][0]["pe"] == "4.63"
    assert result["pe_list"][0]["timestamp"] == "1755187200"  # seconds, as a string


@respx.mock
def test_get_ratings(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/ratings/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_ratings.json"))
    )
    result = stock_info.get_ratings("AAPL.US")
    first = result["elist"][0]
    assert {"buy", "over", "hold", "under", "sell", "total", "date"} <= set(first)
    assert isinstance(first["buy"], str), "rating counts arrive as strings"


@respx.mock
def test_get_company(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/company/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_company.json"))
    )
    result = stock_info.get_company("AAPL.US")
    assert result["basic_info"]["name"] == "Apple"


@respx.mock
def test_get_panorama(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/panorama/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_panorama.json"))
    )
    result = stock_info.get_panorama("AAPL.US")
    assert result["belonged_industry"]["counter_id"] == "BK/US/IN00350"


@respx.mock
def test_get_concepts_chg_is_a_percentage_not_a_ratio(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/concepts/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_concepts.json"))
    )
    result = stock_info.get_concepts("AAPL.US")
    tag = result["concept"]["tags"][0]
    assert tag["counter_id"] == "BK/US/CP00054"
    # note: here chg is a PERCENTAGE ("-0.478...%"), while plate.* chg is a ratio
    assert abs(float(tag["chg"])) > 0.1


@respx.mock
def test_get_events(stock_info):
    route = respx.get("https://data.infoway.io/common/v2/basic/stock/events/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_events.json"))
    )
    result = stock_info.get_events("AAPL.US", limit=20)
    assert route.calls[0].request.url.params["limit"] == "20"
    # real keys are id/date/date_type/act_type/act_desc — not event_type/event_date
    first = result["items"][0]
    assert {"id", "date", "date_type", "act_type", "act_desc"} <= set(first)
    assert first["date"] == "20260511"   # YYYYMMDD string, not a timestamp


@respx.mock
def test_get_drivers(stock_info):
    respx.get("https://data.infoway.io/common/v2/basic/stock/drivers/02016.HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_drivers.json"))
    )
    result = stock_info.get_drivers("02016.HK")
    assert result["counter_id"] == "ST/HK/2016"
    assert result["node"]["title"] == "CZBANK"

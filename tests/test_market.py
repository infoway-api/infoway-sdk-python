"""client.market.* — asserted against verbatim production payloads."""

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.exceptions import InfowayAPIError
from infoway.rest.market import MarketClient
from tests.conftest import load_json


@pytest.fixture
def market():
    return MarketClient(HttpClient(api_key="test-key", max_retries=1))


@respx.mock
def test_get_temperature(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/temperature").mock(
        return_value=httpx.Response(200, json=load_json("rest/market_temperature.json"))
    )
    result = market.get_temperature(market="HK,US")
    first = result["list"][0]
    assert {"temp", "temp_intro", "valuation", "sentiment", "market"} <= set(first)


@respx.mock
def test_get_breadth(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/breadth/US").mock(
        return_value=httpx.Response(200, json=load_json("rest/market_breadth.json"))
    )
    result = market.get_breadth("US")
    assert result["flatline"] == 2847
    assert result["rise_less_than_three"] == 5027


@respx.mock
def test_get_indexes(market):
    respx.get("https://data.infoway.io/common/v2/basic/market/indexes").mock(
        return_value=httpx.Response(200, json=load_json("rest/market_indexes.json"))
    )
    result = market.get_indexes()
    assert result["indexes"][0]["counter_id"] == "IX/US/.DJI"


@respx.mock
def test_get_leaders_is_nested_one_level_deeper_than_documented(market):
    route = respx.get("https://data.infoway.io/common/v2/basic/market/leaders/HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/market_leaders.json"))
    )
    result = market.get_leaders("HK", limit=2)
    assert route.calls[0].request.url.params["limit"] == "2"
    # real shape is data.lists[].lists[] — one level more than the docs claim
    assert result["lists"][0]["market"] == "HK"
    assert result["lists"][0]["lists"][0]["counter_id"].startswith("BK/HK/")


@respx.mock
def test_get_rank_config_404_raises(market):
    """The rank-config route does not exist on the server (HTTP 404 + {"detail"})."""
    respx.get("https://data.infoway.io/common/v2/basic/market/rank-config/US").mock(
        return_value=httpx.Response(404, json=load_json("rest/market_rank_config_404.json"))
    )
    with pytest.raises(InfowayAPIError) as exc:
        market.get_rank_config("US")
    assert exc.value.ret == 404
    assert exc.value.msg == "Not Found"


@respx.mock
def test_get_turnover_overview_and_rank(market):
    from infoway import Lang, Market, RankSort, SortOrder

    respx.get("https://data.infoway.io/common/v2/basic/market/turnover/US").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {}})
    )
    respx.get("https://data.infoway.io/common/v2/basic/market/overview/US").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {}})
    )
    respx.get("https://data.infoway.io/common/v2/basic/market/rank/categories/US").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": []})
    )
    route = respx.get("https://data.infoway.io/common/v2/basic/market/rank/US/all").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": []})
    )
    market.get_turnover(Market.US)
    market.get_overview(Market.US, Lang.ZH_CN)
    market.get_rank_categories(Market.US)
    market.get_rank(Market.US, "all", RankSort.CHG, SortOrder.DESC, 30, 0, Lang.EN)
    params = route.calls[0].request.url.params
    assert params["sort"] == "chg"
    assert params["order"] == "desc"
    assert params["limit"] == "30"

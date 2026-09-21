"""client.plate.* — asserted against verbatim production payloads."""

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.rest.plate import PlateClient
from tests.conftest import load_json


@pytest.fixture
def plate():
    return PlateClient(HttpClient(api_key="test-key", max_retries=1))


@respx.mock
def test_get_industry(plate):
    route = respx.get("https://data.infoway.io/common/v2/basic/plate/industry/HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/plate_industry.json"))
    )
    result = plate.get_industry("HK", limit=2)
    assert route.calls[0].request.url.params["limit"] == "2"
    assert result[0]["symbol"] == "IN20234.HK"
    assert result[0]["type"] == "industry"
    assert result[0]["chg"] == "0.1388"   # plate chg is a RATIO string


@respx.mock
def test_get_concept(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/concept/HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/plate_concept.json"))
    )
    result = plate.get_concept("HK", limit=2)
    assert result[0]["symbol"].startswith("CP")
    assert result[0]["type"] == "concept"


@respx.mock
def test_get_members(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/members/IN20293.HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/plate_members.json"))
    )
    result = plate.get_members("IN20293.HK", limit=2)
    assert result["total"] == 18
    assert result["members"][0]["symbol"] == "02016.HK"


@respx.mock
def test_get_intro_has_no_data_key(plate):
    """/plate/intro answers {"plate","intro"} — no envelope, no "data" key."""
    respx.get("https://data.infoway.io/common/v2/basic/plate/intro/IN20293.HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/envelope_no_data_key.json"))
    )
    result = plate.get_intro("IN20293.HK")
    assert result["plate"] == "IN20293.HK"
    assert result["intro"].startswith("Large, geographically diverse banks")


@respx.mock
def test_get_chart(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/chart/HK").mock(
        return_value=httpx.Response(200, json=load_json("rest/plate_chart.json"))
    )
    result = plate.get_chart("HK", limit=2)
    assert result[0]["symbol"] == "IN20293.HK"
    assert "market_weight" in result[0]

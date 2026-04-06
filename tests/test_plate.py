import httpx, respx, pytest
from infoway._http import HttpClient
from infoway.rest.plate import PlateClient

@pytest.fixture
def plate():
    return PlateClient(HttpClient(api_key="test-key"))

@respx.mock
def test_get_industry(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/industry/HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"data":[{"symbol":"IN20293.HK"}]}}))
    assert plate.get_industry("HK") is not None

@respx.mock
def test_get_concept(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/concept/HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"data":[{"symbol":"CP20027.HK"}]}}))
    assert plate.get_concept("HK") is not None

@respx.mock
def test_get_members(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/members/IN20293.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"members":[{"symbol":"939.HK"}]}}))
    assert plate.get_members("IN20293.HK") is not None

@respx.mock
def test_get_intro(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/intro/IN20293.HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":{"intro":"Banking sector"}}))
    assert plate.get_intro("IN20293.HK")["intro"] == "Banking sector"

@respx.mock
def test_get_chart(plate):
    respx.get("https://data.infoway.io/common/v2/basic/plate/chart/HK").mock(
        return_value=httpx.Response(200, json={"ret":200,"msg":"success","data":[{"symbol":"IN20293.HK","chg":"0.02"}]}))
    assert plate.get_chart("HK") is not None

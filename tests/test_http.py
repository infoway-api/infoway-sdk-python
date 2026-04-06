import pytest
import httpx
import respx
from infoway._http import HttpClient
from infoway.exceptions import InfowayAPIError, InfowayAuthError, InfowayTimeoutError


@pytest.fixture
def client():
    return HttpClient(api_key="test-key", base_url="https://data.infoway.io")


@respx.mock
def test_get_success(client):
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "traceId": "t1",
            "data": [{"s": "AAPL.US", "p": "150.00"}]
        })
    )
    result = client.get("/stock/batch_trade/AAPL.US")
    assert result == [{"s": "AAPL.US", "p": "150.00"}]


@respx.mock
def test_post_success(client):
    respx.post("https://data.infoway.io/stock/v2/batch_kline").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "traceId": "t2",
            "data": [{"s": "AAPL.US", "kline": []}]
        })
    )
    result = client.post("/stock/v2/batch_kline", json={"codes": "AAPL.US"})
    assert result[0]["s"] == "AAPL.US"


@respx.mock
def test_auth_error(client):
    respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(200, json={
            "ret": 401, "msg": "Unauthorized", "traceId": "t3", "data": None
        })
    )
    with pytest.raises(InfowayAuthError):
        client.get("/test")


@respx.mock
def test_api_error(client):
    respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(200, json={
            "ret": 500, "msg": "server error", "traceId": "t4", "data": None
        })
    )
    with pytest.raises(InfowayAPIError) as exc_info:
        client.get("/test")
    assert exc_info.value.ret == 500


@respx.mock
def test_sends_api_key_header(client):
    route = respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {}})
    )
    client.get("/test")
    assert route.calls[0].request.headers["apiKey"] == "test-key"


@respx.mock
def test_retry_on_failure(client):
    route = respx.get("https://data.infoway.io/test")
    route.side_effect = [
        httpx.ConnectError("fail"),
        httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {"ok": True}}),
    ]
    result = client.get("/test")
    assert result == {"ok": True}
    assert route.call_count == 2

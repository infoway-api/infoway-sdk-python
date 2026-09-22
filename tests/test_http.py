"""Response-handling layer — the 5 real production envelopes.

Every payload here is a verbatim capture from https://data.infoway.io
(tests/fixtures/rest/*.json). See docs/specs/2026-08-15-sdk-contract-fix-design.md §1.
"""

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.exceptions import (
    InfowayAPIError,
    InfowayAuthError,
    InfowayRateLimitError,
    InfowayTimeoutError,
)
from tests.conftest import load_json, load_text


@pytest.fixture
def client():
    # max_retries=1 keeps the retry backoff out of the unit tests
    return HttpClient(api_key="test-key", base_url="https://data.infoway.io", max_retries=1)


# --------------------------------------------------------------------------
# Envelope 1 — standard {"ret","msg","traceId","data"}
# --------------------------------------------------------------------------

@respx.mock
def test_envelope1_standard_returns_data(client):
    body = load_json("rest/stock_trade.json")
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US").mock(
        return_value=httpx.Response(200, json=body)
    )
    result = client.get("/stock/batch_trade/AAPL.US")
    # real field names: s / t / p / v / vw / td  (NOT "symbol", NOT "price")
    assert result == [
        {"s": "AAPL.US", "t": 1786751999691, "p": "305.771", "v": "1", "vw": "305.771", "td": 0}
    ]


@respx.mock
def test_envelope1_kline_uses_resplist(client):
    body = load_json("rest/stock_kline.json")
    respx.post("https://data.infoway.io/stock/v2/batch_kline").mock(
        return_value=httpx.Response(200, json=body)
    )
    result = client.post("/stock/v2/batch_kline", json={"codes": "AAPL.US"})
    assert result[0]["s"] == "AAPL.US"
    # the server key is "respList", never "kline"
    assert "kline" not in result[0]
    assert result[0]["respList"][0]["c"] == "305.930"
    assert result[0]["respList"][0]["pc"] == "0.03%"


@respx.mock
def test_envelope1_depth_uses_a_b_transposed(client):
    body = load_json("rest/stock_depth.json")
    respx.get("https://data.infoway.io/stock/batch_depth/AAPL.US").mock(
        return_value=httpx.Response(200, json=body)
    )
    result = client.get("/stock/batch_depth/AAPL.US")
    # the server keys are "a"/"b" holding COLUMN-major [[prices],[qtys]]
    assert "asks" not in result[0] and "bids" not in result[0]
    assert result[0]["a"] == [["305.800"], ["229"]]
    assert result[0]["b"] == [["305.770"], ["24"]]


# --------------------------------------------------------------------------
# Envelope 2 — v2 outer {"market","count","data"}
# --------------------------------------------------------------------------

@respx.mock
def test_envelope2_v2_outer_returns_inner_data(client):
    body = load_json("rest/envelope_v2_outer.json")
    respx.get("https://data.infoway.io/common/v2/basic/plate/industry/HK").mock(
        return_value=httpx.Response(200, json=body)
    )
    result = client.get("/common/v2/basic/plate/industry/HK")
    assert isinstance(result, list)
    assert result[0]["symbol"] == "IN20234.HK"


# --------------------------------------------------------------------------
# Envelope 3 — HTTP 200, NO "data" key  → must return the whole body
# --------------------------------------------------------------------------

@respx.mock
def test_envelope3_no_data_key_returns_whole_body(client):
    body = load_json("rest/envelope_no_data_key.json")
    respx.get("https://data.infoway.io/common/v2/basic/plate/intro/IN20293.HK").mock(
        return_value=httpx.Response(200, json=body)
    )
    result = client.get("/common/v2/basic/plate/intro/IN20293.HK")
    assert result is not None, "envelope without a 'data' key must not be swallowed"
    assert result["plate"] == "IN20293.HK"
    assert result["intro"].startswith("Large, geographically diverse banks")


# --------------------------------------------------------------------------
# Envelope 4 — RFC7807 problem+json on HTTP 400 / 404
# --------------------------------------------------------------------------

@respx.mock
def test_envelope4_rfc7807_400_raises_api_error(client):
    body = load_json("rest/envelope_rfc7807_400.json")
    respx.get("https://data.infoway.io/common/basic/symbols").mock(
        return_value=httpx.Response(400, json=body)
    )
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/common/basic/symbols")
    assert exc.value.ret == 400
    assert exc.value.msg == "Required parameter 'type' is not present."


@respx.mock
def test_envelope4_rfc7807_404_raises_api_error(client):
    body = load_json("rest/envelope_rfc7807_404.json")
    respx.get("https://data.infoway.io/common/basic/markets/trading_hours").mock(
        return_value=httpx.Response(404, json=body)
    )
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/common/basic/markets/trading_hours")
    assert exc.value.ret == 404
    assert "No static resource" in exc.value.msg


# --------------------------------------------------------------------------
# Envelope 5 — rate limit, served with HTTP **200**
# --------------------------------------------------------------------------

@respx.mock
def test_envelope5_rate_limit_on_http_200_raises(client):
    body = load_json("rest/envelope_rate_limit.json")
    respx.get("https://data.infoway.io/common/v2/basic/stock/drivers/AAPL.US").mock(
        return_value=httpx.Response(200, json=body)
    )
    with pytest.raises(InfowayRateLimitError) as exc:
        client.get("/common/v2/basic/stock/drivers/AAPL.US")
    assert isinstance(exc.value, InfowayAPIError)
    assert "Rate limit exceeded" in str(exc.value)


@respx.mock
def test_http_429_raises_rate_limit_error(client):
    respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(429, json={"detail": "Rate limit exceeded"})
    )
    with pytest.raises(InfowayRateLimitError):
        client.get("/test")


@respx.mock
def test_http_429_html_gateway_page_does_not_crash(client):
    """The gateway serves an HTML page on 429 — json() would raise JSONDecodeError."""
    respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(429, html="<html><title>429 Too Many Requests</title></html>")
    )
    with pytest.raises(InfowayRateLimitError):
        client.get("/test")


# --------------------------------------------------------------------------
# 401 handling — body uses "message", not "msg"
# --------------------------------------------------------------------------

@respx.mock
def test_http_401_raises_auth_error_with_message_field(client):
    body = load_json("rest/envelope_401.json")
    assert "message" in body and "msg" not in body  # guard: real 401 body shape
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US").mock(
        return_value=httpx.Response(401, json=body)
    )
    with pytest.raises(InfowayAuthError) as exc:
        client.get("/stock/batch_trade/AAPL.US")
    assert exc.value.ret == 401
    assert "Token invalid" in str(exc.value)


# --------------------------------------------------------------------------
# ret/code non-200 inside an HTTP 200 body
# --------------------------------------------------------------------------

@respx.mock
def test_ret_500_raises_api_error(client):
    body = load_json("rest/envelope_ret500.json")
    respx.get("https://data.infoway.io/stock/batch_trade/700.HK").mock(
        return_value=httpx.Response(200, json=body)
    )
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/stock/batch_trade/700.HK")
    assert exc.value.ret == 508
    assert exc.value.msg == "All product not exists"
    assert exc.value.trace_id is not None
    assert exc.value.error_name == "PRODUCT_NOT_EXISTS"


@respx.mock
def test_plain_server_error_stays_500(client):
    respx.get("https://data.infoway.io/stock/batch_trade/NOPE").mock(
        return_value=httpx.Response(
            200, json={"ret": 500, "msg": "server error", "traceId": "t", "data": None}
        )
    )
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/stock/batch_trade/NOPE")
    assert exc.value.ret == 500
    assert exc.value.error_name == "SERVER_ERROR"


@respx.mock
def test_ret_508_is_product_not_exists(client):
    respx.get("https://data.infoway.io/stock/batch_trade/NOPE").mock(
        return_value=httpx.Response(
            200,
            json={"ret": 508, "msg": "All product not exists", "traceId": "t", "data": None},
        )
    )
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/stock/batch_trade/NOPE")
    assert exc.value.error_name == "PRODUCT_NOT_EXISTS"
    assert "[508 PRODUCT_NOT_EXISTS]" in str(exc.value)


@respx.mock
def test_ret_zero_is_not_treated_as_success(client):
    """`ret = data.get("ret") or data.get("code", 200)` turned a falsy 0 into 200."""
    respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(200, json={"ret": 0, "msg": "boom", "data": None})
    )
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/test")
    assert exc.value.ret == 0


# --------------------------------------------------------------------------
# Non-JSON / empty bodies on HTTP >= 400
# --------------------------------------------------------------------------

@respx.mock
def test_http_502_empty_body_raises_api_error(client):
    respx.get("https://data.infoway.io/test").mock(return_value=httpx.Response(502, content=b""))
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/test")
    assert exc.value.ret == 502


@respx.mock
def test_http_400_non_json_body_raises_api_error(client):
    respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(400, html="<html>bad request</html>")
    )
    with pytest.raises(InfowayAPIError) as exc:
        client.get("/test")
    assert exc.value.ret == 400


# --------------------------------------------------------------------------
# transport-level behaviour
# --------------------------------------------------------------------------

@respx.mock
def test_sends_api_key_header():
    c = HttpClient(api_key="test-key", max_retries=1)
    route = respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {}})
    )
    c.get("/test")
    assert route.calls[0].request.headers["apikey"] == "test-key"


@respx.mock
def test_retry_on_connection_failure():
    c = HttpClient(api_key="test-key", max_retries=3)
    route = respx.get("https://data.infoway.io/test")
    route.side_effect = [
        httpx.ConnectError("fail"),
        httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {"ok": True}}),
    ]
    result = c.get("/test")
    assert result == {"ok": True}
    assert route.call_count == 2


@respx.mock
def test_rate_limit_is_retried_with_backoff(monkeypatch):
    """Rate limiting is transient — it must go through the retry/backoff path."""
    slept = []
    monkeypatch.setattr("infoway._http.time.sleep", lambda s: slept.append(s))
    c = HttpClient(api_key="test-key", max_retries=3)
    route = respx.get("https://data.infoway.io/test")
    route.side_effect = [
        httpx.Response(200, json={"detail": "Rate limit exceeded"}),
        httpx.Response(200, json={"ret": 200, "msg": "ok", "data": {"ok": True}}),
    ]
    assert c.get("/test") == {"ok": True}
    assert route.call_count == 2
    assert slept, "a backoff sleep must happen between rate-limited attempts"


@respx.mock
def test_rate_limit_exhausts_retries_and_raises(monkeypatch):
    monkeypatch.setattr("infoway._http.time.sleep", lambda s: None)
    c = HttpClient(api_key="test-key", max_retries=2)
    respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(200, json={"detail": "Rate limit exceeded"})
    )
    with pytest.raises(InfowayRateLimitError):
        c.get("/test")


@respx.mock
def test_api_error_is_not_retried():
    c = HttpClient(api_key="test-key", max_retries=3)
    route = respx.get("https://data.infoway.io/test").mock(
        return_value=httpx.Response(200, json=load_json("rest/envelope_ret500.json"))
    )
    with pytest.raises(InfowayAPIError):
        c.get("/test")
    assert route.call_count == 1


@respx.mock
def test_timeout_raises_timeout_error(monkeypatch):
    monkeypatch.setattr("infoway._http.time.sleep", lambda s: None)
    c = HttpClient(api_key="test-key", max_retries=2)
    respx.get("https://data.infoway.io/test").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(InfowayTimeoutError):
        c.get("/test")

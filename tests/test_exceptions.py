from infoway.exceptions import (
    InfowayAPIError,
    InfowayAuthError,
    InfowayIoError,
    InfowayRateLimitError,
    InfowayTimeoutError,
)


def test_api_error_stores_fields():
    err = InfowayAPIError(ret=500, msg="All product not exists", trace_id="abc-123")
    assert err.ret == 500
    assert err.msg == "All product not exists"
    assert err.trace_id == "abc-123"
    assert "500" in str(err)
    assert "All product not exists" in str(err)


def test_api_error_defaults():
    err = InfowayAPIError(ret=400, msg="Required parameter 'type' is not present.")
    assert err.trace_id is None


def test_auth_error_is_api_error():
    err = InfowayAuthError()
    assert isinstance(err, InfowayAPIError)
    assert err.ret == 401


def test_auth_error_keeps_custom_message():
    err = InfowayAuthError("Token invalid")
    assert "Token invalid" in str(err)


def test_rate_limit_error_is_api_error():
    err = InfowayRateLimitError()
    assert isinstance(err, InfowayAPIError)
    assert err.ret == 429
    assert "Rate limit exceeded" in str(err)


def test_rate_limit_error_keeps_the_status_it_arrived_with():
    """The gateway serves rate limiting with HTTP 200 as well as 429."""
    err = InfowayRateLimitError("Rate limit exceeded", ret=200)
    assert err.ret == 200


def test_timeout_error_is_base_exception():
    err = InfowayTimeoutError("request timed out")
    assert isinstance(err, Exception)
    assert "timed out" in str(err)


def test_exceptions_are_exported_from_the_package():
    import infoway

    assert infoway.InfowayRateLimitError is InfowayRateLimitError
    assert infoway.InfowayAuthError is InfowayAuthError
    assert infoway.InfowayIoError is InfowayIoError


def test_of_rest_and_of_ws_use_different_names_for_508():
    rest = InfowayAPIError.of_rest(508, "All product not exists")
    ws = InfowayAPIError.of_ws(508, "expired")
    assert rest.error_name == "PRODUCT_NOT_EXISTS"
    assert ws.error_name == "APIKEY_EXPIRED"
    assert "[508 PRODUCT_NOT_EXISTS]" in str(rest)
    assert "[508 APIKEY_EXPIRED]" in str(ws)


def test_of_http_status_does_not_lookup_rest_enum():
    err = InfowayAPIError.of_http_status(502, "Bad Gateway")
    assert err.error_name is None
    assert err.ret == 502

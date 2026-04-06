from infoway.exceptions import InfowayAPIError, InfowayAuthError, InfowayTimeoutError


def test_api_error_stores_fields():
    err = InfowayAPIError(ret=500, msg="server error", trace_id="abc-123")
    assert err.ret == 500
    assert err.msg == "server error"
    assert err.trace_id == "abc-123"
    assert "500" in str(err)
    assert "server error" in str(err)


def test_api_error_defaults():
    err = InfowayAPIError(ret=400, msg="bad request")
    assert err.trace_id is None


def test_auth_error_is_api_error():
    err = InfowayAuthError()
    assert isinstance(err, InfowayAPIError)
    assert err.ret == 401


def test_timeout_error_is_base_exception():
    err = InfowayTimeoutError("request timed out")
    assert isinstance(err, Exception)
    assert "timed out" in str(err)

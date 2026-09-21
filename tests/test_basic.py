"""client.basic.* — parameters and paths the server actually requires.

Payloads are verbatim production captures (tests/fixtures/rest/basic_*.json).
See docs/specs/2026-08-15-sdk-contract-fix-design.md §2.
"""

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.rest.basic import BasicClient
from tests.conftest import load_json


@pytest.fixture
def basic():
    return BasicClient(HttpClient(api_key="test-key", max_retries=1))


# --------------------------------------------------------------------------
# get_symbols(type)
# --------------------------------------------------------------------------

@respx.mock
def test_get_symbols_sends_type_not_market(basic):
    route = respx.get("https://data.infoway.io/common/basic/symbols").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_symbols.json"))
    )
    result = basic.get_symbols("STOCK_US")
    assert route.calls[0].request.url.params["type"] == "STOCK_US"
    assert "market" not in route.calls[0].request.url.params
    assert result[0]["symbol"] == "AAPL.US"
    assert result[0]["name_en"] == "Apple"


@respx.mock
def test_get_symbols_optional_symbols_filter(basic):
    route = respx.get("https://data.infoway.io/common/basic/symbols").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_symbols.json"))
    )
    basic.get_symbols("STOCK_US", symbols="AAPL.US")
    params = route.calls[0].request.url.params
    assert params["type"] == "STOCK_US"
    assert params["symbols"] == "AAPL.US"


def test_get_symbols_requires_type(basic):
    with pytest.raises(TypeError):
        basic.get_symbols()  # type: ignore[call-arg]


# --------------------------------------------------------------------------
# get_symbol_info(type, symbols)
# --------------------------------------------------------------------------

@respx.mock
def test_get_symbol_info_sends_type_and_symbols(basic):
    route = respx.get("https://data.infoway.io/common/basic/symbols/info").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_symbol_info.json"))
    )
    result = basic.get_symbol_info("STOCK_US", "AAPL.US")
    params = route.calls[0].request.url.params
    assert params["type"] == "STOCK_US"
    assert params["symbols"] == "AAPL.US"
    assert "codes" not in params
    assert result[0]["symbol"] == "AAPL.US"
    assert result[0]["lot_size"] == 1
    assert result[0]["exchange"] == "NASD"


# --------------------------------------------------------------------------
# get_adjustment_factors(symbol, market, begin_day, end_day)
# --------------------------------------------------------------------------

@respx.mock
def test_get_adjustment_factors_sends_all_four_params(basic):
    route = respx.get("https://data.infoway.io/common/basic/symbols/adjustment_factors").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_adjustment_factors.json"))
    )
    result = basic.get_adjustment_factors("AAPL.US", "US", "20260801", "20260814")
    params = route.calls[0].request.url.params
    assert params["symbol"] == "AAPL.US"
    assert params["market"] == "US"
    assert params["beginDay"] == "20260801"
    assert params["endDay"] == "20260814"
    assert "codes" not in params
    assert result[0]["trade_date"] == "20260803"
    assert result[0]["forward_factor"] == 1.0


# --------------------------------------------------------------------------
# get_trading_days(market, begin_day, end_day)
# --------------------------------------------------------------------------

@respx.mock
def test_get_trading_days_sends_begin_and_end(basic):
    route = respx.get("https://data.infoway.io/common/basic/markets/trading_days").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_trading_days.json"))
    )
    result = basic.get_trading_days("US", "20260801", "20260831")
    params = route.calls[0].request.url.params
    assert params["market"] == "US"
    assert params["beginDay"] == "20260801"
    assert params["endDay"] == "20260831"
    # data is an OBJECT with trade_days / half_trade_days, not a list of dates
    assert result["trade_days"][0] == "20260803"
    assert result["half_trade_days"] == []


# --------------------------------------------------------------------------
# get_trading_schedule(market)  (+ deprecated get_trading_hours alias)
# --------------------------------------------------------------------------

@respx.mock
def test_get_trading_schedule_uses_trading_schedule_path(basic):
    route = respx.get("https://data.infoway.io/common/basic/markets/trading_schedule").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_trading_schedule.json"))
    )
    result = basic.get_trading_schedule()
    assert route.calls[0].request.url.path == "/common/basic/markets/trading_schedule"
    assert result[0]["symbol"] == "XAGEUR"
    assert result[0]["type"] == "METAL"
    assert "segments" in result[0]["trading_hours"]


@respx.mock
def test_get_trading_schedule_type_filter(basic):
    route = respx.get("https://data.infoway.io/common/basic/markets/trading_schedule").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_trading_schedule.json"))
    )
    basic.get_trading_schedule(type="METAL")
    assert route.calls[0].request.url.params["type"] == "METAL"


@respx.mock
def test_get_trading_hours_is_deprecated_alias(basic):
    route = respx.get("https://data.infoway.io/common/basic/markets/trading_schedule").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_trading_schedule.json"))
    )
    with pytest.deprecated_call():
        result = basic.get_trading_hours()
    assert route.calls[0].request.url.path == "/common/basic/markets/trading_schedule"
    assert result[0]["symbol"] == "XAGEUR"


# --------------------------------------------------------------------------
# real server rejections must surface as exceptions, never as None
# --------------------------------------------------------------------------

@respx.mock
def test_missing_type_400_surfaces_as_exception(basic):
    from infoway.exceptions import InfowayAPIError

    respx.get("https://data.infoway.io/common/basic/symbols").mock(
        return_value=httpx.Response(400, json=load_json("rest/envelope_rfc7807_400.json"))
    )
    with pytest.raises(InfowayAPIError) as exc:
        basic.get_symbols("")
    assert "Required parameter 'type' is not present." in str(exc.value)


@respx.mock
def test_get_markets(basic):
    route = respx.get("https://data.infoway.io/common/basic/markets").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": []})
    )
    basic.get_markets()
    assert route.calls[0].request.url.path == "/common/basic/markets"


@respx.mock
def test_get_stock_detail(basic):
    from infoway import SymbolType

    route = respx.get("https://data.infoway.io/common/basic/stock/detail").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": None})
    )
    basic.get_stock_detail(SymbolType.STOCK_US, "AAPL.US")
    params = route.calls[0].request.url.params
    assert params["type"] == "STOCK_US"
    assert params["symbol"] == "AAPL.US"


@respx.mock
def test_get_trading_schedule_by_type(basic):
    from infoway import ScheduleType, SymbolType

    route = respx.get("https://data.infoway.io/common/basic/markets/trading_schedule").mock(
        return_value=httpx.Response(200, json=load_json("rest/basic_trading_schedule.json"))
    )
    basic.get_trading_schedule_by_type(ScheduleType.ENERGY)
    assert route.calls[0].request.url.params["type"] == "ENERGY"
    with pytest.raises(ValueError, match="ENERGY/FOREX"):
        basic.get_trading_schedule_by_type(SymbolType.STOCK_US)

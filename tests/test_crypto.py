import httpx
import respx
import pytest
from infoway._http import HttpClient
from infoway.rest.crypto import CryptoClient


@pytest.fixture
def crypto():
    http = HttpClient(api_key="test-key")
    return CryptoClient(http)


@respx.mock
def test_get_trade(crypto):
    respx.get("https://data.infoway.io/crypto/batch_trade/BTCUSDT").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "data": [{"s": "BTCUSDT", "p": "65000.00"}]
        })
    )
    result = crypto.get_trade("BTCUSDT")
    assert result[0]["s"] == "BTCUSDT"


@respx.mock
def test_get_kline(crypto):
    respx.post("https://data.infoway.io/crypto/v2/batch_kline").mock(
        return_value=httpx.Response(200, json={
            "ret": 200, "msg": "success", "data": [{"s": "BTCUSDT", "kline": []}]
        })
    )
    result = crypto.get_kline("BTCUSDT", kline_type=8, count=5)
    assert result[0]["s"] == "BTCUSDT"

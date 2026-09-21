import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.rest.korea import KoreaClient
from infoway.rest.taiwan import TaiwanClient


@respx.mock
def test_korea_trade_path():
    client = KoreaClient(HttpClient(api_key="test-key", max_retries=1))
    route = respx.get("https://data.infoway.io/korea/batch_trade/005930.KS").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": []})
    )
    client.get_trade("005930.KS")
    assert route.calls[0].request.url.path == "/korea/batch_trade/005930.KS"


@respx.mock
def test_taiwan_trade_path():
    client = TaiwanClient(HttpClient(api_key="test-key", max_retries=1))
    route = respx.get("https://data.infoway.io/taiwan/batch_trade/2330.TW").mock(
        return_value=httpx.Response(200, json={"ret": 200, "msg": "ok", "data": []})
    )
    client.get_trade("2330.TW")
    assert route.calls[0].request.url.path == "/taiwan/batch_trade/2330.TW"

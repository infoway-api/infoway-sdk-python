"""client.crypto.* — asserted against verbatim production payloads."""

import json

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.rest.crypto import CryptoClient
from tests.conftest import load_json


@pytest.fixture
def crypto():
    return CryptoClient(HttpClient(api_key="test-key", max_retries=1))


@respx.mock
def test_get_trade(crypto):
    respx.get("https://data.infoway.io/crypto/batch_trade/BTCUSDT").mock(
        return_value=httpx.Response(200, json=load_json("rest/crypto_trade.json"))
    )
    [row] = crypto.get_trade("BTCUSDT")
    assert row["s"] == "BTCUSDT"
    assert row["p"] == "63059.36"
    assert row["v"] == "0.01056"
    assert row["vw"] == "665.9068416"
    assert row["td"] == 1


@respx.mock
def test_get_depth_five_levels(crypto):
    respx.get("https://data.infoway.io/crypto/batch_depth/BTCUSDT").mock(
        return_value=httpx.Response(200, json=load_json("rest/crypto_depth.json"))
    )
    [row] = crypto.get_depth("BTCUSDT")
    assert row["s"] == "BTCUSDT"
    assert len(row["a"]) == 2, "a is [[prices],[qtys]], i.e. two columns"
    assert len(row["a"][0]) == 5, "five price levels"
    assert len(row["a"][1]) == 5, "five quantities"


@respx.mock
def test_get_kline(crypto):
    route = respx.post("https://data.infoway.io/crypto/v2/batch_kline").mock(
        return_value=httpx.Response(200, json=load_json("rest/crypto_kline.json"))
    )
    [row] = crypto.get_kline("BTCUSDT", kline_type=1, count=2)
    assert json.loads(route.calls[0].request.content) == {
        "codes": "BTCUSDT", "klineType": 1, "klineNum": 2
    }
    assert row["s"] == "BTCUSDT"
    assert len(row["respList"]) == 2
    assert set(row["respList"][0]) >= {"t", "o", "h", "l", "c", "v", "vw", "pc", "pca"}

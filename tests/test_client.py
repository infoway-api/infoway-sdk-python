import pytest
from infoway.client import InfowayClient
from infoway.rest.stock import StockClient
from infoway.rest.crypto import CryptoClient
from infoway.rest.basic import BasicClient
from infoway.rest.market import MarketClient
from infoway.rest.plate import PlateClient
from infoway.rest.stock_info import StockInfoClient


def test_client_creates_sub_clients():
    client = InfowayClient(api_key="test-key")
    assert isinstance(client.stock, StockClient)
    assert isinstance(client.crypto, CryptoClient)
    assert isinstance(client.basic, BasicClient)
    assert isinstance(client.market, MarketClient)
    assert isinstance(client.plate, PlateClient)
    assert isinstance(client.stock_info, StockInfoClient)


def test_client_context_manager():
    with InfowayClient(api_key="test-key") as client:
        assert client.stock is not None


def test_client_reads_env_var(monkeypatch):
    monkeypatch.setenv("INFOWAY_API_KEY", "env-test-key")
    client = InfowayClient()
    assert client._http._api_key == "env-test-key"

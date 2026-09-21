from infoway.client import InfowayClient
from infoway.rest.basic import BasicClient
from infoway.rest.crypto import CryptoClient
from infoway.rest.financial import FinancialClient
from infoway.rest.korea import KoreaClient
from infoway.rest.market import MarketClient
from infoway.rest.packages import PackageClient
from infoway.rest.plate import PlateClient
from infoway.rest.stock import StockClient
from infoway.rest.stock_info import StockInfoClient
from infoway.rest.taiwan import TaiwanClient


def test_client_creates_sub_clients():
    client = InfowayClient(api_key="test-key")
    assert isinstance(client.stock, StockClient)
    assert isinstance(client.crypto, CryptoClient)
    assert isinstance(client.basic, BasicClient)
    assert isinstance(client.market, MarketClient)
    assert isinstance(client.plate, PlateClient)
    assert isinstance(client.stock_info, StockInfoClient)
    assert isinstance(client.korea, KoreaClient)
    assert isinstance(client.taiwan, TaiwanClient)
    assert isinstance(client.financial, FinancialClient)
    assert isinstance(client.packages, PackageClient)


def test_client_context_manager():
    with InfowayClient(api_key="test-key") as client:
        assert client.stock is not None


def test_client_reads_env_var(monkeypatch):
    monkeypatch.setenv("INFOWAY_API_KEY", "env-test-key")
    client = InfowayClient()
    assert client._http._api_key == "env-test-key"


def test_parse_is_off_by_default():
    client = InfowayClient(api_key="test-key")
    assert client.stock._parse is False
    assert client.crypto._parse is False


def test_parse_propagates_to_market_sub_clients():
    client = InfowayClient(api_key="test-key", parse=True)
    for sub in (
        client.stock, client.crypto, client.japan, client.india,
        client.korea, client.taiwan, client.common,
    ):
        assert sub._parse is True


def test_version_is_030():
    import infoway

    assert infoway.__version__ == "0.3.0"

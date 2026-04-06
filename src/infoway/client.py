"""Main entry point for the Infoway SDK."""

from __future__ import annotations

from infoway._http import HttpClient
from infoway.rest.stock import StockClient
from infoway.rest.crypto import CryptoClient
from infoway.rest.japan import JapanClient
from infoway.rest.india import IndiaClient
from infoway.rest.common import CommonClient
from infoway.rest.basic import BasicClient
from infoway.rest.market import MarketClient
from infoway.rest.plate import PlateClient
from infoway.rest.stock_info import StockInfoClient


class InfowayClient:
    """Infoway API client.

    Usage::

        from infoway import InfowayClient

        client = InfowayClient(api_key="YOUR_API_KEY")
        trades = client.stock.get_trade("AAPL.US")
        klines = client.crypto.get_kline("BTCUSDT", kline_type=8, count=100)
        temp = client.market.get_temperature(market="HK,US")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://data.infoway.io",
        timeout: float = 15.0,
        max_retries: int = 3,
    ):
        self._http = HttpClient(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries,
        )
        self.stock = StockClient(self._http)
        self.crypto = CryptoClient(self._http)
        self.japan = JapanClient(self._http)
        self.india = IndiaClient(self._http)
        self.common = CommonClient(self._http)
        self.basic = BasicClient(self._http)
        self.market = MarketClient(self._http)
        self.plate = PlateClient(self._http)
        self.stock_info = StockInfoClient(self._http)

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

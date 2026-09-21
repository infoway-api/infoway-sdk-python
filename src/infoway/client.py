"""Main entry point for the Infoway SDK."""

from __future__ import annotations

from infoway._http import HttpClient
from infoway.rest.basic import BasicClient
from infoway.rest.common import CommonClient
from infoway.rest.crypto import CryptoClient
from infoway.rest.financial import FinancialClient
from infoway.rest.india import IndiaClient
from infoway.rest.japan import JapanClient
from infoway.rest.korea import KoreaClient
from infoway.rest.market import MarketClient
from infoway.rest.packages import PackageClient
from infoway.rest.plate import PlateClient
from infoway.rest.stock import StockClient
from infoway.rest.stock_info import StockInfoClient
from infoway.rest.taiwan import TaiwanClient


class InfowayClient:
    """Infoway API client.

    Usage::

        from infoway import InfowayClient, SymbolType

        client = InfowayClient(api_key="YOUR_API_KEY")
        trades = client.stock.get_trade("AAPL.US")
        klines = client.crypto.get_kline("BTCUSDT", kline_type=8, count=100)
        symbols = client.basic.get_symbols(SymbolType.STOCK_US)

    Args:
        api_key: API key; falls back to the ``INFOWAY_API_KEY`` environment variable.
        base_url: REST base URL.
        timeout: Per-request timeout in seconds.
        max_retries: Attempts per request (connection errors, timeouts and rate
            limiting are retried with exponential backoff).
        parse: When ``True``, market-data responses are normalised (Decimals,
            datetimes, flattened klines, ``(price, qty)`` depth pairs). Defaults
            to ``False``, i.e. raw server payloads.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://data.infoway.io",
        timeout: float = 15.0,
        max_retries: int = 3,
        parse: bool = False,
    ):
        self._http = HttpClient(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries,
        )
        self._parse = parse
        self.stock = StockClient(self._http, parse=parse)
        self.crypto = CryptoClient(self._http, parse=parse)
        self.japan = JapanClient(self._http, parse=parse)
        self.india = IndiaClient(self._http, parse=parse)
        self.korea = KoreaClient(self._http, parse=parse)
        self.taiwan = TaiwanClient(self._http, parse=parse)
        self.common = CommonClient(self._http, parse=parse)
        self.basic = BasicClient(self._http)
        self.packages = PackageClient(self._http)
        self.market = MarketClient(self._http)
        self.plate = PlateClient(self._http)
        self.stock_info = StockInfoClient(self._http)
        self.financial = FinancialClient(self._http)

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

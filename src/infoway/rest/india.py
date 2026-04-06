"""India market data client."""

from __future__ import annotations
from typing import TYPE_CHECKING
from infoway.rest._market_data import MarketDataMixin

if TYPE_CHECKING:
    from infoway._http import HttpClient


class IndiaClient(MarketDataMixin):
    _prefix = "india"

    def __init__(self, http: HttpClient):
        self._http = http

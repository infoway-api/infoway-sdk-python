"""Crypto market data client."""

from __future__ import annotations
from typing import TYPE_CHECKING
from infoway.rest._market_data import MarketDataMixin

if TYPE_CHECKING:
    from infoway._http import HttpClient


class CryptoClient(MarketDataMixin):
    _prefix = "crypto"

    def __init__(self, http: HttpClient):
        self._http = http

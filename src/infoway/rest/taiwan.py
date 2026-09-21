"""Taiwan market data client (.TW)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from infoway.rest._market_data import MarketDataMixin

if TYPE_CHECKING:
    from infoway._http import HttpClient


class TaiwanClient(MarketDataMixin):
    _prefix = "taiwan"

    def __init__(self, http: HttpClient, parse: bool = False):
        self._http = http
        self._parse = parse

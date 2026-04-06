"""Basic information client (symbols, trading days, hours)."""

from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from infoway._http import HttpClient


class BasicClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_symbols(self, market: str | None = None) -> Any:
        params = {"market": market} if market else None
        return self._http.get("/common/basic/symbols", params=params)

    def get_symbol_info(self, codes: str) -> Any:
        return self._http.get("/common/basic/symbols/info", params={"codes": codes})

    def get_adjustment_factors(self, codes: str) -> Any:
        return self._http.get("/common/basic/symbols/adjustment_factors", params={"codes": codes})

    def get_trading_days(self, market: str) -> Any:
        return self._http.get("/common/basic/markets/trading_days", params={"market": market})

    def get_trading_hours(self, market: str | None = None) -> Any:
        params = {"market": market} if market else None
        return self._http.get("/common/basic/markets", params=params)

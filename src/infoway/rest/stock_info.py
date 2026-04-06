"""Stock fundamental data client."""

from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from infoway._http import HttpClient


class StockInfoClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_valuation(self, symbol: str) -> Any:
        return self._http.get(f"/common/v2/basic/stock/valuation/{symbol}")

    def get_ratings(self, symbol: str) -> Any:
        return self._http.get(f"/common/v2/basic/stock/ratings/{symbol}")

    def get_company(self, symbol: str) -> Any:
        return self._http.get(f"/common/v2/basic/stock/company/{symbol}")

    def get_panorama(self, symbol: str) -> Any:
        return self._http.get(f"/common/v2/basic/stock/panorama/{symbol}")

    def get_concepts(self, symbol: str) -> Any:
        return self._http.get(f"/common/v2/basic/stock/concepts/{symbol}")

    def get_events(self, symbol: str, limit: int = 20) -> Any:
        return self._http.get(f"/common/v2/basic/stock/events/{symbol}", params={"limit": limit})

    def get_drivers(self, symbol: str) -> Any:
        return self._http.get(f"/common/v2/basic/stock/drivers/{symbol}")

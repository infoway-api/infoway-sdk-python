"""Market overview client (temperature, breadth, indexes, leaders)."""

from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from infoway._http import HttpClient


class MarketClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_temperature(self, market: str = "HK,US,CN,SG") -> Any:
        return self._http.get("/common/v2/basic/market/temperature", params={"market": market})

    def get_breadth(self, market: str) -> Any:
        return self._http.get(f"/common/v2/basic/market/breadth/{market}")

    def get_indexes(self) -> Any:
        return self._http.get("/common/v2/basic/market/indexes")

    def get_leaders(self, market: str, limit: int = 10) -> Any:
        return self._http.get(f"/common/v2/basic/market/leaders/{market}", params={"limit": limit})

    def get_rank_config(self, market: str) -> Any:
        return self._http.get(f"/common/v2/basic/market/rank-config/{market}")

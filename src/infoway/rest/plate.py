"""Plate (sector) data client."""

from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from infoway._http import HttpClient


class PlateClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_industry(self, market: str, limit: int = 200) -> Any:
        return self._http.get(f"/common/v2/basic/plate/industry/{market}", params={"limit": limit})

    def get_concept(self, market: str, limit: int = 100) -> Any:
        return self._http.get(f"/common/v2/basic/plate/concept/{market}", params={"limit": limit})

    def get_members(self, plate_symbol: str, offset: int = 0, limit: int = 50) -> Any:
        return self._http.get(f"/common/v2/basic/plate/members/{plate_symbol}", params={"offset": offset, "limit": limit})

    def get_intro(self, plate_symbol: str) -> Any:
        return self._http.get(f"/common/v2/basic/plate/intro/{plate_symbol}")

    def get_chart(self, market: str, limit: int = 50) -> Any:
        return self._http.get(f"/common/v2/basic/plate/chart/{market}", params={"limit": limit})

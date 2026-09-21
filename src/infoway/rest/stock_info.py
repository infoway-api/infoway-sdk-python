"""Stock fundamental data client."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from infoway._types import Lang, query, wire

if TYPE_CHECKING:
    from infoway._http import HttpClient


class StockInfoClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_valuation(self, symbol: str, lang: Lang | str | None = None) -> Any:
        return self._get(f"/common/v2/basic/stock/valuation/{symbol}", lang)

    def get_ratings(self, symbol: str, lang: Lang | str | None = None) -> Any:
        return self._get(f"/common/v2/basic/stock/ratings/{symbol}", lang)

    def get_company(self, symbol: str, lang: Lang | str | None = None) -> Any:
        return self._get(f"/common/v2/basic/stock/company/{symbol}", lang)

    def get_panorama(self, symbol: str, lang: Lang | str | None = None) -> Any:
        return self._get(f"/common/v2/basic/stock/panorama/{symbol}", lang)

    def get_concepts(self, symbol: str, lang: Lang | str | None = None) -> Any:
        return self._get(f"/common/v2/basic/stock/concepts/{symbol}", lang)

    def get_events(
        self, symbol: str, limit: int = 20, lang: Lang | str | None = None
    ) -> Any:
        return self._http.get(
            f"/common/v2/basic/stock/events/{symbol}",
            params=query(limit=limit, lang=wire(lang)),
        )

    def get_drivers(self, symbol: str, lang: Lang | str | None = None) -> Any:
        return self._get(f"/common/v2/basic/stock/drivers/{symbol}", lang)

    def _get(self, path: str, lang: Lang | str | None) -> Any:
        return self._http.get(path, params=query(lang=wire(lang)))

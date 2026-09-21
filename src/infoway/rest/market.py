"""Market overview client (temperature, breadth, turnover, indexes, leaders, ranks)."""

from __future__ import annotations

import warnings
from typing import Any, TYPE_CHECKING

from infoway._types import Lang, Market, RankSort, SortOrder, query, wire

if TYPE_CHECKING:
    from infoway._http import HttpClient


class MarketClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_temperature(
        self,
        market: Market | str | None = None,
        lang: Lang | str | None = None,
    ) -> Any:
        """Sentiment overview. Default markets are ``HK,US,CN``.

        Join several markets with ``Market.join(Market.HK, Market.US)`` or a
        comma string ``"HK,US"``.
        """
        joined = "HK,US,CN" if market is None else wire(market)
        return self._http.get(
            "/common/v2/basic/market/temperature",
            params=query(market=joined, lang=wire(lang)),
        )

    def get_breadth(self, market: Market | str, lang: Lang | str | None = None) -> Any:
        return self._http.get(
            f"/common/v2/basic/market/breadth/{wire(market)}",
            params=query(lang=wire(lang)),
        )

    def get_turnover(self, market: Market | str, lang: Lang | str | None = None) -> Any:
        return self._http.get(
            f"/common/v2/basic/market/turnover/{wire(market)}",
            params=query(lang=wire(lang)),
        )

    def get_indexes(self, lang: Lang | str | None = None) -> Any:
        return self._http.get(
            "/common/v2/basic/market/indexes",
            params=query(lang=wire(lang)),
        )

    def get_leaders(
        self,
        market: Market | str,
        limit: int = 10,
        lang: Lang | str | None = None,
    ) -> Any:
        return self._http.get(
            f"/common/v2/basic/market/leaders/{wire(market)}",
            params=query(limit=limit, lang=wire(lang)),
        )

    def get_overview(self, market: Market | str, lang: Lang | str | None = None) -> Any:
        return self._http.get(
            f"/common/v2/basic/market/overview/{wire(market)}",
            params=query(lang=wire(lang)),
        )

    def get_rank_categories(
        self, market: Market | str, lang: Lang | str | None = None
    ) -> Any:
        return self._http.get(
            f"/common/v2/basic/market/rank/categories/{wire(market)}",
            params=query(lang=wire(lang)),
        )

    def get_rank(
        self,
        market: Market | str,
        key: str,
        sort: RankSort | str | None = None,
        order: SortOrder | str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        lang: Lang | str | None = None,
    ) -> Any:
        return self._http.get(
            f"/common/v2/basic/market/rank/{wire(market)}/{key}",
            params=query(
                sort=wire(sort),
                order=wire(order),
                limit=limit,
                offset=offset,
                lang=wire(lang),
            ),
        )

    def get_rank_config(self, market: Market | str) -> Any:
        warnings.warn(
            "get_rank_config() is deprecated; the path returns HTTP 404. "
            "Use get_rank_categories() and get_rank().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._http.get(f"/common/v2/basic/market/rank-config/{wire(market)}")

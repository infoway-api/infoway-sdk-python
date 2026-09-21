"""Basic information client (symbols, adjustment factors, trading calendar)."""

from __future__ import annotations

import warnings
from typing import Any, TYPE_CHECKING

from infoway._types import (
    SYMBOL_TYPES,
    Market,
    ScheduleType,
    SymbolType,
    query,
    wire,
)

if TYPE_CHECKING:
    from infoway._http import HttpClient


class BasicClient:
    """Reference data: instrument lists, static info, adjustment factors, calendar."""

    def __init__(self, http: HttpClient):
        self._http = http

    def get_symbols(
        self, type: SymbolType | str, symbols: str | None = None
    ) -> Any:
        """List instruments of a given type.

        Args:
            type: One of :class:`SymbolType` (e.g. ``STOCK_US``). **Required** —
                the server answers HTTP 400 without it. A market code ``US`` is
                not accepted.
            symbols: Optional comma-separated filter, e.g. ``"AAPL.US,TSLA.US"``.
        """
        return self._http.get(
            "/common/basic/symbols",
            params=query(type=wire(type), symbols=symbols),
        )

    def get_symbol_info(self, type: SymbolType | str, symbols: str) -> Any:
        return self._http.get(
            "/common/basic/symbols/info",
            params=query(type=wire(type), symbols=symbols),
        )

    def get_adjustment_factors(
        self,
        symbol: str,
        market: Market | str,
        begin_day: str,
        end_day: str,
    ) -> Any:
        return self._http.get(
            "/common/basic/symbols/adjustment_factors",
            params=query(
                symbol=symbol,
                market=wire(market),
                beginDay=begin_day,
                endDay=end_day,
            ),
        )

    def get_trading_days(
        self, market: Market | str, begin_day: str, end_day: str
    ) -> Any:
        return self._http.get(
            "/common/basic/markets/trading_days",
            params=query(market=wire(market), beginDay=begin_day, endDay=end_day),
        )

    def get_trading_schedule(
        self, market: Market | str | None = None, type: str | None = None
    ) -> Any:
        """Trading sessions / holidays.

        ``market`` is ignored by the server (kept for call-site compatibility).
        Filter by product with :meth:`get_trading_schedule_by_type`.
        """
        return self._http.get(
            "/common/basic/markets/trading_schedule",
            params=query(market=wire(market), type=type),
        )

    def get_trading_schedule_by_type(self, type: ScheduleType | SymbolType | str) -> Any:
        """Same endpoint, filtered by ``ENERGY`` / ``FOREX`` / ``FUTURES`` / ``METAL`` / ``INDICES``.

        Passing an equity :class:`SymbolType` such as ``STOCK_US`` raises
        ``ValueError`` before the request (the server would answer HTTP 400).
        """
        resolved = ScheduleType.from_symbol_type(type) if not isinstance(type, ScheduleType) else type
        if isinstance(type, SymbolType) and resolved is None:
            raise ValueError(
                "type must be one of ENERGY/FOREX/FUTURES/METAL/INDICES "
                f"(got {type.value})"
            )
        if resolved is None and isinstance(type, str):
            resolved = ScheduleType.from_value(type)
        if resolved is None:
            raise ValueError(
                "type must be one of ENERGY/FOREX/FUTURES/METAL/INDICES "
                f"(got {type!r})"
            )
        return self.get_trading_schedule(type=resolved.value)

    def get_trading_hours(
        self, market: Market | str | None = None, type: str | None = None
    ) -> Any:
        """Deprecated alias of :meth:`get_trading_schedule`.

        .. deprecated:: 0.2.0
        """
        warnings.warn(
            "get_trading_hours() is deprecated and will be removed in 1.0; "
            "use get_trading_schedule() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_trading_schedule(market=market, type=type)

    def get_markets(self) -> Any:
        return self._http.get("/common/basic/markets")

    def get_stock_detail(self, type: SymbolType | str, symbol: str) -> Any:
        return self._http.get(
            "/common/basic/stock/detail",
            params=query(type=wire(type), symbol=symbol),
        )


__all__ = ["BasicClient", "SYMBOL_TYPES"]

"""Stock financial statements and earnings."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from infoway._types import SYMBOL_TYPES, PeriodType, RestErrorCode, SymbolType, query, wire
from infoway.exceptions import InfowayAPIError

if TYPE_CHECKING:
    from infoway._http import HttpClient


class FinancialClient:
    """Nine endpoints under ``/common/basic/financial/*``.

    Every call needs ``symbol`` plus a product ``type`` (``STOCK_US``,
    ``STOCK_TW``, …). Statement-style methods accept optional ``period_type``:
    ``fq`` / ``fy`` / ``fh``.
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def get_earning_status(self, symbol: str, type: SymbolType | str) -> Any:
        return self._get("earning_status", symbol, type)

    def get_income_statement(
        self,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        return self._get("income_statement", symbol, type, period_type)

    def get_revenue(
        self,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        return self._get("revenue", symbol, type, period_type)

    def get_cash_flow(
        self,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        return self._get("cash_flow", symbol, type, period_type)

    def get_balance_sheet(
        self,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        return self._get("balance_sheet", symbol, type, period_type)

    def get_statistics(
        self,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        return self._get("statistics", symbol, type, period_type)

    def get_dividend(
        self,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        return self._get("dividend", symbol, type, period_type)

    def get_dividend_payout(self, symbol: str, type: SymbolType | str) -> Any:
        return self._get("dividend_payout", symbol, type)

    def get_earnings(
        self,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        return self._get("earnings", symbol, type, period_type)

    def _get(
        self,
        name: str,
        symbol: str,
        type: SymbolType | str,
        period_type: PeriodType | str | None = None,
    ) -> Any:
        value = wire(type)
        if value not in SYMBOL_TYPES:
            raise InfowayAPIError.of_rest(int(RestErrorCode.PARAM_ERROR), "Param error：type")
        return self._http.get(
            f"/common/basic/financial/{name}",
            params=query(symbol=symbol, type=wire(type), period_type=wire(period_type)),
        )

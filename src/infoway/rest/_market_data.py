"""Shared market data methods for trade/depth/kline."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from infoway._http import HttpClient


class MarketDataMixin:
    """Mixin providing get_trade, get_depth, get_kline for a market data prefix."""

    _prefix: str
    _http: HttpClient

    def get_trade(self, codes: str) -> list[dict[str, Any]]:
        """Get real-time trade data.

        Args:
            codes: Comma-separated symbol codes (e.g. "AAPL.US" or "AAPL.US,TSLA.US")
        """
        return self._http.get(f"/{self._prefix}/batch_trade/{codes}")

    def get_depth(self, codes: str) -> list[dict[str, Any]]:
        """Get real-time order book depth.

        Args:
            codes: Comma-separated symbol codes
        """
        return self._http.get(f"/{self._prefix}/batch_depth/{codes}")

    def get_kline(self, codes: str, kline_type: int, count: int) -> list[dict[str, Any]]:
        """Get candlestick/K-line data.

        Args:
            codes: Comma-separated symbol codes
            kline_type: K-line interval (use KlineType enum or int 1-12)
            count: Number of candles to return
        """
        return self._http.post(
            f"/{self._prefix}/v2/batch_kline",
            json={"codes": codes, "klineType": int(kline_type), "klineCount": count},
        )

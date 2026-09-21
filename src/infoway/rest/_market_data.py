"""Shared market data methods for trade/depth/kline."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from infoway._normalize import normalize_depth, normalize_kline, normalize_trade

if TYPE_CHECKING:
    from infoway._http import HttpClient


class MarketDataMixin:
    """Mixin providing get_trade, get_depth, get_kline for a market data prefix.

    Field names come straight from the server and are **not** what an
    English-language guess would produce:

    * trade: ``s`` symbol, ``t`` epoch **ms**, ``p`` price, ``v`` volume,
      ``vw`` **turnover** (not VWAP), ``td`` trade direction.
    * depth: ``a``/``b`` are column-major ``[[price...],[qty...]]`` — not
      ``asks``/``bids`` and not a list of levels.
    * kline: each element is ``{"s": ..., "respList": [candle, ...]}`` — the
      candles are nested under ``respList``.

    Pass ``parse=True`` (per call, or client-wide via
    ``InfowayClient(parse=True)``) to get Decimals, datetimes, flattened klines
    and ``(price, qty)`` depth pairs instead.
    """

    _prefix: str
    _http: HttpClient
    _parse: bool = False

    def _should_parse(self, parse: bool | None) -> bool:
        return self._parse if parse is None else parse

    def get_trade(self, codes: str, parse: bool | None = None) -> list[dict[str, Any]]:
        """Get the latest trade for one or more instruments.

        Args:
            codes: Comma-separated codes (``"AAPL.US"`` or ``"AAPL.US,TSLA.US"``).
                Equity codes need their market suffix, and Hong Kong codes must be
                zero-padded to 5 digits (``00700.HK``, not ``700.HK``).
            parse: Override the client-wide normalisation setting.

        Returns:
            ``[{"s","t","p","v","vw","td"}, ...]``
        """
        data = self._http.get(f"/{self._prefix}/batch_trade/{codes}")
        return normalize_trade(data) if self._should_parse(parse) else data

    def get_depth(self, codes: str, parse: bool | None = None) -> list[dict[str, Any]]:
        """Get the order book snapshot.

        Returns:
            ``[{"s","t","a":[[prices],[qtys]],"b":[[prices],[qtys]]}, ...]``
            — with ``parse=True``, ``a``/``b`` become ``[(price, qty), ...]``.
        """
        data = self._http.get(f"/{self._prefix}/batch_depth/{codes}")
        return normalize_depth(data) if self._should_parse(parse) else data

    def get_kline(
        self,
        codes: str,
        kline_type: int,
        count: int,
        timestamp: int | None = None,
        parse: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Get candlestick/K-line data.

        Args:
            codes: Comma-separated codes. **Single instrument: up to 500 candles;
                with multiple instruments the server returns only 2 candles each.**
            kline_type: Interval (``KlineType`` enum or int 1-12).
            count: Number of candles requested.
            timestamp: Optional unix-seconds end time (minute / hour bars only).
            parse: Override the client-wide normalisation setting.

        Returns:
            ``[{"s": ..., "respList": [{"t","o","h","l","c","v","vw","pc","pca"}, ...]}]``
            — with ``parse=True`` this is flattened into a single list of candles.
        """
        body: dict[str, Any] = {
            "codes": codes,
            "klineType": int(kline_type),
            "klineNum": count,
        }
        if timestamp is not None:
            body["timestamp"] = timestamp
        data = self._http.post(f"/{self._prefix}/v2/batch_kline", json=body)
        return normalize_kline(data) if self._should_parse(parse) else data

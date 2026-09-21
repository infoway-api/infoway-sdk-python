"""Optional field-normalisation layer (``parse=True``).

The server is inconsistent in ways the SDK can absorb — see
``docs/specs/2026-08-15-sdk-contract-fix-design.md`` §5:

===========================================  ==========================================
server                                       normalised
===========================================  ==========================================
prices/quantities as strings ``"305.771"``   :class:`decimal.Decimal`
``t`` — trade/depth int **ms**,              timezone-aware :class:`datetime.datetime`
``t`` — kline str **seconds**                (unit decided per field, never guessed
                                             from the digit count)
``pc`` (REST) / ``pfr`` (WS) = ``"0.03%"``   ``change_percent`` as a ratio (``0.0003``)
kline wrapped in ``respList``                flattened to one list of candles
depth ``a``/``b`` column-major               ``[(price, qty), ...]``
``vw`` (actually **turnover**, not VWAP)     renamed ``turnover``
===========================================  ==========================================

Normalisation is off by default; raw server payloads are returned unchanged
unless ``parse=True`` is requested.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

__all__ = [
    "to_decimal",
    "from_epoch_ms",
    "from_epoch_seconds",
    "to_ratio",
    "transpose_levels",
    "normalize_trade",
    "normalize_depth",
    "normalize_kline",
    "normalize_ws_trade",
    "normalize_ws_depth",
    "normalize_ws_kline",
    "normalize_news",
]

# numeric fields shared by trade / depth / kline payloads
_PRICE_FIELDS = ("p", "o", "h", "l", "c", "v", "pca")


def to_decimal(value: Any) -> Any:
    """Convert a numeric string to :class:`~decimal.Decimal`, leaving anything else alone."""
    if value is None or isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value


def from_epoch_ms(value: Any) -> Any:
    """Millisecond epoch → aware :class:`~datetime.datetime` (trade / depth ``t``)."""
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return value


def from_epoch_seconds(value: Any) -> Any:
    """Second epoch → aware :class:`~datetime.datetime` (kline ``t``, news ``published``)."""
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return value


def to_ratio(value: Any) -> Any:
    """``"0.03%"`` → ``Decimal("0.0003")``; a bare number is taken as already-a-ratio."""
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith("%"):
        try:
            return Decimal(text[:-1]) / Decimal(100)
        except (InvalidOperation, ValueError):
            return value
    return to_decimal(value)


def transpose_levels(levels: Any) -> Any:
    """Column-major ``[[p1,p2,...],[q1,q2,...]]`` → ``[(p1,q1), (p2,q2), ...]``."""
    if not isinstance(levels, (list, tuple)) or len(levels) != 2:
        return levels
    prices, qtys = levels
    if not isinstance(prices, (list, tuple)) or not isinstance(qtys, (list, tuple)):
        return levels
    return [(to_decimal(p), to_decimal(q)) for p, q in zip(prices, qtys)]


def _decimalise(item: dict[str, Any]) -> dict[str, Any]:
    for key in _PRICE_FIELDS:
        if key in item:
            item[key] = to_decimal(item[key])
    if "vw" in item:
        # `vw` is turnover (vw / v gives the average price), NOT a VWAP
        item["turnover"] = to_decimal(item.pop("vw"))
    for key in ("pc", "pfr"):
        if key in item:
            item["change_percent"] = to_ratio(item.pop(key))
    return item


# ---------------------------------------------------------------------------
# REST payloads
# ---------------------------------------------------------------------------

def normalize_trade(data: Any) -> Any:
    """Normalise ``/{market}/batch_trade`` payloads (``t`` is an int in ms)."""
    if not isinstance(data, list):
        return data
    out = []
    for row in data:
        if not isinstance(row, dict):
            out.append(row)
            continue
        item = _decimalise(dict(row))
        if "t" in item:
            item["t"] = from_epoch_ms(item["t"])
        out.append(item)
    return out


def normalize_depth(data: Any) -> Any:
    """Normalise ``/{market}/batch_depth`` payloads (``a``/``b`` are column-major)."""
    if not isinstance(data, list):
        return data
    out = []
    for row in data:
        if not isinstance(row, dict):
            out.append(row)
            continue
        item = dict(row)
        if "t" in item:
            item["t"] = from_epoch_ms(item["t"])
        for side in ("a", "b"):
            if side in item:
                item[side] = transpose_levels(item[side])
        out.append(item)
    return out


def normalize_kline(data: Any) -> Any:
    """Flatten ``[{"s":..., "respList":[...]}]`` into one list of candles.

    Each candle keeps its instrument under ``s`` and gets ``t`` as a datetime
    (the server sends kline ``t`` as a **string in seconds**).
    """
    if not isinstance(data, list):
        return data
    out: list[Any] = []
    for row in data:
        if not isinstance(row, dict):
            out.append(row)
            continue
        symbol = row.get("s")
        candles = row.get("respList")
        if not isinstance(candles, list):
            out.append(_decimalise(dict(row)))
            continue
        for candle in candles:
            if not isinstance(candle, dict):
                out.append(candle)
                continue
            item = _decimalise(dict(candle))
            if symbol is not None:
                item["s"] = symbol
            if "t" in item:
                item["t"] = from_epoch_seconds(item["t"])
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# WebSocket payloads (already unwrapped from the envelope)
# ---------------------------------------------------------------------------

def normalize_ws_trade(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    item = _decimalise(dict(data))
    if "t" in item:
        item["t"] = from_epoch_ms(item["t"])
    return item


def normalize_ws_depth(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    item = dict(data)
    if "t" in item:
        item["t"] = from_epoch_ms(item["t"])
    for side in ("a", "b"):
        if side in item:
            item[side] = transpose_levels(item[side])
    return item


def normalize_ws_kline(data: Any) -> Any:
    """Normalise a 10008 push. ``ty`` (the interval) is preserved as-is."""
    if not isinstance(data, dict):
        return data
    item = _decimalise(dict(data))
    if "t" in item:
        item["t"] = from_epoch_seconds(item["t"])
    return item


def normalize_news(data: Any) -> Any:
    """Normalise a 10022 news push (``published`` is a Unix timestamp in seconds)."""
    if not isinstance(data, dict):
        return data
    item = dict(data)
    if "published" in item:
        item["published"] = from_epoch_seconds(item["published"])
    return item

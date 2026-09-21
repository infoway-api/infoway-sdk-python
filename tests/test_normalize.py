"""Optional normalisation layer (``parse=True``).

Every input below is a verbatim production payload.
See docs/specs/2026-08-15-sdk-contract-fix-design.md §5.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway._normalize import (
    from_epoch_ms,
    from_epoch_seconds,
    normalize_depth,
    normalize_kline,
    normalize_trade,
    normalize_ws_depth,
    normalize_ws_kline,
    normalize_ws_trade,
    to_decimal,
    to_ratio,
    transpose_levels,
)
from infoway.client import InfowayClient
from infoway.rest.crypto import CryptoClient
from infoway.rest.stock import StockClient
from tests.conftest import load_json, load_ws_frames

UTC = timezone.utc


def _ws_payload(name, code):
    for raw in load_ws_frames(f"ws/{name}"):
        msg = json.loads(raw) if raw.startswith("{") else {}
        if msg.get("code") == code:
            return msg["data"]
    raise AssertionError(f"no code={code} frame in {name}")


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------

def test_to_decimal():
    assert to_decimal("305.771") == Decimal("305.771")
    assert isinstance(to_decimal("305.771"), Decimal)
    assert to_decimal(None) is None
    assert to_decimal("not-a-number") == "not-a-number"


def test_to_ratio_converts_percent_string():
    assert to_ratio("0.03%") == Decimal("0.0003")
    assert to_ratio("-0.01%") == Decimal("-0.0001")
    assert to_ratio("0.00%") == Decimal("0")


def test_timestamp_units_are_per_field_not_guessed_from_digits():
    """kline `t` is always seconds and trade/depth `t` always ms — never inferred."""
    assert from_epoch_ms(1786751999691) == datetime(2026, 8, 14, 23, 59, 59, 691000, tzinfo=UTC)
    assert from_epoch_seconds("1786737540") == datetime(2026, 8, 14, 19, 59, tzinfo=UTC)
    # a 13-digit value in a *seconds* field must NOT be silently rescaled to ms;
    # it is out of datetime range, so it comes back untouched instead
    assert from_epoch_seconds(1786751999691) == 1786751999691
    # ...and a seconds value in a ms field is likewise not rescaled
    assert from_epoch_ms(1786737540) == datetime(1970, 1, 21, 16, 18, 57, 540000, tzinfo=UTC)


def test_transpose_levels():
    assert transpose_levels([["305.800"], ["229"]]) == [(Decimal("305.800"), Decimal("229"))]
    assert transpose_levels([]) == []


# --------------------------------------------------------------------------
# REST trade
# --------------------------------------------------------------------------

def test_normalize_trade_from_real_payload():
    data = load_json("rest/stock_trade.json")["data"]
    [row] = normalize_trade(data)
    assert row["s"] == "AAPL.US"
    assert row["p"] == Decimal("305.771")
    assert row["v"] == Decimal("1")
    assert row["t"] == datetime(2026, 8, 14, 23, 59, 59, 691000, tzinfo=UTC)
    # `vw` is turnover, not a VWAP — the English docs had it backwards
    assert row["turnover"] == Decimal("305.771")
    assert "vw" not in row
    assert row["td"] == 0


def test_normalize_trade_crypto():
    data = load_json("rest/crypto_trade.json")["data"]
    [row] = normalize_trade(data)
    assert row["s"] == "BTCUSDT"
    assert row["p"] == Decimal("63059.36")
    assert row["turnover"] == Decimal("665.9068416")
    # turnover / volume == price  (proves vw is an amount, not an average price)
    assert (row["turnover"] / row["v"]).quantize(Decimal("0.01")) == Decimal("63059.36")


# --------------------------------------------------------------------------
# REST depth
# --------------------------------------------------------------------------

def test_normalize_depth_transposes_columns_to_pairs():
    data = load_json("rest/stock_depth.json")["data"]
    [row] = normalize_depth(data)
    assert row["s"] == "AAPL.US"
    assert row["t"] == datetime(2026, 8, 14, 23, 49, 57, 726000, tzinfo=UTC)
    assert row["a"] == [(Decimal("305.800"), Decimal("229"))]
    assert row["b"] == [(Decimal("305.770"), Decimal("24"))]


def test_normalize_depth_multi_level_crypto():
    data = load_json("rest/crypto_depth.json")["data"]
    [row] = normalize_depth(data)
    assert len(row["a"]) == 5 and len(row["b"]) == 5
    prices = [p for p, _ in row["a"]]
    assert prices == sorted(prices), "asks must stay in ascending price order"
    for price, qty in row["a"]:
        assert isinstance(price, Decimal) and isinstance(qty, Decimal)


# --------------------------------------------------------------------------
# REST kline
# --------------------------------------------------------------------------

def test_normalize_kline_flattens_resplist():
    data = load_json("rest/stock_kline.json")["data"]
    candles = normalize_kline(data)
    assert len(candles) == 2
    first = candles[0]
    assert "respList" not in first
    assert first["s"] == "AAPL.US"
    assert first["o"] == Decimal("305.830")
    assert first["h"] == Decimal("305.990")
    assert first["l"] == Decimal("305.675")
    assert first["c"] == Decimal("305.930")
    assert first["v"] == Decimal("331559")
    assert first["turnover"] == Decimal("101402874.954")
    assert first["change_percent"] == Decimal("0.0003")   # "0.03%"
    assert "pc" not in first and "vw" not in first
    assert first["t"] == datetime(2026, 8, 14, 19, 59, tzinfo=UTC)


# --------------------------------------------------------------------------
# WebSocket payloads
# --------------------------------------------------------------------------

def test_normalize_ws_trade():
    payload = _ws_payload("crypto_trade.jsonl", 10002)
    row = normalize_ws_trade(payload)
    assert row["s"] == "BTCUSDT"
    assert row["p"] == Decimal("63039")
    assert row["t"] == datetime(2026, 8, 15, 6, 27, 7, 483000, tzinfo=UTC)
    assert row["turnover"] == Decimal("5000.88387")


def test_normalize_ws_depth():
    payload = _ws_payload("crypto_depth.jsonl", 10005)
    row = normalize_ws_depth(payload)
    assert row["t"] == datetime(2026, 8, 15, 6, 27, 15, 640000, tzinfo=UTC)
    assert row["a"][0] == (Decimal("63039.00000000"), Decimal("45.06645000"))
    assert len(row["b"]) == 5


def test_normalize_ws_kline_keeps_ty_and_uses_seconds():
    payload = _ws_payload("crypto_kline.jsonl", 10008)
    row = normalize_ws_kline(payload)
    assert row["ty"] == 1
    assert row["t"] == datetime(2026, 8, 15, 6, 27, tzinfo=UTC)
    assert row["c"] == Decimal("63039.00000")
    # WS calls it pfr, REST calls it pc — both land on change_percent
    assert row["change_percent"] == Decimal("-0.0001")
    assert "pfr" not in row


# --------------------------------------------------------------------------
# wiring: parse=False by default
# --------------------------------------------------------------------------

@respx.mock
def test_rest_parse_is_off_by_default():
    stock = StockClient(HttpClient(api_key="k", max_retries=1))
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_trade.json"))
    )
    row = stock.get_trade("AAPL.US")[0]
    assert row["p"] == "305.771"          # untouched string
    assert row["t"] == 1786751999691      # untouched int
    assert "vw" in row and "turnover" not in row


@respx.mock
def test_rest_parse_per_call():
    stock = StockClient(HttpClient(api_key="k", max_retries=1))
    respx.get("https://data.infoway.io/stock/batch_trade/AAPL.US").mock(
        return_value=httpx.Response(200, json=load_json("rest/stock_trade.json"))
    )
    row = stock.get_trade("AAPL.US", parse=True)[0]
    assert row["p"] == Decimal("305.771")
    assert row["turnover"] == Decimal("305.771")


@respx.mock
def test_rest_parse_client_wide_default():
    client = InfowayClient(api_key="k", max_retries=1, parse=True)
    respx.post("https://data.infoway.io/crypto/v2/batch_kline").mock(
        return_value=httpx.Response(200, json=load_json("rest/crypto_kline.json"))
    )
    candles = client.crypto.get_kline("BTCUSDT", kline_type=1, count=2)
    assert isinstance(candles, list) and candles
    assert all("respList" not in c for c in candles)
    assert all(c["s"] == "BTCUSDT" for c in candles)
    assert isinstance(candles[0]["c"], Decimal)
    assert isinstance(candles[0]["t"], datetime)


@respx.mock
def test_rest_per_call_parse_overrides_client_default():
    client = InfowayClient(api_key="k", max_retries=1, parse=True)
    respx.get("https://data.infoway.io/crypto/batch_depth/BTCUSDT").mock(
        return_value=httpx.Response(200, json=load_json("rest/crypto_depth.json"))
    )
    row = client.crypto.get_depth("BTCUSDT", parse=False)[0]
    assert row["a"] == load_json("rest/crypto_depth.json")["data"][0]["a"]


async def test_ws_parse_flag_normalises_callbacks():
    from unittest.mock import AsyncMock

    from infoway.ws.client import InfowayWebSocket

    w = InfowayWebSocket(api_key="k", business="crypto", parse=True)
    w.on_kline = AsyncMock()
    for raw in load_ws_frames("ws/crypto_kline.jsonl"):
        if '"code":10008' in raw:
            await w._dispatch(raw)
            break
    payload = w.on_kline.call_args.args[0]
    assert payload["ty"] == 1
    assert isinstance(payload["c"], Decimal)
    assert isinstance(payload["t"], datetime)

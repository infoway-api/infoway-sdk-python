"""Shared test fixtures.

All golden fixtures under ``tests/fixtures/`` are **verbatim production
responses** captured from https://data.infoway.io on 2026-08-15.
No hand-written/imagined payloads are allowed in this test suite.
"""

import json
from pathlib import Path

import pytest

API_KEY = "test-api-key-for-unit-tests"

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str):
    """Load a verbatim captured REST response, e.g. ``rest/stock_trade.json``."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def load_ws_frames(name: str, direction: str = "recv") -> list[str]:
    """Return the raw WS frames of a captured session (``ws/*.jsonl``)."""
    frames = []
    for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("_dir") == direction:
            frames.append(rec["_raw"])
    return frames


@pytest.fixture
def api_key():
    return API_KEY


@pytest.fixture
def fixtures_dir():
    return FIXTURES

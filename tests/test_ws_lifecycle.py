"""Server-driven lifecycle: drop, reconnect, resubscribe, close."""

from __future__ import annotations

import asyncio
import json

import pytest
import websockets
from unittest.mock import AsyncMock

from infoway._types import KlineType, WsCode
from infoway.ws.client import InfowayWebSocket


class LifeServer:
    def __init__(self) -> None:
        self.connections = 0
        self.received: list[str] = []
        self.clients: list = []
        self._server = None
        self.url = ""

    async def start(self) -> None:
        async def handler(ws):
            self.connections += 1
            self.clients.append(ws)
            try:
                await ws.send(json.dumps({"code": 200, "msg": "ws connect success"}))
                async for raw in ws:
                    self.received.append(raw if isinstance(raw, str) else raw.decode())
            finally:
                if ws in self.clients:
                    self.clients.remove(ws)

        self._server = await websockets.serve(handler, "127.0.0.1", 0)
        port = self._server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/ws"

    async def drop_all(self) -> None:
        for ws in list(self.clients):
            await ws.close()
        self.clients.clear()

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()


def _codes(frames: list[str]) -> list[int]:
    out = []
    for raw in frames:
        try:
            out.append(json.loads(raw)["code"])
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return out


def _client(url: str) -> InfowayWebSocket:
    w = InfowayWebSocket(api_key="k", business="crypto", base_url=url)
    w._heartbeat_interval = 0.08
    w._initial_backoff = 0.02
    w._backoff = 0.02
    return w


async def _until(pred, timeout: float = 4.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if pred():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not met")


@pytest.fixture
async def life():
    srv = LifeServer()
    await srv.start()
    try:
        yield srv
    finally:
        await srv.close()


@pytest.mark.asyncio
async def test_drop_reconnects_once_and_resubscribes(life):
    w = _client(life.url)
    w.on_reconnect = AsyncMock()
    w.on_disconnect = AsyncMock()
    ticks: list = []

    async def on_trade(data):
        ticks.append(data)

    w.on_trade = on_trade
    await w.subscribe_trade("BTCUSDT")
    task = asyncio.create_task(w.connect())
    await _until(lambda: life.connections == 1 and life.received)
    w.on_reconnect.assert_not_awaited()
    assert _codes(life.received).count(int(WsCode.SUB_TRADE)) == 1

    await life.drop_all()
    await _until(lambda: life.connections == 2)
    await _until(lambda: _codes(life.received).count(int(WsCode.SUB_TRADE)) >= 2)
    w.on_reconnect.assert_awaited()
    w.on_disconnect.assert_awaited()
    assert life.connections == 2
    assert w._heartbeat_gens == 2

    await life.clients[0].send(json.dumps({"code": 10002, "data": {"s": "BTCUSDT", "p": "1"}}))
    await _until(lambda: len(ticks) == 1)
    assert ticks[0]["s"] == "BTCUSDT"

    await asyncio.sleep(0.08)
    assert life.connections == 2
    await w.close()
    await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
async def test_user_close_does_not_reconnect(life):
    w = _client(life.url)
    w.on_disconnect = AsyncMock()
    w.on_reconnect = AsyncMock()
    task = asyncio.create_task(w.connect())
    await _until(lambda: life.connections == 1)
    await w.close()
    await asyncio.wait_for(task, timeout=1)
    await asyncio.sleep(0.15)
    assert life.connections == 1
    w.on_disconnect.assert_not_awaited()
    w.on_reconnect.assert_not_awaited()


@pytest.mark.asyncio
async def test_unsubscribe_is_not_replayed(life):
    w = _client(life.url)
    task = asyncio.create_task(w.connect())
    await _until(lambda: life.connections == 1)
    await w.subscribe_trade("BTCUSDT")
    await w.subscribe_depth("BTCUSDT")
    await _until(lambda: int(WsCode.SUB_DEPTH) in _codes(life.received))
    await w.unsubscribe_trade("BTCUSDT")
    await _until(lambda: int(WsCode.UNSUB_TRADE) in _codes(life.received))
    life.received.clear()
    await life.drop_all()
    await _until(lambda: life.connections == 2)
    await _until(lambda: life.received)
    await asyncio.sleep(0.04)
    assert int(WsCode.SUB_DEPTH) in _codes(life.received)
    assert int(WsCode.SUB_TRADE) not in _codes(life.received)
    await w.close()
    await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
async def test_kline_interval_kept_after_reconnect(life):
    w = _client(life.url)
    task = asyncio.create_task(w.connect())
    await _until(lambda: life.connections == 1)
    await w.subscribe_kline("BTCUSDT", KlineType.MIN_1)
    await w.subscribe_kline("BTCUSDT", KlineType.DAY)
    await w.unsubscribe_kline("BTCUSDT", KlineType.MIN_1)
    await _until(lambda: int(WsCode.UNSUB_KLINE) in _codes(life.received))
    life.received.clear()
    await life.drop_all()
    await _until(lambda: life.connections == 2)
    await _until(lambda: life.received)
    await asyncio.sleep(0.04)
    kline = [json.loads(r) for r in life.received if json.loads(r).get("code") == int(WsCode.SUB_KLINE)]
    assert len(kline) == 1
    assert kline[0]["data"]["arr"][0]["type"] == int(KlineType.DAY)
    await w.close()
    await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
async def test_subscribe_while_offline_is_flushed(life):
    w = _client(life.url)
    task = asyncio.create_task(w.connect())
    await _until(lambda: life.connections == 1)
    await life.drop_all()
    await w.subscribe_trade("ETHUSDT")
    await _until(lambda: life.connections == 2)
    await _until(lambda: int(WsCode.SUB_TRADE) in _codes(life.received))
    last = next(
        json.loads(r)
        for r in reversed(life.received)
        if json.loads(r).get("code") == int(WsCode.SUB_TRADE)
    )
    assert last["data"]["codes"] == "ETHUSDT"
    await w.close()
    await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
async def test_handshake_honors_max_reconnect():
    hits = 0

    async def _http(reader, writer):
        nonlocal hits
        hits += 1
        writer.write(b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(_http, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    w = InfowayWebSocket(
        api_key="k",
        business="crypto",
        base_url=f"ws://127.0.0.1:{port}/ws",
        max_reconnect_attempts=1,
    )
    w._initial_backoff = 0.02
    w._backoff = 0.02
    task = asyncio.create_task(w.connect())
    await asyncio.wait_for(task, timeout=2)
    server.close()
    await server.wait_closed()
    assert hits == 2


@pytest.mark.asyncio
async def test_news_drop_replays_lang(life):
    from infoway.ws.news import InfowayNewsWebSocket

    n = InfowayNewsWebSocket(api_key="k", base_url=life.url, lang="en")
    n._heartbeat_interval = 0.08
    n._initial_backoff = 0.02
    n._backoff = 0.02
    n.on_reconnect = AsyncMock()
    task = asyncio.create_task(n.connect())
    await _until(lambda: life.connections == 1 and any("lang" in r for r in life.received))
    n.on_reconnect.assert_not_awaited()
    life.received.clear()
    await life.drop_all()
    await _until(lambda: life.connections == 2 and any('"lang": "en"' in r or '"lang":"en"' in r for r in life.received))
    n.on_reconnect.assert_awaited()
    await n.close()
    await asyncio.wait_for(task, timeout=1)

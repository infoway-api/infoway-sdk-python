"""WebSocket client with auto-reconnect, heartbeat, and subscription management."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Awaitable

import websockets
from websockets.asyncio.client import ClientConnection

from infoway._types import WsCode

logger = logging.getLogger("infoway.ws")

_BASE_WS_URL = "wss://data.infoway.io/ws"
_HEARTBEAT_INTERVAL = 30
_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 30.0


class InfowayWebSocket:
    """Async WebSocket client for Infoway real-time data feeds.

    Usage::

        ws = InfowayWebSocket(api_key="YOUR_API_KEY", business="stock")
        ws.on_trade = my_trade_handler
        await ws.connect()
        await ws.subscribe_trade("AAPL.US,TSLA.US")

    Features:
        - Auto-reconnect with exponential backoff (1s -> 30s cap)
        - Auto-resubscribe on reconnect
        - Heartbeat keepalive (30s interval)
        - Event callbacks: on_trade, on_depth, on_kline, on_error, on_reconnect, on_disconnect
    """

    def __init__(
        self,
        api_key: str,
        business: str,
        base_url: str = _BASE_WS_URL,
        max_reconnect_attempts: int | None = None,
    ):
        self._url = f"{base_url}?business={business}&apikey={api_key}"
        self._business = business
        self._max_reconnect = max_reconnect_attempts
        self._ws: ClientConnection | None = None
        self._subscriptions: set[tuple[str, str]] = set()
        self._running = False
        self._backoff = _INITIAL_BACKOFF

        self.on_trade: Callable[[dict], Awaitable[None]] | None = None
        self.on_depth: Callable[[dict], Awaitable[None]] | None = None
        self.on_kline: Callable[[dict], Awaitable[None]] | None = None
        self.on_error: Callable[[Exception], Awaitable[None]] | None = None
        self.on_reconnect: Callable[[], Awaitable[None]] | None = None
        self.on_disconnect: Callable[[], Awaitable[None]] | None = None

    def _build_message(self, code: int, codes: str | None = None) -> str:
        msg: dict[str, Any] = {"code": int(code), "trace": uuid.uuid4().hex[:12]}
        if codes is not None:
            msg["data"] = {"codes": codes}
        return json.dumps(msg)

    async def connect(self):
        """Connect and start the message loop. Blocks until disconnect/close."""
        self._running = True
        attempt = 0
        while self._running:
            try:
                async with websockets.connect(self._url, close_timeout=5) as ws:
                    self._ws = ws
                    self._backoff = _INITIAL_BACKOFF
                    attempt = 0
                    logger.info("WebSocket connected to %s", self._business)

                    try:
                        init_msg = await asyncio.wait_for(ws.recv(), timeout=5)
                        logger.debug("Init: %s", init_msg)
                    except asyncio.TimeoutError:
                        pass

                    if self._subscriptions:
                        await self._resubscribe()
                        if self.on_reconnect:
                            await self.on_reconnect()

                    await asyncio.gather(
                        self._heartbeat_loop(),
                        self._message_loop(),
                    )
            except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                if not self._running:
                    break
                attempt += 1
                if self._max_reconnect and attempt > self._max_reconnect:
                    logger.error("Max reconnect attempts (%d) reached", self._max_reconnect)
                    break
                logger.warning(
                    "Connection lost (%s), reconnecting in %.1fs (attempt %d)...",
                    e, self._backoff, attempt,
                )
                if self.on_disconnect:
                    await self.on_disconnect()
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, _MAX_BACKOFF)
            except Exception as e:
                if self.on_error:
                    await self.on_error(e)
                if not self._running:
                    break
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, _MAX_BACKOFF)

    async def _message_loop(self):
        assert self._ws is not None
        async for raw in self._ws:
            try:
                msg = json.loads(raw)
                code = msg.get("code")
                if code == WsCode.PUSH_TRADE and self.on_trade:
                    await self.on_trade(msg)
                elif code == WsCode.PUSH_DEPTH and self.on_depth:
                    await self.on_depth(msg)
                elif code == WsCode.PUSH_KLINE and self.on_kline:
                    await self.on_kline(msg)
                elif code == WsCode.HEARTBEAT:
                    logger.debug("Heartbeat pong received")
                else:
                    logger.debug("Message: %s", raw[:200] if isinstance(raw, str) else raw)
            except json.JSONDecodeError:
                logger.debug("Non-JSON message: %s", raw[:200] if isinstance(raw, str) else raw)

    async def _heartbeat_loop(self):
        assert self._ws is not None
        while self._running and self._ws:
            try:
                await self._ws.send(self._build_message(WsCode.HEARTBEAT))
                logger.debug("Heartbeat sent")
            except Exception:
                return
            await asyncio.sleep(_HEARTBEAT_INTERVAL)

    async def _resubscribe(self):
        assert self._ws is not None
        code_map = {
            "trade": WsCode.SUB_TRADE,
            "depth": WsCode.SUB_DEPTH,
            "kline": WsCode.SUB_KLINE,
        }
        for sub_type, codes in self._subscriptions:
            ws_code = code_map.get(sub_type)
            if ws_code:
                await self._ws.send(self._build_message(ws_code, codes))
                logger.info("Re-subscribed %s: %s", sub_type, codes)

    async def subscribe_trade(self, codes: str):
        self._subscriptions.add(("trade", codes))
        if self._ws:
            await self._ws.send(self._build_message(WsCode.SUB_TRADE, codes))

    async def subscribe_depth(self, codes: str):
        self._subscriptions.add(("depth", codes))
        if self._ws:
            await self._ws.send(self._build_message(WsCode.SUB_DEPTH, codes))

    async def subscribe_kline(self, codes: str):
        self._subscriptions.add(("kline", codes))
        if self._ws:
            await self._ws.send(self._build_message(WsCode.SUB_KLINE, codes))

    async def unsubscribe_trade(self, codes: str):
        self._subscriptions.discard(("trade", codes))
        if self._ws:
            await self._ws.send(self._build_message(WsCode.UNSUB_TRADE, codes))

    async def unsubscribe_depth(self, codes: str):
        self._subscriptions.discard(("depth", codes))
        if self._ws:
            await self._ws.send(self._build_message(WsCode.UNSUB_DEPTH, codes))

    async def unsubscribe_kline(self, codes: str):
        self._subscriptions.discard(("kline", codes))
        if self._ws:
            await self._ws.send(self._build_message(WsCode.UNSUB_KLINE, codes))

    async def close(self):
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

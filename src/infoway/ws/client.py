"""WebSocket client with auto-reconnect, heartbeat, and subscription management."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Awaitable

import websockets
from websockets.asyncio.client import ClientConnection

from infoway._types import KlineType, WsCode

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
        - User callbacks are wrapped — an exception in user code does not kill the connection
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
        # subscription state: (sub_type, codes, kline_type) — kline_type is 0 for trade/depth
        self._subscriptions: set[tuple[str, str, int]] = set()
        self._running = False
        self._backoff = _INITIAL_BACKOFF

        self.on_trade: Callable[[dict], Awaitable[None]] | None = None
        self.on_depth: Callable[[dict], Awaitable[None]] | None = None
        self.on_kline: Callable[[dict], Awaitable[None]] | None = None
        self.on_error: Callable[[Exception], Awaitable[None]] | None = None
        self.on_reconnect: Callable[[], Awaitable[None]] | None = None
        self.on_disconnect: Callable[[], Awaitable[None]] | None = None

    def _build_codes_message(self, code: int, codes: str | None) -> str:
        msg: dict[str, Any] = {"code": int(code), "trace": uuid.uuid4().hex[:12]}
        if codes is not None:
            msg["data"] = {"codes": codes}
        return json.dumps(msg)

    def _build_kline_message(self, code: int, codes: str, kline_type: int) -> str:
        return json.dumps({
            "code": int(code),
            "trace": uuid.uuid4().hex[:12],
            "data": {"arr": [{"codes": codes, "type": int(kline_type)}]},
        })

    async def _safe_call(self, cb, *args, name: str = "callback"):
        if cb is None:
            return
        try:
            await cb(*args)
        except Exception:
            logger.exception("User %s raised — connection preserved", name)

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

                    if self._subscriptions:
                        await self._resubscribe()
                        await self._safe_call(self.on_reconnect, name="on_reconnect")

                    await asyncio.gather(
                        self._heartbeat_loop(),
                        self._message_loop(),
                    )
            except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                self._ws = None
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
                await self._safe_call(self.on_disconnect, name="on_disconnect")
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, _MAX_BACKOFF)
            except Exception as e:
                self._ws = None
                await self._safe_call(self.on_error, e, name="on_error")
                if not self._running:
                    break
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, _MAX_BACKOFF)

    async def _message_loop(self):
        assert self._ws is not None
        async for raw in self._ws:
            # The server sends a plaintext greeting on connect — skip non-JSON.
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                logger.debug("Non-JSON message: %s", raw[:200] if isinstance(raw, (str, bytes)) else raw)
                continue
            code = msg.get("code")
            if code == WsCode.PUSH_TRADE:
                await self._safe_call(self.on_trade, msg, name="on_trade")
            elif code == WsCode.PUSH_DEPTH:
                await self._safe_call(self.on_depth, msg, name="on_depth")
            elif code == WsCode.PUSH_KLINE:
                await self._safe_call(self.on_kline, msg, name="on_kline")
            elif code in (WsCode.SUB_TRADE_ACK, WsCode.SUB_DEPTH_ACK,
                          WsCode.SUB_KLINE_ACK, WsCode.UNSUB_ACK):
                logger.debug("Sub/unsub ack: code=%s", code)
            elif code == WsCode.HEARTBEAT:
                logger.debug("Heartbeat received")
            else:
                logger.debug("Unhandled code %s: %s", code, raw[:200] if isinstance(raw, str) else raw)

    async def _heartbeat_loop(self):
        assert self._ws is not None
        while self._running and self._ws:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            try:
                await self._ws.send(self._build_codes_message(WsCode.HEARTBEAT, None))
                logger.debug("Heartbeat sent")
            except Exception:
                # let the message_loop / websockets raise ConnectionClosed in the outer scope
                return

    async def _resubscribe(self):
        assert self._ws is not None
        for sub_type, codes, kline_type in self._subscriptions:
            if sub_type == "trade":
                await self._ws.send(self._build_codes_message(WsCode.SUB_TRADE, codes))
            elif sub_type == "depth":
                await self._ws.send(self._build_codes_message(WsCode.SUB_DEPTH, codes))
            elif sub_type == "kline":
                await self._ws.send(self._build_kline_message(WsCode.SUB_KLINE, codes, kline_type))
            logger.info("Re-subscribed %s: %s", sub_type, codes)

    async def subscribe_trade(self, codes: str):
        self._subscriptions.add(("trade", codes, 0))
        if self._ws:
            await self._ws.send(self._build_codes_message(WsCode.SUB_TRADE, codes))

    async def subscribe_depth(self, codes: str):
        self._subscriptions.add(("depth", codes, 0))
        if self._ws:
            await self._ws.send(self._build_codes_message(WsCode.SUB_DEPTH, codes))

    async def subscribe_kline(self, codes: str, kline_type: KlineType | int = KlineType.MIN_1):
        t = int(kline_type)
        self._subscriptions.add(("kline", codes, t))
        if self._ws:
            await self._ws.send(self._build_kline_message(WsCode.SUB_KLINE, codes, t))

    async def unsubscribe_trade(self, codes: str):
        self._subscriptions.discard(("trade", codes, 0))
        if self._ws:
            await self._ws.send(self._build_codes_message(WsCode.UNSUB_TRADE, codes))

    async def unsubscribe_depth(self, codes: str):
        self._subscriptions.discard(("depth", codes, 0))
        if self._ws:
            await self._ws.send(self._build_codes_message(WsCode.UNSUB_DEPTH, codes))

    async def unsubscribe_kline(self, codes: str, kline_type: KlineType | int = KlineType.MIN_1):
        self._subscriptions.discard(("kline", codes, int(kline_type)))
        if self._ws:
            await self._ws.send(self._build_codes_message(WsCode.UNSUB_KLINE, codes))

    async def close(self):
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

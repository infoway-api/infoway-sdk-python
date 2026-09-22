"""WebSocket client with auto-reconnect, heartbeat, and subscription management."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import uuid
from contextlib import suppress
from typing import Any, Awaitable, Callable, Iterable

import websockets
from websockets.asyncio.client import ClientConnection

from infoway._normalize import normalize_ws_depth, normalize_ws_kline, normalize_ws_trade
from infoway._types import KlineType, WsCode, WsErrorCode, wire
from infoway.exceptions import InfowayAPIError, InfowayAuthError, InfowayRateLimitError

logger = logging.getLogger("infoway.ws")

_BASE_WS_URL = "wss://data.infoway.io/ws"
_HEARTBEAT_INTERVAL = 30
_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 30.0

#: Frame the server sends on a successful handshake — informational, not an error.
WS_CONNECT_OK = 200


def join_codes(codes: str | Iterable[str]) -> str:
    """Merge an iterable of codes into the single comma-joined string the server wants.

    The gateway allows only **60 frames per minute per connection** (heartbeats
    included), so one frame per symbol will get the connection dropped.
    """
    if isinstance(codes, str):
        return codes
    return ",".join(str(c).strip() for c in codes if str(c).strip())


def handshake_status(exc: BaseException) -> int | None:
    """Extract the HTTP status from a websockets handshake rejection.

    ``websockets`` >= 14 raises ``InvalidStatus`` (``.response.status_code``);
    older versions raise ``InvalidStatusCode`` (``.status_code``).
    """
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(exc, "status_code", None)
    return int(status) if status is not None else None


class InfowayWebSocket:
    """Async WebSocket client for Infoway real-time market data feeds.

    Usage::

        ws = InfowayWebSocket(api_key="YOUR_API_KEY", business="crypto")
        ws.on_trade = my_trade_handler          # receives msg["data"]
        await ws.subscribe_trade("BTCUSDT,ETHUSDT")
        await ws.connect()

    Behaviour worth knowing (verified against production, 2026-08-15):

    * On ``business=stock`` the first frame is **plain text**
      (``You have permission to subscribe to all market data``); it is skipped.
    * ``{"code":200,"msg":"ws connect success"}`` is the welcome frame, not an error.
    * A bad/unauthorised API key is rejected at the **HTTP handshake** with 401.
      That raises :class:`~infoway.exceptions.InfowayAuthError` and reconnecting
      stops — retrying a rejected key risks getting the IP banned.
    * Callbacks receive ``msg["data"]`` (same unwrapping as the REST layer).
    * The server sends **no acknowledgement for heartbeats** (code 10010) — never
      treat a missing heartbeat reply as a dead connection.
    * A ``10001``/``10004``/``10007`` ack only means the frame was accepted. Wrong
      ``business`` or a non-existent code is also acked and then stays silent
      forever — pick the channel that matches your instruments.
    * All frames (subscribe + unsubscribe + heartbeat) share a budget of
      **60 per minute per connection**; always merge codes into one frame.
    """

    def __init__(
        self,
        api_key: str | None = None,
        business: str | None = None,
        base_url: str = _BASE_WS_URL,
        max_reconnect_attempts: int | None = None,
        parse: bool = False,
        print_frames: bool = False,
    ):
        from infoway._http import resolve_api_key
        key = resolve_api_key(api_key)
        if not key:
            raise ValueError("apiKey is required (set INFOWAY_API_KEY or pass api_key)")
        channel = wire(business)
        if not channel:
            raise ValueError("business is required (stock/japan/india/korea/taiwan/crypto/common)")
        self._url = f"{base_url}?business={channel}&apikey={key}"
        self._business = channel
        self._max_reconnect = max_reconnect_attempts
        self._parse = parse
        self._print_frames = print_frames
        self._ws: ClientConnection | None = None
        # subscription state: (sub_type, codes, kline_type) — kline_type is 0 for trade/depth
        self._subscriptions: set[tuple[str, str, int]] = set()
        self._include_ty: set[str] = set()
        self._running = False
        self._initial_backoff = _INITIAL_BACKOFF
        self._backoff = _INITIAL_BACKOFF
        self._heartbeat_interval = _HEARTBEAT_INTERVAL
        self._heartbeat_gens = 0
        self._ever_connected = False
        self._stop: asyncio.Event | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

        self.on_trade: Callable[[dict], Awaitable[None]] | None = None
        self.on_depth: Callable[[dict], Awaitable[None]] | None = None
        self.on_kline: Callable[[dict], Awaitable[None]] | None = None
        self.on_frame: Callable[[str], Awaitable[None] | None] | None = None
        self.on_error: Callable[[Exception], Awaitable[None]] | None = None
        self.on_reconnect: Callable[[], Awaitable[None]] | None = None
        self.on_disconnect: Callable[[], Awaitable[None]] | None = None

    # ------------------------------------------------------------------
    # frame building
    # ------------------------------------------------------------------

    def _build_codes_message(
        self,
        code: int,
        codes: str | Iterable[str] | None,
        include_ty: bool = False,
    ) -> str:
        msg: dict[str, Any] = {"code": int(code), "trace": uuid.uuid4().hex[:12]}
        if codes is not None:
            data: dict[str, Any] = {"codes": join_codes(codes)}
            if include_ty:
                data["includeTy"] = True
            msg["data"] = data
        return json.dumps(msg)

    def _build_kline_message(
        self, code: int, codes: str | Iterable[str], kline_type: int
    ) -> str:
        return json.dumps({
            "code": int(code),
            "trace": uuid.uuid4().hex[:12],
            "data": {"arr": [{"codes": join_codes(codes), "type": int(kline_type)}]},
        })

    def _build_kline_unsub_message(
        self, code: int, codes: str | Iterable[str], kline_type: int
    ) -> str:
        """Unsubscribe one interval only.

        Sending just ``{"codes": ...}`` makes the server drop **every** interval
        subscribed for those instruments.
        """
        return json.dumps({
            "code": int(code),
            "trace": uuid.uuid4().hex[:12],
            "data": {"codes": join_codes(codes), "klineTypes": str(int(kline_type))},
        })

    async def _safe_call(self, cb, *args, name: str = "callback"):
        if cb is None:
            return
        try:
            result = cb(*args)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("User %s raised — connection preserved", name)

    # ------------------------------------------------------------------
    # connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        """Connect and run the message loop. Blocks until closed.

        Raises:
            InfowayAuthError: if the server rejects the API key at the handshake
                (HTTP 401). Reconnecting is *not* attempted in that case.
        """
        self._running = True
        self._stop = asyncio.Event()
        attempt = 0
        while self._running:
            drop_reason: str | None = None
            try:
                async with websockets.connect(
                    self._url,
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                    max_queue=256,
                    compression=None,
                ) as ws:
                    self._ws = ws
                    self._backoff = self._initial_backoff
                    attempt = 0
                    logger.info("WebSocket connected to %s", self._business)

                    reconnected = self._ever_connected
                    self._ever_connected = True
                    if self._subscriptions:
                        await self._resubscribe()
                    if reconnected:
                        await self._safe_call(self.on_reconnect, name="on_reconnect")

                    self._heartbeat_gens += 1
                    hb = asyncio.create_task(self._heartbeat_loop(), name="infoway-ws-heartbeat")
                    self._heartbeat_task = hb
                    try:
                        await self._message_loop()
                    finally:
                        self._ws = None
                        self._heartbeat_task = None
                        hb.cancel()
                        with suppress(asyncio.CancelledError):
                            await hb
                    if self._running:
                        drop_reason = "peer closed"
            except websockets.InvalidHandshake as e:
                self._ws = None
                status = handshake_status(e)
                if status == 401:
                    self._running = False
                    raise InfowayAuthError(
                        "WebSocket handshake rejected with HTTP 401 — the API key is "
                        "invalid or not authorised for this channel. Not reconnecting."
                    ) from e
                drop_reason = f"handshake HTTP {status}"
            except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                self._ws = None
                drop_reason = str(e)
            except Exception as e:
                self._ws = None
                await self._safe_call(self.on_error, e, name="on_error")
                drop_reason = str(e)

            if not self._running or drop_reason is None:
                break
            attempt += 1
            if self._max_reconnect and attempt > self._max_reconnect:
                logger.error("Max reconnect attempts (%d) reached", self._max_reconnect)
                break
            logger.warning(
                "Connection lost (%s), reconnecting in %.1fs (attempt %d)...",
                drop_reason, self._backoff, attempt,
            )
            await self._safe_call(self.on_disconnect, name="on_disconnect")
            await self._backoff_wait()
            self._backoff = min(self._backoff * 2, _MAX_BACKOFF)

    async def _message_loop(self):
        assert self._ws is not None
        async for raw in self._ws:
            await self._dispatch(raw)

    async def _emit_frame(self, raw: Any) -> None:
        if not self._print_frames and self.on_frame is None and not logger.isEnabledFor(logging.DEBUG):
            return
        text = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
        if self._print_frames:
            logger.info("WS frame %s", text)
            print(text)
        elif logger.isEnabledFor(logging.DEBUG):
            logger.debug("WS frame %s", text[:200])
        if self.on_frame is not None:
            result = self.on_frame(text)
            if asyncio.iscoroutine(result):
                await result

    async def _dispatch(self, raw: Any):
        """Route one inbound frame to the matching callback.

        Never raises: malformed and unknown frames are logged and dropped.
        """
        await self._emit_frame(raw)
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            # e.g. the plaintext "You have permission to subscribe to all market data"
            logger.debug("Non-JSON frame skipped: %s",
                         raw[:200] if isinstance(raw, (str, bytes)) else raw)
            return
        if not isinstance(msg, dict):
            logger.debug("Non-object frame skipped: %s", msg)
            return

        code = msg.get("code")
        data = msg.get("data")

        if code == WsCode.PUSH_TRADE:
            await self._safe_call(
                self.on_trade, normalize_ws_trade(data) if self._parse else data,
                name="on_trade",
            )
        elif code == WsCode.PUSH_DEPTH:
            await self._safe_call(
                self.on_depth, normalize_ws_depth(data) if self._parse else data,
                name="on_depth",
            )
        elif code == WsCode.PUSH_KLINE:
            await self._safe_call(
                self.on_kline, normalize_ws_kline(data) if self._parse else data,
                name="on_kline",
            )
        elif code in (WsCode.SUB_TRADE_ACK, WsCode.SUB_DEPTH_ACK,
                      WsCode.SUB_KLINE_ACK, WsCode.UNSUB_ACK,
                      WsCode.HEARTBEAT, WsCode.HEART_APPLY):
            logger.debug("Control frame: code=%s trace=%s", code, msg.get("trace"))
        elif code == WS_CONNECT_OK:
            logger.debug("Welcome frame: %s", msg.get("msg"))
        elif isinstance(code, int) and WsErrorCode.is_error(code):
            trace = msg.get("traceId") or msg.get("trace")
            text = str(msg.get("msg") or "")
            if code in (501, 502):
                err: InfowayAPIError = InfowayRateLimitError.ws(code, text, trace)
            else:
                err = InfowayAPIError.of_ws(code, text, trace)
            logger.warning("Server rejected a frame: %s", err)
            await self._safe_call(self.on_error, err, name="on_error")
            if WsErrorCode.is_terminal(code):
                self._running = False
                ws = self._ws
                if ws is not None:
                    await ws.close()
        else:
            logger.debug("Unhandled code %s: %s", code, msg)

    async def _heartbeat_loop(self):
        """Send 10010 every 30s.

        The server sends **no reply** to heartbeats; their only purpose is to keep
        the connection marked active (60s of silence gets you disconnected).
        One task is created per socket and cancelled when the socket ends.
        """
        ws = self._ws
        assert ws is not None
        while self._running and self._ws is ws:
            await asyncio.sleep(self._heartbeat_interval)
            if not self._running or self._ws is not ws:
                return
            try:
                await ws.send('{"code":10010,"trace":"%s"}' % uuid.uuid4().hex[:12])
                logger.debug("Heartbeat sent")
            except Exception:
                return

    async def _backoff_wait(self) -> None:
        if self._backoff <= 0 or not self._running:
            return
        stop = self._stop
        if stop is None:
            await asyncio.sleep(self._backoff)
            return
        try:
            await asyncio.wait_for(stop.wait(), timeout=self._backoff)
        except asyncio.TimeoutError:
            return

    async def _resubscribe(self):
        assert self._ws is not None
        for sub_type, codes, kline_type in self._subscriptions:
            if sub_type == "trade":
                await self._ws.send(self._build_codes_message(
                    WsCode.SUB_TRADE, codes, include_ty=codes in self._include_ty
                ))
            elif sub_type == "depth":
                await self._ws.send(self._build_codes_message(WsCode.SUB_DEPTH, codes))
            elif sub_type == "kline":
                await self._ws.send(self._build_kline_message(WsCode.SUB_KLINE, codes, kline_type))
            logger.info("Re-subscribed %s: %s", sub_type, codes)

    # ------------------------------------------------------------------
    # subscriptions
    # ------------------------------------------------------------------

    async def subscribe_trade(self, codes: str | Iterable[str], include_ty: bool = False):
        """Subscribe to trades. ``codes`` may be a comma string or an iterable.

        ``include_ty=True`` asks the equity channel for trade-type ``ty``.
        """
        joined = join_codes(codes)
        self._subscriptions.add(("trade", joined, 0))
        if include_ty:
            self._include_ty.add(joined)
        await self._send_open(
            self._build_codes_message(WsCode.SUB_TRADE, joined, include_ty=include_ty)
        )

    async def subscribe_depth(self, codes: str | Iterable[str]):
        joined = join_codes(codes)
        self._subscriptions.add(("depth", joined, 0))
        await self._send_open(self._build_codes_message(WsCode.SUB_DEPTH, joined))

    async def subscribe_kline(
        self, codes: str | Iterable[str], kline_type: KlineType | int = KlineType.MIN_1
    ):
        joined = join_codes(codes)
        t = int(kline_type)
        self._subscriptions.add(("kline", joined, t))
        await self._send_open(self._build_kline_message(WsCode.SUB_KLINE, joined, t))

    async def unsubscribe_trade(self, codes: str | Iterable[str]):
        joined = join_codes(codes)
        self._subscriptions.discard(("trade", joined, 0))
        self._include_ty.discard(joined)
        await self._send_open(self._build_codes_message(WsCode.UNSUB_TRADE, joined))

    async def unsubscribe_depth(self, codes: str | Iterable[str]):
        joined = join_codes(codes)
        self._subscriptions.discard(("depth", joined, 0))
        await self._send_open(self._build_codes_message(WsCode.UNSUB_DEPTH, joined))

    async def unsubscribe_kline(
        self, codes: str | Iterable[str], kline_type: KlineType | int = KlineType.MIN_1
    ):
        """Unsubscribe a single K-line interval (``klineTypes`` is sent along)."""
        joined = join_codes(codes)
        t = int(kline_type)
        self._subscriptions.discard(("kline", joined, t))
        await self._send_open(self._build_kline_unsub_message(WsCode.UNSUB_KLINE, joined, t))

    async def _send_open(self, payload: str) -> None:
        ws = self._ws
        if ws is None:
            return
        with suppress(Exception):
            await ws.send(payload)

    async def close(self):
        self._running = False
        if self._stop is not None:
            self._stop.set()
        hb = self._heartbeat_task
        if hb is not None:
            hb.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None

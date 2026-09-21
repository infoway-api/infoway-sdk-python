"""Real-time news WebSocket channel.

The news feed is **not** the market-data connection: it lives on its own path
(``wss://data.infoway.io/news?apikey=...``, no ``business`` parameter) and needs
a separate entitlement on the API key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import suppress
from typing import Any, Awaitable, Callable

import websockets
from websockets.asyncio.client import ClientConnection

from infoway._normalize import normalize_news
from infoway._types import NEWS_LANGUAGES, NewsLang, WsCode, WsErrorCode, wire

# Re-export for callers that imported the tuple from this module.
__all__ = ["InfowayNewsWebSocket", "NEWS_LANGUAGES"]
from infoway.exceptions import InfowayAPIError, InfowayAuthError, InfowayRateLimitError
from infoway.ws.client import WS_CONNECT_OK, handshake_status

logger = logging.getLogger("infoway.ws.news")

_BASE_NEWS_URL = "wss://data.infoway.io/news"
_HEARTBEAT_INTERVAL = 30
_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 30.0

_NO_PERMISSION_MESSAGE = (
    "News channel handshake rejected with HTTP 401: this API key has no news "
    "permission (or is invalid). The /news route is separately authorised — "
    "contact Infoway to enable it. Not reconnecting."
)


class InfowayNewsWebSocket:
    """Async client for the real-time news feed.

    Usage::

        news = InfowayNewsWebSocket(api_key="YOUR_API_KEY")
        news.on_news = my_handler          # receives msg["data"]
        await news.subscribe("en")
        await news.connect()

    Protocol notes (docs + production probe, 2026-08-15):

    * subscribe ``10020`` → ack ``10021`` → pushes ``10022``.
    * There is no per-item unsubscribe: subscribing again **replaces** the
      previous language selection.
    * Heartbeat ``10010`` every 30s; the server sends no reply to it.
    * **One connection per API key** — a second one is rejected.
    * Push fields: ``dk`` (dedupe key), ``country``, ``lang``, ``route``,
      ``title``, ``published`` (Unix **seconds**), ``urgency`` (lower = more
      urgent), ``provider``, ``symbols[]``, ``link``, ``content``, ``sd``.
    * Without the news entitlement the gateway rejects the **HTTP handshake**
      with 401; this client raises :class:`~infoway.exceptions.InfowayAuthError`
      and stops instead of reconnecting forever.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _BASE_NEWS_URL,
        max_reconnect_attempts: int | None = None,
        parse: bool = False,
        print_frames: bool = False,
        lang: NewsLang | str = "en",
    ):
        key = api_key or os.getenv("INFOWAY_API_KEY", "")
        if not key:
            raise ValueError("apiKey is required (set INFOWAY_API_KEY or pass api_key)")
        self._url = f"{base_url}?apikey={key}"
        self._max_reconnect = max_reconnect_attempts
        self._parse = parse
        self._print_frames = print_frames
        self._ws: ClientConnection | None = None
        self._lang: str | None = wire(lang)
        self._running = False
        self._initial_backoff = _INITIAL_BACKOFF
        self._backoff = _INITIAL_BACKOFF
        self._heartbeat_interval = _HEARTBEAT_INTERVAL
        self._ever_connected = False
        self._stop: asyncio.Event | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

        self.on_news: Callable[[dict], Awaitable[None]] | None = None
        self.on_news_parsed: Callable[[dict], Awaitable[None]] | None = None
        self.on_frame: Callable[[str], Any] | None = None
        self.on_error: Callable[[Exception], Awaitable[None]] | None = None
        self.on_reconnect: Callable[[], Awaitable[None]] | None = None
        self.on_disconnect: Callable[[], Awaitable[None]] | None = None

    # ------------------------------------------------------------------

    def _build_subscribe_message(self, lang: NewsLang | str) -> str:
        lang = wire(lang) or "en"
        if lang not in NEWS_LANGUAGES:
            raise ValueError(
                f"unsupported news language {lang!r}; expected one of {', '.join(NEWS_LANGUAGES)}"
            )
        return json.dumps({
            "code": int(WsCode.SUB_NEWS),
            "trace": uuid.uuid4().hex,
            "data": {"lang": lang},
        })

    def _build_heartbeat_message(self) -> str:
        return json.dumps({"code": int(WsCode.HEARTBEAT), "trace": uuid.uuid4().hex})

    async def _safe_call(self, cb, *args, name: str = "callback"):
        if cb is None:
            return
        try:
            await cb(*args)
        except Exception:
            logger.exception("User %s raised — connection preserved", name)

    # ------------------------------------------------------------------

    async def subscribe(self, lang: NewsLang | str = "en"):
        """Subscribe to news in ``lang``. Calling it again replaces the selection."""
        message = self._build_subscribe_message(lang)
        self._lang = wire(lang)
        if self._ws:
            await self._ws.send(message)

    async def unsubscribe(self):
        """Cancel the news subscription (code 11020)."""
        self._lang = None
        if self._ws:
            await self._ws.send(json.dumps({
                "code": int(WsCode.UNSUB_NEWS),
                "trace": uuid.uuid4().hex,
            }))

    async def connect(self):
        """Connect and run the message loop. Blocks until closed.

        Raises:
            InfowayAuthError: when the handshake is rejected with HTTP 401,
                i.e. the key has no news permission. No reconnect is attempted.
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
                    logger.info("News WebSocket connected")

                    reconnected = self._ever_connected
                    self._ever_connected = True
                    if self._lang:
                        await ws.send(self._build_subscribe_message(self._lang))
                    if reconnected:
                        await self._safe_call(self.on_reconnect, name="on_reconnect")

                    hb = asyncio.create_task(self._heartbeat_loop(), name="infoway-news-heartbeat")
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
                    raise InfowayAuthError(_NO_PERMISSION_MESSAGE) from e
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
            logger.warning("News connection lost (%s), retrying in %.1fs", drop_reason, self._backoff)
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
            logger.info("News WS frame %s", text)
            print(text)
        elif logger.isEnabledFor(logging.DEBUG):
            logger.debug("News WS frame %s", text[:200])
        if self.on_frame is not None:
            result = self.on_frame(text)
            if asyncio.iscoroutine(result):
                await result

    async def _dispatch(self, raw: Any):
        await self._emit_frame(raw)
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.debug("Non-JSON frame skipped: %s",
                         raw[:200] if isinstance(raw, (str, bytes)) else raw)
            return
        if not isinstance(msg, dict):
            logger.debug("Non-object frame skipped: %s", msg)
            return

        code = msg.get("code")
        data = msg.get("data")

        if code == WsCode.PUSH_NEWS:
            parsed = normalize_news(data) if data is not None else data
            await self._safe_call(
                self.on_news, parsed if self._parse else data, name="on_news",
            )
            await self._safe_call(self.on_news_parsed, parsed, name="on_news_parsed")
        elif code in (WsCode.SUB_NEWS_ACK, WsCode.UNSUB_ACK,
                      WsCode.HEARTBEAT, WsCode.HEART_APPLY):
            logger.debug("News control frame: %s", code)
        elif code == WS_CONNECT_OK:
            logger.debug("Welcome frame: %s", msg.get("msg"))
        elif isinstance(code, int) and WsErrorCode.is_error(code):
            trace = msg.get("traceId") or msg.get("trace")
            text = str(msg.get("msg") or "")
            if code in (501, 502):
                err: InfowayAPIError = InfowayRateLimitError.ws(code, text, trace)
            else:
                err = InfowayAPIError.of_ws(code, text, trace)
            logger.warning("News channel error frame: %s", err)
            await self._safe_call(self.on_error, err, name="on_error")
        else:
            logger.debug("Unhandled news code %s: %s", code, msg)

    async def _heartbeat_loop(self):
        ws = self._ws
        assert ws is not None
        while self._running and self._ws is ws:
            await asyncio.sleep(self._heartbeat_interval)
            if not self._running or self._ws is not ws:
                return
            try:
                await ws.send(self._build_heartbeat_message())
                logger.debug("News heartbeat sent")
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

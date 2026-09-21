"""Infoway SDK exception types."""

from __future__ import annotations

from infoway._types import RestErrorCode, WsErrorCode


class InfowayTimeoutError(Exception):
    """Raised when a request times out."""


class InfowayIoError(Exception):
    """Raised when retries are exhausted on a network / I/O failure."""

    def __init__(self, message: str, cause: BaseException | None = None):
        super().__init__(message)
        self.__cause__ = cause


class InfowayAPIError(Exception):
    """Raised when the API returns a non-success response.

    ``ret`` is the wire code (REST ``ret``/``code``, WS ``code``, or HTTP status).
    ``error_name`` is the matching :class:`~infoway.RestErrorCode` or
    :class:`~infoway.WsErrorCode` constant when the SDK knows it. 508–514 share
    numbers across the two channels but not meanings.
    """

    def __init__(
        self,
        ret: int,
        msg: str,
        trace_id: str | None = None,
        error_name: str | None = None,
    ):
        self.ret = ret
        self.msg = msg
        self.trace_id = trace_id
        self.error_name = error_name
        prefix = f"[{ret} {error_name}]" if error_name else f"[{ret}]"
        text = f"{prefix} {msg}"
        if trace_id:
            text += f" (trace: {trace_id})"
        super().__init__(text)

    @property
    def errorName(self) -> str | None:
        """CamelCase alias of :attr:`error_name` (matches the Java getter)."""
        return self.error_name

    @classmethod
    def of_rest(cls, ret: int, msg: str, trace_id: str | None = None) -> InfowayAPIError:
        known = RestErrorCode.from_code(ret)
        name = known.name if known is not None else None
        display = msg or (known.name.replace("_", " ").title() if known else "API error")
        return cls(ret=ret, msg=display, trace_id=trace_id, error_name=name)

    @classmethod
    def of_ws(cls, ret: int, msg: str, trace_id: str | None = None) -> InfowayAPIError:
        known = WsErrorCode.from_code(ret)
        name = known.name if known is not None else None
        display = msg or (known.name.replace("_", " ").title() if known else "API error")
        return cls(ret=ret, msg=display, trace_id=trace_id, error_name=name)

    @classmethod
    def of_http_status(cls, status: int, msg: str, trace_id: str | None = None) -> InfowayAPIError:
        """Gateway / transport status — do not look up :class:`RestErrorCode`."""
        return cls(ret=status, msg=msg or "HTTP error", trace_id=trace_id, error_name=None)


class InfowayAuthError(InfowayAPIError):
    """Raised on 401 Unauthorized (bad/expired/unauthorized API key)."""

    def __init__(self, msg: str = "Unauthorized", trace_id: str | None = None):
        super().__init__(ret=401, msg=msg, trace_id=trace_id)


class InfowayRateLimitError(InfowayAPIError):
    """Raised when the gateway rate-limits the request.

    The server may serve rate limiting with **HTTP 200** and a body of
    ``{"detail": "Rate limit exceeded"}``, so the status code alone is not
    enough to detect it. REST ``ret`` 501/502 and WS ``code`` 501/502 also
    map here.
    """

    def __init__(
        self,
        msg: str = "Rate limit exceeded",
        ret: int = 429,
        trace_id: str | None = None,
        error_name: str | None = None,
    ):
        super().__init__(ret=ret, msg=msg, trace_id=trace_id, error_name=error_name)

    @classmethod
    def rest(cls, ret: int, msg: str, trace_id: str | None = None) -> InfowayRateLimitError:
        known = RestErrorCode.from_code(ret)
        return cls(
            msg=msg or "Rate limit exceeded",
            ret=ret,
            trace_id=trace_id,
            error_name=known.name if known is not None else None,
        )

    @classmethod
    def ws(cls, ret: int, msg: str, trace_id: str | None = None) -> InfowayRateLimitError:
        known = WsErrorCode.from_code(ret)
        return cls(
            msg=msg or "Rate limit exceeded",
            ret=ret,
            trace_id=trace_id,
            error_name=known.name if known is not None else None,
        )

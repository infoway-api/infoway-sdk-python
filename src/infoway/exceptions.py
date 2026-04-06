"""Infoway SDK exception types."""


class InfowayTimeoutError(Exception):
    """Raised when a request times out."""


class InfowayAPIError(Exception):
    """Raised when the API returns a non-success response."""

    def __init__(self, ret: int, msg: str, trace_id: str | None = None):
        self.ret = ret
        self.msg = msg
        self.trace_id = trace_id
        super().__init__(f"[{ret}] {msg}" + (f" (trace: {trace_id})" if trace_id else ""))


class InfowayAuthError(InfowayAPIError):
    """Raised on 401 Unauthorized."""

    def __init__(self, msg: str = "Unauthorized"):
        super().__init__(ret=401, msg=msg)

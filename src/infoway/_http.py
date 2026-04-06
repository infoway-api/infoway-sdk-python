"""Low-level HTTP client with retry and error handling."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from infoway.exceptions import InfowayAPIError, InfowayAuthError, InfowayTimeoutError

logger = logging.getLogger("infoway")

_DEFAULT_BASE_URL = "https://data.infoway.io"
_DEFAULT_TIMEOUT = 15.0
_DEFAULT_RETRIES = 3


class HttpClient:
    """HTTP client wrapping httpx with auth, retry, and Infoway error handling."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_RETRIES,
    ):
        self._api_key = api_key or os.getenv("INFOWAY_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"apiKey": self._api_key},
            timeout=self._timeout,
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=json)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = self._client.request(method, path, **kwargs)
                return self._handle_response(resp)
            except (InfowayAPIError, InfowayAuthError):
                raise
            except httpx.TimeoutException as e:
                last_exc = InfowayTimeoutError(str(e))
            except httpx.HTTPError as e:
                last_exc = e
                logger.debug("Request failed (attempt %d/%d): %s", attempt + 1, self._max_retries, e)
            if attempt < self._max_retries - 1:
                time.sleep(min(2 ** attempt, 8))
        raise last_exc

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            raise InfowayAuthError()
        data = resp.json()
        ret = data.get("ret") or data.get("code", 200)
        msg = data.get("msg", "")
        trace_id = data.get("traceId")
        if ret == 401:
            raise InfowayAuthError(msg)
        if ret != 200:
            raise InfowayAPIError(ret=ret, msg=msg, trace_id=trace_id)
        return data.get("data")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args: Any):
        self.close()

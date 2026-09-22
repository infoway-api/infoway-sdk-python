"""Low-level HTTP client with retry and error handling."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from infoway._types import RestErrorCode
from infoway.exceptions import (
    InfowayAPIError,
    InfowayAuthError,
    InfowayIoError,
    InfowayRateLimitError,
    InfowayTimeoutError,
)

logger = logging.getLogger("infoway")


def resolve_api_key(api_key: str | None) -> str:
    """``None`` reads ``INFOWAY_API_KEY``. A blank string is an explicit empty key."""
    if api_key is not None:
        return api_key.strip()
    return os.getenv("INFOWAY_API_KEY", "").strip()

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
        self._api_key = resolve_api_key(api_key)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._closed = False
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"apikey": self._api_key},
            timeout=self._timeout,
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=json)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._closed:
            raise InfowayIoError("InfowayClient is closed")
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = self._client.request(method, path, **kwargs)
                return self._handle_response(resp)
            except InfowayRateLimitError as e:
                last_exc = e
                logger.debug("Rate limited (attempt %d/%d)", attempt + 1, self._max_retries)
            except (InfowayAPIError, InfowayAuthError):
                raise
            except httpx.TimeoutException as e:
                last_exc = InfowayTimeoutError(str(e))
            except httpx.HTTPError as e:
                last_exc = e
                logger.debug("Request failed (attempt %d/%d): %s", attempt + 1, self._max_retries, e)
            if attempt < self._max_retries - 1:
                time.sleep(min(2 ** attempt, 8))
        if isinstance(last_exc, (InfowayRateLimitError, InfowayTimeoutError)):
            raise last_exc
        raise InfowayIoError(
            f"Request failed after {self._max_retries} retries", last_exc
        )

    @staticmethod
    def _json_or_none(resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except Exception:
            return None

    def _handle_response(self, resp: httpx.Response) -> Any:
        """Map a raw HTTP response onto SDK return values / exceptions.

        Order matches Java ``HttpClient`` and
        ``docs/specs/2026-08-15-sdk-contract-fix-design.md`` §1.
        """
        body = self._json_or_none(resp)
        obj = body if isinstance(body, dict) else {}
        msg = obj.get("msg") or obj.get("message") or ""
        trace_id = obj.get("traceId") or obj.get("trace")

        if resp.status_code == 401:
            raise InfowayAuthError(msg or "Unauthorized", trace_id=trace_id)

        if resp.status_code == 429:
            detail = obj.get("detail") or msg or "Rate limit exceeded"
            raise InfowayRateLimitError.rest(429, str(detail), trace_id)

        if "detail" in obj and not ({"ret", "code", "data"} & obj.keys()):
            detail = str(obj["detail"])
            status = obj.get("status") or resp.status_code
            if "rate limit" in detail.lower():
                raise InfowayRateLimitError(detail, ret=int(status), trace_id=trace_id)
            raise InfowayAPIError.of_http_status(int(status), detail, trace_id)

        if "title" in obj and "status" in obj:
            status = obj.get("status") or resp.status_code
            raise InfowayAPIError.of_http_status(
                int(status),
                str(obj.get("detail") or obj.get("title")),
                trace_id,
            )

        ret = obj["ret"] if "ret" in obj else obj.get("code")
        if ret is not None and ret != 200:
            raise self._rest_failure(int(ret), msg or "API error", trace_id)

        if resp.status_code >= 400:
            raise InfowayAPIError.of_http_status(
                resp.status_code,
                msg or (resp.text or resp.reason_phrase or "HTTP error").strip()[:500],
                trace_id,
            )

        if isinstance(body, dict):
            return body["data"] if "data" in body else body
        return body

    @staticmethod
    def _rest_failure(ret: int, msg: str, trace_id: str | None) -> InfowayAPIError:
        ret = RestErrorCode.classify(ret, msg)
        if ret == 401:
            return InfowayAuthError(msg, trace_id=trace_id)
        if ret in (429, RestErrorCode.REQUEST_EXCEED_LIMIT, RestErrorCode.REQUEST_FOR_DAY_LIMIT):
            return InfowayRateLimitError.rest(ret, msg, trace_id)
        return InfowayAPIError.of_rest(ret, msg, trace_id)

    def close(self):
        self._closed = True
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args: Any):
        self.close()

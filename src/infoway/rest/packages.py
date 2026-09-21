"""Current API-key package / quota."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from infoway._http import HttpClient


class PackageClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_info(self) -> Any:
        """Quota for the current key: ``packageName``, ``expireTime``, ``apiNumPerSec``, …"""
        return self._http.get("/package/info")

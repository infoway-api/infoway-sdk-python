"""Shared type definitions and enums."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any


class KlineType(IntEnum):
    MIN_1 = 1
    MIN_5 = 2
    MIN_15 = 3
    MIN_30 = 4
    HOUR_1 = 5
    HOUR_2 = 6
    HOUR_4 = 7
    DAY = 8
    WEEK = 9
    MONTH = 10
    QUARTER = 11
    YEAR = 12


class SymbolType(str, Enum):
    """Product ``type`` for ``basic`` / ``financial`` / ``get_stock_detail``."""

    STOCK_US = "STOCK_US"
    STOCK_CN = "STOCK_CN"
    STOCK_HK = "STOCK_HK"
    STOCK_JP = "STOCK_JP"
    STOCK_KS = "STOCK_KS"
    STOCK_IN = "STOCK_IN"
    STOCK_TW = "STOCK_TW"
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    FUTURES = "FUTURES"
    ENERGY = "ENERGY"
    METAL = "METAL"
    INDICES = "INDICES"


class Market(str, Enum):
    """Equity market codes for overview, plates and calendar."""

    HK = "HK"
    US = "US"
    CN = "CN"
    JP = "JP"
    KS = "KS"
    TW = "TW"
    IN = "IN"

    @staticmethod
    def join(*markets: Market | str | None) -> str | None:
        parts = [wire(m) for m in markets if m]
        return ",".join(parts) if parts else None


class Lang(str, Enum):
    """REST ``lang`` for name-like fields (``en`` / ``zh-CN``)."""

    EN = "en"
    ZH_CN = "zh-CN"


class NewsLang(str, Enum):
    """News WebSocket ``data.lang``."""

    EN = "en"
    ZH_HANS = "zh-Hans"
    ZH_HANT = "zh-Hant"
    JA = "ja"
    KO = "ko"
    DE = "de"
    FR = "fr"
    ES = "es"
    PT = "pt"
    RU = "ru"
    TR = "tr"


class PeriodType(str, Enum):
    """Financial ``period_type``."""

    FQ = "fq"
    FY = "fy"
    FH = "fh"


class ScheduleType(str, Enum):
    """Filter for ``/common/basic/markets/trading_schedule``.

    Not the same as :class:`SymbolType` — equity values such as ``STOCK_US``
    are rejected by the server.
    """

    ENERGY = "ENERGY"
    FOREX = "FOREX"
    FUTURES = "FUTURES"
    METAL = "METAL"
    INDICES = "INDICES"

    @classmethod
    def from_value(cls, type: str | None) -> ScheduleType | None:
        if not type or not str(type).strip():
            return None
        key = str(type).strip().upper()
        for item in cls:
            if item.value == key:
                return item
        return None

    @classmethod
    def from_symbol_type(cls, type: SymbolType | str | None) -> ScheduleType | None:
        return cls.from_value(wire(type) if type is not None else None)


class RankSort(str, Enum):
    CHG = "chg"
    LAST_DONE = "last_done"
    CHANGE = "change"
    TURNOVER = "turnover"
    VOLUME = "volume"
    AMPLITUDE = "amplitude"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class Business(str):
    """WebSocket ``business`` channels.

    A channel only carries its own instruments. Subscribing to e.g. ``AAPL.US``
    on ``crypto`` is acked with ``10001 ok`` and then stays silent forever.
    """

    STOCK = "stock"
    JAPAN = "japan"
    INDIA = "india"
    KOREA = "korea"
    TAIWAN = "taiwan"
    CRYPTO = "crypto"
    COMMON = "common"


# Alias matching the Java ``WsBusiness`` name.
WsBusiness = Business


class WsCode(IntEnum):
    """WebSocket subscribe / push protocol codes (not 5xx error frames)."""

    SUB_TRADE = 10000
    SUB_DEPTH = 10003
    SUB_KLINE = 10006
    SUB_NEWS = 10020
    HEARTBEAT = 10010
    HEART_APPLY = 10011
    UNSUB_TRADE = 11000
    UNSUB_DEPTH = 11001
    UNSUB_KLINE = 11002
    UNSUB_NEWS = 11020
    SUB_TRADE_ACK = 10001
    SUB_DEPTH_ACK = 10004
    SUB_KLINE_ACK = 10007
    SUB_NEWS_ACK = 10021
    PUSH_TRADE = 10002
    PUSH_DEPTH = 10005
    PUSH_KLINE = 10008
    PUSH_NEWS = 10022
    UNSUB_ACK = 11010

    @classmethod
    def from_code(cls, code: int) -> WsCode | None:
        try:
            return cls(code)
        except ValueError:
            return None


class RestErrorCode(IntEnum):
    """REST ``ret`` from the quote service / commonApi.

    508–514 collide with :class:`WsErrorCode` but mean different things.
    """

    SUCCESS = 200
    BAD_REQUEST = 400
    SERVER_ERROR = 500
    REQUEST_EXCEED_LIMIT = 501
    REQUEST_FOR_DAY_LIMIT = 502
    KLINE_EXCEEDS_LIMIT = 503
    ORDER_BOOK_DEPTH_EXCEEDS_LIMIT = 504
    PRODUCTS_EXCEEDS_LIMIT = 505
    PARAM_ERROR = 506
    PARAM_LOST = 507
    PRODUCT_NOT_EXISTS = 508
    TOKEN_PERMISSION_EXPIRED = 509
    WEBSOCKET_EXCEEDS_LIMIT = 510
    WEBSOCKET_HEARTBEAT_TIMEOUT = 511
    WEBSOCKET_DISCONNECTED = 512
    TIME_LIMIT_ERROR = 513
    NO_PERMISSION = 514

    @classmethod
    def from_code(cls, code: int) -> RestErrorCode | None:
        try:
            return cls(code)
        except ValueError:
            return None


class WsErrorCode(IntEnum):
    """WebSocket 5xx error-frame codes. Do not use these to decode REST ``ret``."""

    SERVER_ERROR = 500
    REQUEST_FREQUENCY_MIN_EXCEED = 501
    REQUEST_FREQUENCY_DAY_EXCEED = 502
    KLINE_QUANTITY_EXCEED = 503
    ORDER_BOOK_DEPTH_EXCEED = 504
    PRODUCTS_QUANTITY_EXCEED = 505
    PARAM_ERROR = 506
    PARAM_LOST = 507
    APIKEY_EXPIRED = 508
    APIKEY_INVALID = 509
    APIKEY_EMPTY = 510
    APIKEY_BLACKLIST = 511
    WS_CONN_EXCEED = 512
    WS_HEART_TIMEOUT = 513
    WS_URL_WRONG = 514
    PARAM_NOT_JSON = 515
    ALL_PRODUCTS_QUANTITY_EXCEED = 516
    WS_HANDSHAKE_APIKEY_MISSING = 517
    WS_HANDSHAKE_APIKEY_NOT_EXIST = 518
    WS_HANDSHAKE_NO_PERMISSION = 519
    PRODUCT_CODE_OR_ALREADY_CONNECTED = 520
    WS_HANDSHAKE_MAX_CONNECTIONS = 521

    @classmethod
    def from_code(cls, code: int) -> WsErrorCode | None:
        try:
            return cls(code)
        except ValueError:
            return None

    @staticmethod
    def is_error(code: int) -> bool:
        return 500 <= code < 10000 and WsCode.from_code(code) is None


#: Legal values for the ``type`` parameter of the symbol endpoints.
SYMBOL_TYPES = tuple(item.value for item in SymbolType)

#: Languages the news channel accepts for ``data.lang``.
NEWS_LANGUAGES = tuple(item.value for item in NewsLang)


def wire(value: Any | None) -> str | None:
    """Turn an enum or raw value into the wire string the server expects."""
    if value is None:
        return None
    if isinstance(value, Enum):
        v = value.value
        return str(v)
    return str(value)


def query(**kwargs: Any) -> dict[str, Any] | None:
    """Drop ``None`` query values."""
    out = {k: v for k, v in kwargs.items() if v is not None}
    return out or None

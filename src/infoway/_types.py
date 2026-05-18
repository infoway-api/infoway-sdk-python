"""Shared type definitions and enums."""

from enum import IntEnum


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


class Business(str):
    STOCK = "stock"
    JAPAN = "japan"
    INDIA = "india"
    CRYPTO = "crypto"
    COMMON = "common"


class WsCode(IntEnum):
    """WebSocket message codes.

    Outbound (client → server):
        SUB_TRADE / SUB_DEPTH / SUB_KLINE / HEARTBEAT
        UNSUB_TRADE / UNSUB_DEPTH / UNSUB_KLINE

    Inbound (server → client):
        SUB_*_ACK — one-shot ``{"msg":"ok"}`` after a successful subscribe
        PUSH_TRADE (10002) / PUSH_DEPTH (10005) / PUSH_KLINE (10008) — real-time data pushes
        UNSUB_ACK (11010) — unsubscribe confirmation
    """

    # Outbound — subscribe
    SUB_TRADE = 10000
    SUB_DEPTH = 10003
    SUB_KLINE = 10006

    # Outbound — heartbeat
    HEARTBEAT = 10010

    # Outbound — unsubscribe
    UNSUB_TRADE = 11000
    UNSUB_DEPTH = 11001
    UNSUB_KLINE = 11002

    # Inbound — subscription acknowledgements
    SUB_TRADE_ACK = 10001
    SUB_DEPTH_ACK = 10004
    SUB_KLINE_ACK = 10007

    # Inbound — real-time data pushes
    PUSH_TRADE = 10002
    PUSH_DEPTH = 10005
    PUSH_KLINE = 10008

    # Inbound — unsubscribe ack
    UNSUB_ACK = 11010

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
    SUB_TRADE = 10000
    PUSH_TRADE = 10001
    UNSUB_TRADE = 10002
    SUB_DEPTH = 10003
    PUSH_DEPTH = 10004
    UNSUB_DEPTH = 10005
    SUB_KLINE = 10006
    PUSH_KLINE = 10007
    UNSUB_KLINE = 10008
    HEARTBEAT = 10010

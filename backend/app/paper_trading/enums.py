from enum import Enum

class TradeStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    TP_HIT = "TP_HIT"
    SL_HIT = "SL_HIT"
    CANCELLED = "CANCELLED"
    INVALID = "INVALID"
    MANUAL_CLOSED = "MANUAL_CLOSED"

class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    MANUAL = "MANUAL"
    CANCELLED = "CANCELLED"
    INVALID = "INVALID"

class PositionSizingMode(str, Enum):
    FIXED_LOT = "FIXED_LOT"
    FIXED_RISK_AMOUNT = "FIXED_RISK_AMOUNT"
    PERCENTAGE_RISK = "PERCENTAGE_RISK"

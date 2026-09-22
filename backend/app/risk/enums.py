from enum import Enum

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class TPSource(str, Enum):
    PROVIDER = "PROVIDER"
    CALCULATED = "CALCULATED"
    NONE = "NONE"

class SLSource(str, Enum):
    PROVIDER = "PROVIDER"
    STRATEGY = "STRATEGY"
    NONE = "NONE"

class RiskValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    PARTIAL = "PARTIAL"
    LOW_RR = "LOW_RR"

class RejectionReason(str, Enum):
    SL_ABOVE_BUY_ENTRY = "Stop loss must be strictly below entry price for BUY"
    SL_BELOW_SELL_ENTRY = "Stop loss must be strictly above entry price for SELL"
    ZERO_OR_NEGATIVE_RISK = "Calculated risk distance is zero or negative"
    TP_BELOW_BUY_ENTRY = "Take profit must be strictly above entry price for BUY"
    TP_ABOVE_SELL_ENTRY = "Take profit must be strictly below entry price for SELL"
    INVALID_PRICE = "One or more price values are non-positive or invalid"
    INVALID_SIDE = "Side must be either BUY or SELL"
    MISSING_STOP_LOSS = "Stop loss is missing and zero-assumption policy prevents fabrication"
    MISSING_ENTRY_PRICE = "Entry price is missing or invalid"

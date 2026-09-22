from enum import Enum

class ParsingState(str, Enum):
    """
    Explicit lifecycle states for signal parsing.
    - VALID: Complete signal with Symbol, Direction, Entry, and Stop Loss.
    - PARTIAL: Signal contains directional trade intent and entry, but lacks Stop Loss (or vice-versa).
    - INVALID: Contains trade keywords but malformed values, conflicting data, or invalid syntax.
    - UNKNOWN: Completely unrelated message or no trade parameters detected.
    """
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"

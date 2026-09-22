from typing import Optional, List
from dataclasses import dataclass
from app.services.signal_parser import ParsedSignalResult
from app.utils.instrument_specs import get_instrument_spec, normalize_symbol_name

@dataclass
class NormalizedSignal:
    symbol: str
    side: str                          # BUY, SELL
    order_type: str                    # MARKET, LIMIT, STOP
    entry_price: Optional[float]
    entry_price_upper: Optional[float]
    provider_sl: Optional[float]
    provider_tps: List[float]
    confidence: float
    raw_text: str
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None
    digits: int = 5
    pip_size: float = 0.0001
    point_size: float = 0.00001
    contract_size: float = 100000.0

class SignalNormalizer:
    """Standardizes parsed fields, rounds prices to asset precision, and sorts TP targets."""

    @classmethod
    def normalize(cls, parsed: ParsedSignalResult) -> NormalizedSignal:
        raw_sym = parsed.symbol or "UNKNOWN"
        canonical_sym = normalize_symbol_name(raw_sym) or raw_sym.upper()
        spec = get_instrument_spec(canonical_sym) or {
            "digits": 5,
            "pip_size": 0.0001,
            "point_size": 0.00001,
            "contract_size": 100000.0
        }
        digits = spec["digits"]

        norm_entry = round(parsed.entry_price, digits) if parsed.entry_price is not None else None
        norm_entry_upper = round(parsed.entry_price_upper, digits) if parsed.entry_price_upper is not None else None
        norm_zone_low = round(parsed.entry_zone_low, digits) if parsed.entry_zone_low is not None else norm_entry
        norm_zone_high = round(parsed.entry_zone_high, digits) if parsed.entry_zone_high is not None else norm_entry
        norm_sl = round(parsed.provider_sl, digits) if parsed.provider_sl is not None else None

        # Sort TPs monotonically based on side
        norm_tps = [round(tp, digits) for tp in parsed.provider_tps]
        if parsed.side == "BUY":
            norm_tps = sorted(norm_tps)
        elif parsed.side == "SELL":
            norm_tps = sorted(norm_tps, reverse=True)

        return NormalizedSignal(
            symbol=canonical_sym,
            side=parsed.side or "UNKNOWN",
            order_type=parsed.order_type or "MARKET",
            entry_price=norm_entry,
            entry_price_upper=norm_entry_upper,
            entry_zone_low=norm_zone_low,
            entry_zone_high=norm_zone_high,
            provider_sl=norm_sl,
            provider_tps=norm_tps,
            confidence=parsed.confidence,
            raw_text=parsed.raw_text,
            digits=digits,
            pip_size=spec["pip_size"],
            point_size=spec["point_size"],
            contract_size=spec["contract_size"]
        )


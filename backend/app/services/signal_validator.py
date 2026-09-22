from typing import Optional, List, Tuple
from dataclasses import dataclass
from app.services.signal_normalizer import NormalizedSignal
from app.config import settings

@dataclass
class ValidationResult:
    is_valid: bool
    status: str                         # VALID, INVALID, SKIPPED_NO_SL
    effective_sl: Optional[float]
    sl_source: Optional[str]            # PROVIDER, CONFIGURED_STRATEGY, NONE
    rejection_reasons: List[str]
    warning_notes: List[str]

class SignalValidator:
    """
    Strict validation engine for trading signals.
    Enforces directional price rules, zero-assumption SL requirements, and audit trail generation.
    """

    @classmethod
    def validate(cls, signal: NormalizedSignal) -> ValidationResult:
        reasons: List[str] = []
        warnings: List[str] = []

        # 1. Check Symbol
        if not signal.symbol or signal.symbol == "UNKNOWN":
            reasons.append("Unrecognized or missing trading symbol.")

        # 2. Check Side
        if signal.side not in ["BUY", "SELL"]:
            reasons.append(f"Invalid trading side: '{signal.side}'. Expected BUY or SELL.")

        # 3. Check Entry Price
        if signal.entry_price is None or signal.entry_price <= 0:
            reasons.append("Missing or invalid entry price.")

        # 4. SL Priority Resolution
        effective_sl: Optional[float] = None
        sl_source: Optional[str] = None

        if signal.provider_sl is not None and signal.provider_sl > 0:
            effective_sl = signal.provider_sl
            sl_source = "PROVIDER"
        elif settings.CONFIGURED_STRATEGY_SL_ENABLED and signal.entry_price is not None:
            # Strategy SL calculation
            if signal.side == "BUY":
                effective_sl = round(signal.entry_price - (settings.DEFAULT_SL_PIPS * signal.pip_size), signal.digits)
            else:
                effective_sl = round(signal.entry_price + (settings.DEFAULT_SL_PIPS * signal.pip_size), signal.digits)
            sl_source = "CONFIGURED_STRATEGY"
            warnings.append(f"No provider SL supplied. Applied configured strategy SL ({settings.DEFAULT_SL_PIPS} pips).")
        else:
            reasons.append("NO_VALID_STOP_LOSS: System strictly requires an SL and strategy-based SL is disabled.")
            sl_source = "NONE"

        # If already failed basic requirements, return early
        if reasons:
            status = "SKIPPED_NO_SL" if "NO_VALID_STOP_LOSS" in str(reasons) else "INVALID"
            return ValidationResult(
                is_valid=False,
                status=status,
                effective_sl=effective_sl,
                sl_source=sl_source,
                rejection_reasons=reasons,
                warning_notes=warnings
            )

        # 5. Directional Validation Checks
        entry = signal.entry_price
        sl = effective_sl

        if signal.side == "BUY":
            # BUY: entry > stop_loss
            if sl >= entry:
                reasons.append(f"Directional Error (BUY): Stop Loss ({sl}) must be lower than Entry Price ({entry}).")

            # Check provider TPs (must be > entry)
            for i, tp in enumerate(signal.provider_tps, 1):
                if tp <= entry:
                    reasons.append(f"Directional Error (BUY): Take Profit {i} ({tp}) must be higher than Entry Price ({entry}).")

        elif signal.side == "SELL":
            # SELL: entry < stop_loss
            if sl <= entry:
                reasons.append(f"Directional Error (SELL): Stop Loss ({sl}) must be higher than Entry Price ({entry}).")

            # Check provider TPs (must be < entry)
            for i, tp in enumerate(signal.provider_tps, 1):
                if tp >= entry:
                    reasons.append(f"Directional Error (SELL): Take Profit {i} ({tp}) must be lower than Entry Price ({entry}).")

        # 6. TP Warnings
        if not signal.provider_tps:
            warnings.append("No provider TP supplied. R-multiple targets (1R, 1.5R, 2R, 3R) will be calculated automatically.")

        is_valid = len(reasons) == 0
        status = "VALID" if is_valid else "INVALID"

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            effective_sl=effective_sl,
            sl_source=sl_source,
            rejection_reasons=reasons,
            warning_notes=warnings
        )


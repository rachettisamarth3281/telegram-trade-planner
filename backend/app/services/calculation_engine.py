from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from app.services.signal_normalizer import NormalizedSignal
from app.config import settings

@dataclass
class CalculatedMetricsResult:
    effective_sl: float
    sl_source: str
    risk_price_diff: float
    risk_pips: float
    r1_target: float
    r1_5_target: float
    r2_target: float
    r3_target: float
    r_targets: Dict[str, float]
    provider_tp_rrrs: Dict[str, float]
    suggested_lot_size: float
    risk_amount_usd: float

class CalculationEngine:
    """
    Precision math engine for Stop Loss, Take Profit, R-multiples, RRR, and position sizing.
    Uses high-precision decimal math to eliminate floating point drift.
    """

    @classmethod
    def calculate(
        cls,
        signal: NormalizedSignal,
        effective_sl: float,
        sl_source: str = "PROVIDER",
        account_balance: float = 10000.0,
        risk_percent: float = 1.0,
        custom_r_multiples: Optional[List[float]] = None
    ) -> CalculatedMetricsResult:
        digits = signal.digits
        entry_d = Decimal(str(signal.entry_price))
        sl_d = Decimal(str(effective_sl))
        pip_size_d = Decimal(str(signal.pip_size))
        contract_size_d = Decimal(str(signal.contract_size))

        # 1. Calculate Risk Price Diff
        if signal.side == "BUY":
            risk_d = entry_d - sl_d
        else:  # SELL
            risk_d = sl_d - entry_d

        if risk_d <= 0:
            raise ValueError(f"Invalid risk distance: {risk_d} for side {signal.side}")

        # Round format string e.g. '0.01' for 2 digits, '0.00001' for 5 digits
        quant_format = Decimal('10') ** -digits

        # Calculate R-Multiple Targets
        r_targets_to_calc = custom_r_multiples or settings.CALCULATED_R_MULTIPLES
        r_targets_map: Dict[str, float] = {}

        for r in r_targets_to_calc:
            r_dec = Decimal(str(r))
            if signal.side == "BUY":
                target_d = entry_d + (risk_d * r_dec)
            else:
                target_d = entry_d - (risk_d * r_dec)

            # Round using standard half-up
            rounded_target = target_d.quantize(quant_format, rounding=ROUND_HALF_UP)
            key = f"{r:g}R"
            r_targets_map[key] = float(rounded_target)

        # Standard R targets
        r1 = r_targets_map.get("1R", float((entry_d + risk_d if signal.side == "BUY" else entry_d - risk_d).quantize(quant_format, rounding=ROUND_HALF_UP)))
        r1_5 = r_targets_map.get("1.5R", float((entry_d + (risk_d * Decimal('1.5')) if signal.side == "BUY" else entry_d - (risk_d * Decimal('1.5'))).quantize(quant_format, rounding=ROUND_HALF_UP)))
        r2 = r_targets_map.get("2R", float((entry_d + (risk_d * Decimal('2.0')) if signal.side == "BUY" else entry_d - (risk_d * Decimal('2.0'))).quantize(quant_format, rounding=ROUND_HALF_UP)))
        r3 = r_targets_map.get("3R", float((entry_d + (risk_d * Decimal('3.0')) if signal.side == "BUY" else entry_d - (risk_d * Decimal('3.0'))).quantize(quant_format, rounding=ROUND_HALF_UP)))

        # 2. Calculate Provider TP RRRs
        provider_rrrs: Dict[str, float] = {}
        for i, tp in enumerate(signal.provider_tps, 1):
            tp_d = Decimal(str(tp))
            reward_d = (tp_d - entry_d) if signal.side == "BUY" else (entry_d - tp_d)
            if reward_d > 0 and risk_d > 0:
                rrr_val = (reward_d / risk_d).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                provider_rrrs[f"TP{i}"] = float(rrr_val)

        # 3. Calculate Risk in Pips
        risk_pips_d = (risk_d / pip_size_d).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # 4. Calculate Risk Amount ($) and Position Sizing (Lots)
        balance_d = Decimal(str(account_balance))
        risk_pct_d = Decimal(str(risk_percent)) / Decimal('100')
        risk_amount_usd_d = balance_d * risk_pct_d

        # Position size = Risk $ / (Risk distance * Contract Size)
        loss_per_unit = risk_d * contract_size_d
        if loss_per_unit > 0:
            lot_size_d = (risk_amount_usd_d / loss_per_unit).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            # Minimum lot size 0.01
            lot_size = max(float(lot_size_d), 0.01)
        else:
            lot_size = 0.01

        return CalculatedMetricsResult(
            effective_sl=float(sl_d.quantize(quant_format, rounding=ROUND_HALF_UP)),
            sl_source=sl_source,
            risk_price_diff=float(risk_d.quantize(quant_format, rounding=ROUND_HALF_UP)),
            risk_pips=float(risk_pips_d),
            r1_target=r1,
            r1_5_target=r1_5,
            r2_target=r2,
            r3_target=r3,
            r_targets=r_targets_map,
            provider_tp_rrrs=provider_rrrs,
            suggested_lot_size=lot_size,
            risk_amount_usd=float(risk_amount_usd_d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        )


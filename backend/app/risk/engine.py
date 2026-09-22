from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, List, Dict, Union, Any
from app.risk.enums import Side, TPSource, SLSource, RiskValidationStatus, RejectionReason
from app.risk.models import (
    RiskEngineConfig,
    RiskCalculationInput,
    RiskCalculationResult,
    ProviderTPMetrics,
)
from app.config import settings

class RiskEngine:
    """
    Deterministic SL/TP and Risk/Reward calculation engine.
    
    Guarantees:
    - Purely rule-based (NO random choices, NO AI trading decisions).
    - High-precision Decimal calculations.
    - Zero-assumption policy: Never fabricates missing Stop Losses.
    - Configurable R-multiples, minimum RR validation, and tick-size/decimal rounding.
    """

    @classmethod
    def calculate_from_values(
        cls,
        symbol: Optional[str] = None,
        side: Optional[Union[str, Side]] = None,
        entry_price: Optional[Union[Decimal, float, str, int]] = None,
        stop_loss: Optional[Union[Decimal, float, str, int]] = None,
        provider_take_profit: Optional[Union[Decimal, float, str, int]] = None,
        provider_take_profits: Optional[List[Union[Decimal, float, str, int]]] = None,
        strategy_stop_loss: Optional[Union[Decimal, float, str, int]] = None,
        config: Optional[RiskEngineConfig] = None,
    ) -> RiskCalculationResult:
        """Convenience method accepting raw arguments."""
        calc_input = RiskCalculationInput(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            provider_take_profit=provider_take_profit,
            provider_take_profits=provider_take_profits,
            strategy_stop_loss=strategy_stop_loss,
            config=config,
        )
        return cls.calculate(calc_input)

    @classmethod
    def calculate(cls, input_data: RiskCalculationInput) -> RiskCalculationResult:
        """
        Execute deterministic risk/reward and SL/TP calculation.
        """
        cfg = input_data.config or cls._get_default_config()
        rejection_reasons: List[str] = []
        warning_flags: List[str] = []

        # 1. Normalize Side
        normalized_side = cls._normalize_side(input_data.side)
        if not normalized_side:
            rejection_reasons.append(RejectionReason.INVALID_SIDE.value)
            return RiskCalculationResult(
                is_valid=False,
                status=RiskValidationStatus.INVALID,
                rejection_reasons=rejection_reasons,
                symbol=input_data.symbol,
                side=str(input_data.side) if input_data.side else None,
            )

        # 2. Parse and Validate Entry Price
        entry_d = cls._to_decimal(input_data.entry_price)
        if entry_d is None or entry_d <= Decimal("0"):
            rejection_reasons.append(RejectionReason.MISSING_ENTRY_PRICE.value)
            return RiskCalculationResult(
                is_valid=False,
                status=RiskValidationStatus.INVALID,
                rejection_reasons=rejection_reasons,
                symbol=input_data.symbol,
                side=normalized_side.value,
            )

        # 3. Resolve Stop Loss (SL Priority: PROVIDER -> STRATEGY -> NONE)
        provider_sl_d = cls._to_decimal(input_data.stop_loss)
        strategy_sl_d = cls._to_decimal(input_data.strategy_stop_loss)

        effective_sl: Optional[Decimal] = None
        sl_source: SLSource = SLSource.NONE

        if provider_sl_d is not None:
            if provider_sl_d <= Decimal("0"):
                rejection_reasons.append(RejectionReason.INVALID_PRICE.value)
            else:
                effective_sl = provider_sl_d
                sl_source = SLSource.PROVIDER
        elif cfg.allow_strategy_sl and strategy_sl_d is not None:
            if strategy_sl_d <= Decimal("0"):
                rejection_reasons.append(RejectionReason.INVALID_PRICE.value)
            else:
                effective_sl = strategy_sl_d
                sl_source = SLSource.STRATEGY

        # Zero assumption rule: if no valid SL could be resolved, do not fabricate one
        if effective_sl is None:
            rejection_reasons.append(RejectionReason.MISSING_STOP_LOSS.value)
            return RiskCalculationResult(
                is_valid=False,
                status=RiskValidationStatus.PARTIAL,
                rejection_reasons=rejection_reasons,
                symbol=input_data.symbol,
                side=normalized_side.value,
                entry_price=cls._apply_precision(entry_d, cfg),
                effective_sl=None,
                sl_source=SLSource.NONE,
            )

        # 4. Calculate Risk Distance and Validate Directional Geometry
        # BUY: risk_distance = entry - SL (SL must be < entry)
        # SELL: risk_distance = SL - entry (SL must be > entry)
        if normalized_side == Side.BUY:
            if effective_sl >= entry_d:
                rejection_reasons.append(RejectionReason.SL_ABOVE_BUY_ENTRY.value)
                rejection_reasons.append(RejectionReason.ZERO_OR_NEGATIVE_RISK.value)
            risk_distance = entry_d - effective_sl
        else:  # SELL
            if effective_sl <= entry_d:
                rejection_reasons.append(RejectionReason.SL_BELOW_SELL_ENTRY.value)
                rejection_reasons.append(RejectionReason.ZERO_OR_NEGATIVE_RISK.value)
            risk_distance = effective_sl - entry_d

        if risk_distance <= Decimal("0"):
            if RejectionReason.ZERO_OR_NEGATIVE_RISK.value not in rejection_reasons:
                rejection_reasons.append(RejectionReason.ZERO_OR_NEGATIVE_RISK.value)

            return RiskCalculationResult(
                is_valid=False,
                status=RiskValidationStatus.INVALID,
                rejection_reasons=rejection_reasons,
                symbol=input_data.symbol,
                side=normalized_side.value,
                entry_price=cls._apply_precision(entry_d, cfg),
                effective_sl=cls._apply_precision(effective_sl, cfg),
                sl_source=sl_source,
                risk_distance=cls._apply_precision(risk_distance, cfg),
            )

        # 5. Calculate R-Multiple Targets
        # BUY: TP = entry + risk_distance * R
        # SELL: TP = entry - risk_distance * R
        r_targets_map: Dict[str, Decimal] = {}
        tp_1R: Optional[Decimal] = None
        tp_1_5R: Optional[Decimal] = None
        tp_2R: Optional[Decimal] = None
        tp_3R: Optional[Decimal] = None

        for r_val in cfg.r_multiples:
            if normalized_side == Side.BUY:
                raw_target = entry_d + (risk_distance * r_val)
            else:
                raw_target = entry_d - (risk_distance * r_val)

            quantized_target = cls._apply_precision(raw_target, cfg)
            r_float = float(r_val)
            label = f"{r_float:g}R"
            r_targets_map[label] = quantized_target

            if r_float == 1.0:
                tp_1R = quantized_target
            elif r_float == 1.5:
                tp_1_5R = quantized_target
            elif r_float == 2.0:
                tp_2R = quantized_target
            elif r_float == 3.0:
                tp_3R = quantized_target

        # 6. Parse and Validate Provider Take Profits
        provider_tps_raw: List[Decimal] = []
        if input_data.provider_take_profits:
            for item in input_data.provider_take_profits:
                dec = cls._to_decimal(item)
                if dec is not None and dec > Decimal("0"):
                    provider_tps_raw.append(dec)
        elif input_data.provider_take_profit is not None:
            dec = cls._to_decimal(input_data.provider_take_profit)
            if dec is not None and dec > Decimal("0"):
                provider_tps_raw.append(dec)

        provider_tps_metrics: List[ProviderTPMetrics] = []
        valid_provider_tps: List[Decimal] = []

        for idx, ptp in enumerate(provider_tps_raw, start=1):
            # Validate TP Geometry
            # BUY: TP must be > entry
            # SELL: TP must be < entry
            if normalized_side == Side.BUY:
                reward = ptp - entry_d
                is_wrong_side = ptp <= entry_d
            else:
                reward = entry_d - ptp
                is_wrong_side = ptp >= entry_d

            if is_wrong_side:
                reason = (
                    RejectionReason.TP_BELOW_BUY_ENTRY.value
                    if normalized_side == Side.BUY
                    else RejectionReason.TP_ABOVE_SELL_ENTRY.value
                )
                rejection_reasons.append(f"TP{idx} ({ptp}): {reason}")
                continue

            rrr = reward / risk_distance
            is_low_rr = rrr < cfg.min_rr

            metric = ProviderTPMetrics(
                tp_index=idx,
                tp_price=cls._apply_precision(ptp, cfg),
                reward_distance=cls._apply_precision(reward, cfg),
                risk_reward_ratio=cls._round_ratio(rrr),
                is_low_rr=is_low_rr,
            )
            provider_tps_metrics.append(metric)
            valid_provider_tps.append(ptp)

        # 7. Resolve Effective Take Profit (TP Priority: PROVIDER -> CALCULATED -> NONE)
        effective_tp: Optional[Decimal] = None
        tp_source: TPSource = TPSource.NONE
        reward_distance: Optional[Decimal] = None
        risk_reward_ratio: Optional[Decimal] = None

        if valid_provider_tps:
            # Priority 1: Provider TP
            primary_tp = valid_provider_tps[0]
            effective_tp = cls._apply_precision(primary_tp, cfg)
            tp_source = TPSource.PROVIDER
            primary_metric = provider_tps_metrics[0]
            reward_distance = primary_metric.reward_distance
            risk_reward_ratio = primary_metric.risk_reward_ratio

            if primary_metric.is_low_rr:
                warning_flags.append(
                    f"LOW_RR: Provider TP1 RRR ({risk_reward_ratio}) is below configured MIN_RR ({cfg.min_rr})"
                )

        elif cfg.default_tp_r is not None and cfg.default_tp_r > Decimal("0"):
            # Priority 2: Configured R-multiple TP
            default_r = cfg.default_tp_r
            if normalized_side == Side.BUY:
                calc_tp = entry_d + (risk_distance * default_r)
            else:
                calc_tp = entry_d - (risk_distance * default_r)

            effective_tp = cls._apply_precision(calc_tp, cfg)
            tp_source = TPSource.CALCULATED
            reward_distance = cls._apply_precision(risk_distance * default_r, cfg)
            risk_reward_ratio = cls._round_ratio(default_r)
        else:
            # Priority 3: No TP
            tp_source = TPSource.NONE

        # 8. Determine Final Status
        if rejection_reasons:
            status = RiskValidationStatus.INVALID
            is_valid = False
        elif "LOW_RR" in [w.split(":")[0] for w in warning_flags]:
            status = RiskValidationStatus.LOW_RR
            is_valid = True
        else:
            status = RiskValidationStatus.VALID
            is_valid = True

        return RiskCalculationResult(
            is_valid=is_valid,
            status=status,
            rejection_reasons=rejection_reasons,
            warning_flags=warning_flags,
            symbol=input_data.symbol,
            side=normalized_side.value,
            entry_price=cls._apply_precision(entry_d, cfg),
            effective_sl=cls._apply_precision(effective_sl, cfg),
            sl_source=sl_source,
            risk_distance=cls._apply_precision(risk_distance, cfg),
            effective_tp=effective_tp,
            tp_source=tp_source,
            reward_distance=reward_distance,
            risk_reward_ratio=risk_reward_ratio,
            tp_1R=tp_1R,
            tp_1_5R=tp_1_5R,
            tp_2R=tp_2R,
            tp_3R=tp_3R,
            r_targets=r_targets_map,
            provider_tps_metrics=provider_tps_metrics,
        )

    # --- Helper Utilities ---

    @staticmethod
    def _normalize_side(side: Optional[Union[str, Side]]) -> Optional[Side]:
        if not side:
            return None
        if isinstance(side, Side):
            return side
        cleaned = str(side).strip().upper()
        if cleaned in ("BUY", "LONG"):
            return Side.BUY
        if cleaned in ("SELL", "SHORT"):
            return Side.SELL
        return None

    @staticmethod
    def _to_decimal(val: Any) -> Optional[Decimal]:
        if val is None:
            return None
        if isinstance(val, Decimal):
            return val
        try:
            val_str = str(val).strip()
            if not val_str or val_str.lower() in ("none", "null", "nan", "inf", "-inf"):
                return None
            return Decimal(val_str)
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _apply_precision(val: Optional[Decimal], cfg: RiskEngineConfig) -> Optional[Decimal]:
        if val is None:
            return None
        if cfg.tick_size is not None and cfg.tick_size > Decimal("0"):
            # Round to nearest tick_size
            num_ticks = (val / cfg.tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            return num_ticks * cfg.tick_size
        elif cfg.decimal_places is not None:
            quant = Decimal("10") ** -cfg.decimal_places
            return val.quantize(quant, rounding=ROUND_HALF_UP)
        return val

    @staticmethod
    def _round_ratio(val: Decimal) -> Decimal:
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _get_default_config(cls) -> RiskEngineConfig:
        r_multiples_list = [Decimal(str(r)) for r in settings.ALTERNATIVE_TP_R_MULTIPLES]
        return RiskEngineConfig(
            min_rr=Decimal(str(getattr(settings, "MIN_RR", 1.5))),
            r_multiples=r_multiples_list,
            default_tp_r=Decimal(str(settings.DEFAULT_TP_R_MULTIPLE)),
            allow_strategy_sl=settings.CONFIGURED_STRATEGY_SL_ENABLED,
        )

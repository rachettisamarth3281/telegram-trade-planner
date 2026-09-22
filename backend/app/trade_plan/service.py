from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Signal, TradePlan, ValueProvenance, TradePlanStatus
from app.paper_trading.position_sizing import PositionSizingService
from app.risk.guards import RiskGuardsService
from app.config.instruments import get_instrument_specification
from app.config import settings

class TradePlanService:
    """
    Trade Plan Generation, Provenance, and Manual Override Engine (V1).
    
    Implements:
    - SL/TP Rules 1–6
    - Provenance tracking (TELEGRAM, SYSTEM_CALCULATED, USER_MODIFIED)
    - Floor-quantized Position Sizing & Currency Conversion
    - Risk Guards Evaluation (Daily Risk, Open Trades, Min Volume)
    - Manual Overrides & Mark-as-Executed tracking
    - Zero live execution hooks.
    """

    def __init__(
        self,
        position_sizer: Optional[PositionSizingService] = None,
    ):
        self.position_sizer = position_sizer or PositionSizingService()

    async def generate_or_update_plan(
        self,
        db: AsyncSession,
        signal: Signal,
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> TradePlan:
        """
        Generate or update a TradePlan for a given Signal.
        Preserves original Telegram values while allowing user overrides.
        """
        now = datetime.now(timezone.utc)
        spec = get_instrument_specification(signal.symbol or "XAUUSD")

        # Check for existing TradePlan
        stmt = select(TradePlan).where(TradePlan.signal_id == signal.id)
        existing_plan = await db.scalar(stmt)
        plan = existing_plan or TradePlan(signal_id=signal.id, symbol=signal.symbol or "XAUUSD", side=signal.side or "BUY")

        # 1. Capture Original Telegram Values Snapshot (Never Overwritten)
        orig_telegram = {
            "symbol": signal.symbol,
            "side": signal.side,
            "entry_price": signal.entry_price,
            "entry_zone_low": signal.entry_zone_low,
            "entry_zone_high": signal.entry_zone_high,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "raw_message": signal.raw_message
        }
        plan.original_telegram_values = orig_telegram

        # 2. Resolve Entry Price & Zone
        overrides = user_overrides or {}
        if "entry_price" in overrides and overrides["entry_price"] is not None:
            entry = float(overrides["entry_price"])
            entry_prov = ValueProvenance.USER_MODIFIED.value
            zone_low = overrides.get("entry_zone_low", entry)
            zone_high = overrides.get("entry_zone_high", entry)
        else:
            entry = float(signal.entry_price or 0.0)
            entry_prov = ValueProvenance.TELEGRAM.value
            zone_low = signal.entry_zone_low or entry
            zone_high = signal.entry_zone_high or entry

        plan.symbol = signal.symbol or "XAUUSD"
        plan.side = signal.side or "BUY"
        plan.order_type = signal.order_type or "MARKET"
        plan.entry_price = entry if entry > 0 else None
        plan.entry_zone_low = zone_low if zone_low > 0 else None
        plan.entry_zone_high = zone_high if zone_high > 0 else None
        plan.entry_provenance = entry_prov

        # 3. Resolve Stop Loss (Rule 1 & Rule 4)
        if "stop_loss" in overrides and overrides["stop_loss"] is not None:
            sl = float(overrides["stop_loss"])
            sl_prov = ValueProvenance.USER_MODIFIED.value
        elif signal.stop_loss is not None:
            sl = float(signal.stop_loss)
            sl_prov = ValueProvenance.TELEGRAM.value
        else:
            sl = None
            sl_prov = ValueProvenance.TELEGRAM.value

        plan.stop_loss = sl
        plan.sl_provenance = sl_prov

        # Missing Entry check
        if entry <= 0:
            plan.plan_status = TradePlanStatus.INCOMPLETE.value
            plan.guard_rejection_reason = "Missing valid entry price"
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            return plan

        # Missing SL check (Rule 4: WAITING_FOR_SL, Rule 5: INCOMPLETE)
        if sl is None:
            has_tp = bool(signal.take_profit or signal.targets_json or overrides.get("tp1"))
            if has_tp:
                plan.plan_status = TradePlanStatus.WAITING_FOR_SL.value
                plan.guard_rejection_reason = "Awaiting correlated Telegram Stop Loss message"
            else:
                plan.plan_status = TradePlanStatus.INCOMPLETE.value
                plan.guard_rejection_reason = "Missing Stop Loss and Take Profit"

            plan.calculated_lot_size = 0.0
            plan.monetary_risk_inr = 0.0
            plan.monetary_risk_usd = 0.0
            plan.risk_distance_points = None
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            return plan

        # Directional Geometry Check
        is_buy = plan.side.upper() == "BUY"
        if is_buy and sl >= entry:
            plan.plan_status = TradePlanStatus.REJECTED.value
            plan.guard_rejection_reason = f"Invalid BUY geometry: Stop Loss ({sl}) is at or above Entry ({entry})"
            plan.calculated_lot_size = 0.0
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            return plan
        elif not is_buy and sl <= entry:
            plan.plan_status = TradePlanStatus.REJECTED.value
            plan.guard_rejection_reason = f"Invalid SELL geometry: Stop Loss ({sl}) is at or below Entry ({entry})"
            plan.calculated_lot_size = 0.0
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            return plan

        # Risk Distance in price points
        risk_dist = abs(entry - sl)
        plan.risk_distance_points = round(risk_dist, 4)

        # 4. Resolve Take Profits (Rules 2 & 3)
        # Parse targets from signal
        telegram_targets: List[float] = []
        if signal.targets_json:
            import json
            try:
                t_list = json.loads(signal.targets_json)
                for item in t_list:
                    if isinstance(item, dict) and "price" in item:
                        telegram_targets.append(float(item["price"]))
                    elif isinstance(item, (int, float)):
                        telegram_targets.append(float(item))
            except Exception:
                pass
        if not telegram_targets and signal.take_profit:
            telegram_targets.append(float(signal.take_profit))

        # TP1
        if "tp1" in overrides and overrides["tp1"] is not None:
            plan.tp1 = float(overrides["tp1"])
            plan.tp1_provenance = ValueProvenance.USER_MODIFIED.value
        elif len(telegram_targets) >= 1:
            plan.tp1 = telegram_targets[0]
            plan.tp1_provenance = ValueProvenance.TELEGRAM.value
        else:
            plan.tp1 = round(entry + (risk_dist * 1.0) if is_buy else entry - (risk_dist * 1.0), 2)
            plan.tp1_provenance = ValueProvenance.SYSTEM_CALCULATED.value

        # TP2
        if "tp2" in overrides and overrides["tp2"] is not None:
            plan.tp2 = float(overrides["tp2"])
            plan.tp2_provenance = ValueProvenance.USER_MODIFIED.value
        elif len(telegram_targets) >= 2:
            plan.tp2 = telegram_targets[1]
            plan.tp2_provenance = ValueProvenance.TELEGRAM.value
        else:
            plan.tp2 = round(entry + (risk_dist * 2.0) if is_buy else entry - (risk_dist * 2.0), 2)
            plan.tp2_provenance = ValueProvenance.SYSTEM_CALCULATED.value

        # TP3
        if "tp3" in overrides and overrides["tp3"] is not None:
            plan.tp3 = float(overrides["tp3"])
            plan.tp3_provenance = ValueProvenance.USER_MODIFIED.value
        elif len(telegram_targets) >= 3:
            plan.tp3 = telegram_targets[2]
            plan.tp3_provenance = ValueProvenance.TELEGRAM.value
        else:
            plan.tp3 = round(entry + (risk_dist * 3.0) if is_buy else entry - (risk_dist * 3.0), 2)
            plan.tp3_provenance = ValueProvenance.SYSTEM_CALCULATED.value

        # Reward/Risk Ratios
        plan.reward_risk_ratio_tp1 = round(abs(plan.tp1 - entry) / risk_dist, 2) if plan.tp1 else None
        plan.reward_risk_ratio_tp2 = round(abs(plan.tp2 - entry) / risk_dist, 2) if plan.tp2 else None
        plan.reward_risk_ratio_tp3 = round(abs(plan.tp3 - entry) / risk_dist, 2) if plan.tp3 else None

        # 5. Position Sizing & Currency Conversion
        pos_result = self.position_sizer.calculate_trade_plan_position_size(
            symbol=plan.symbol,
            risk_distance=Decimal(str(risk_dist)),
            account_balance_inr=Decimal(str(settings.CURRENT_BALANCE)),
            risk_percent=Decimal(str(settings.RISK_PER_TRADE_PCT)),
            usd_inr_rate=Decimal(str(settings.MANUAL_USD_INR_RATE))
        )

        plan.calculated_lot_size = pos_result["lot_size"]
        plan.monetary_risk_inr = pos_result["monetary_risk_inr"]
        plan.monetary_risk_usd = pos_result["monetary_risk_usd"]

        # 6. Evaluate Risk Guards
        is_ready, guard_reason, audit_details = await RiskGuardsService.evaluate_guards(
            db=db,
            plan_risk_inr=plan.monetary_risk_inr,
            calculated_lot_size=plan.calculated_lot_size,
            position_sizing_reason=pos_result.get("rejection_reason")
        )

        audit_details.update({
            "entry": entry,
            "stop_loss": sl,
            "risk_distance": risk_dist,
            "tp1": plan.tp1,
            "tp2": plan.tp2,
            "tp3": plan.tp3,
            "provenances": {
                "entry": plan.entry_provenance,
                "sl": plan.sl_provenance,
                "tp1": plan.tp1_provenance,
                "tp2": plan.tp2_provenance,
                "tp3": plan.tp3_provenance,
            }
        })
        plan.calculation_details = audit_details

        if plan.is_manually_executed:
            plan.plan_status = TradePlanStatus.MARKED_EXECUTED.value
            plan.guard_rejection_reason = None
        elif is_ready:
            plan.plan_status = TradePlanStatus.READY.value
            plan.guard_rejection_reason = None
        else:
            plan.plan_status = TradePlanStatus.NOT_READY.value
            plan.guard_rejection_reason = guard_reason

        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan

from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.models import TradePlan

class RiskGuardsService:
    """
    Risk Guard Engine (V1 Trade Planning).
    
    Evaluates:
    1. Maximum Risk per Trade: Current Balance * Risk % (e.g. 50,000 * 1% = ₹500)
    2. Maximum Daily Risk: Daily Starting Balance * 3% (e.g. 50,000 * 3% = ₹1,500)
    3. Maximum Open Trades: 3 open/executed trades
    4. Minimum Tradable Volume: Volume >= min_volume (0.01 lot)
    
    If any guard is triggered:
    - Ingestion and signal analysis CONTINUES normally.
    - TradePlan is marked NOT_READY with an explicit, auditable guard explanation.
    """

    @classmethod
    async def evaluate_guards(
        cls,
        db: AsyncSession,
        plan_risk_inr: float,
        calculated_lot_size: float,
        position_sizing_reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Evaluate all risk guards.
        Returns: (is_ready: bool, guard_rejection_reason: Optional[str], audit_details: Dict[str, Any])
        """
        current_balance = Decimal(str(settings.CURRENT_BALANCE))
        daily_starting_balance = Decimal(str(settings.DAILY_STARTING_BALANCE))
        risk_per_trade_pct = Decimal(str(settings.RISK_PER_TRADE_PCT))
        max_daily_risk_pct = Decimal(str(settings.MAX_DAILY_RISK_PCT))
        max_open_trades = settings.MAX_OPEN_TRADES

        max_risk_per_trade_inr = (current_balance * risk_per_trade_pct) / Decimal("100.0")
        daily_risk_limit_inr = (daily_starting_balance * max_daily_risk_pct) / Decimal("100.0")

        # 1. Query active open/executed trade plans for today
        stmt_open = select(func.count(TradePlan.id)).where(
            TradePlan.is_manually_executed == True,
            TradePlan.plan_status.in_(("MARKED_EXECUTED", "OPEN"))
        )
        open_trades_count = (await db.scalar(stmt_open)) or 0

        # Sum daily risk used by executed plans
        stmt_daily_risk = select(func.sum(TradePlan.monetary_risk_inr)).where(
            TradePlan.is_manually_executed == True
        )
        daily_risk_used_inr = Decimal(str((await db.scalar(stmt_daily_risk)) or 0.0))
        daily_risk_remaining_inr = max(Decimal("0.0"), daily_risk_limit_inr - daily_risk_used_inr)

        audit_details = {
            "current_balance_inr": float(current_balance),
            "daily_starting_balance_inr": float(daily_starting_balance),
            "risk_per_trade_pct": float(risk_per_trade_pct),
            "max_risk_per_trade_inr": float(max_risk_per_trade_inr),
            "max_daily_risk_pct": float(max_daily_risk_pct),
            "daily_risk_limit_inr": float(daily_risk_limit_inr),
            "daily_risk_used_inr": float(daily_risk_used_inr),
            "daily_risk_remaining_inr": float(daily_risk_remaining_inr),
            "open_trades_count": open_trades_count,
            "max_open_trades": max_open_trades,
            "calculated_lot_size": calculated_lot_size,
            "plan_risk_inr": plan_risk_inr
        }

        # Guard 1: Minimum volume rejection from position sizer
        if calculated_lot_size <= 0.0:
            reason = position_sizing_reason or "Minimum tradable volume exceeds configured risk."
            return False, reason, audit_details

        # Guard 2: Daily risk exhaustion
        if (daily_risk_used_inr + Decimal(str(plan_risk_inr))) > daily_risk_limit_inr:
            reason = f"DAILY_RISK_EXHAUSTED: Daily risk limit of ₹{daily_risk_limit_inr:.2f} reached (Used: ₹{daily_risk_used_inr:.2f}, Remaining: ₹{daily_risk_remaining_inr:.2f})."
            return False, reason, audit_details

        # Guard 3: Max open trades limit
        if open_trades_count >= max_open_trades:
            reason = f"MAX_OPEN_TRADES_REACHED: Maximum {max_open_trades} open trades limit reached ({open_trades_count} active)."
            return False, reason, audit_details

        # Guard 4: Single trade risk exceeds configured maximum
        if Decimal(str(plan_risk_inr)) > max_risk_per_trade_inr:
            reason = f"RISK_EXCEEDS_LIMIT: Trade risk (₹{plan_risk_inr:.2f}) exceeds max per-trade limit of ₹{max_risk_per_trade_inr:.2f}."
            return False, reason, audit_details

        return True, None, audit_details


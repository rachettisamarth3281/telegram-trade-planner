from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import TradePlan, Signal, ValueProvenance, TradePlanStatus
from app.trade_plan.service import TradePlanService

router = APIRouter(prefix="/trade-plans", tags=["Trade Plans (V1)"])
trade_plan_service = TradePlanService()

class TradePlanOverrideRequest(BaseModel):
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    notes: Optional[str] = None

class MarkExecutedRequest(BaseModel):
    notes: Optional[str] = None

def serialize_trade_plan(plan: TradePlan, raw_message: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": plan.id,
        "signal_id": plan.signal_id,
        "symbol": plan.symbol,
        "side": plan.side,
        "order_type": plan.order_type,
        "entry_price": plan.entry_price,
        "entry_zone_low": plan.entry_zone_low,
        "entry_zone_high": plan.entry_zone_high,
        "entry_provenance": plan.entry_provenance,
        "stop_loss": plan.stop_loss,
        "sl_provenance": plan.sl_provenance,
        "tp1": plan.tp1,
        "tp1_provenance": plan.tp1_provenance,
        "tp2": plan.tp2,
        "tp2_provenance": plan.tp2_provenance,
        "tp3": plan.tp3,
        "tp3_provenance": plan.tp3_provenance,
        "calculated_lot_size": plan.calculated_lot_size,
        "monetary_risk_inr": plan.monetary_risk_inr,
        "monetary_risk_usd": plan.monetary_risk_usd,
        "risk_distance_points": plan.risk_distance_points,
        "reward_risk_ratio_tp1": plan.reward_risk_ratio_tp1,
        "reward_risk_ratio_tp2": plan.reward_risk_ratio_tp2,
        "reward_risk_ratio_tp3": plan.reward_risk_ratio_tp3,
        "plan_status": plan.plan_status,
        "guard_rejection_reason": plan.guard_rejection_reason,
        "is_manually_executed": plan.is_manually_executed,
        "executed_at": plan.executed_at.isoformat() if plan.executed_at else None,
        "notes": plan.notes,
        "calculation_details": plan.calculation_details or {},
        "original_telegram_values": plan.original_telegram_values or {},
        "raw_message": raw_message or (plan.original_telegram_values or {}).get("raw_message", ""),
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }

@router.get("")
async def list_trade_plans(
    status: Optional[str] = Query(None, description="Filter by plan_status: READY, NOT_READY, WAITING_FOR_SL, MARKED_EXECUTED, etc."),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    is_executed: Optional[bool] = Query(None, description="Filter by manual execution"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List Trade Plans with full provenance and guard tracking."""
    stmt = select(TradePlan).options(selectinload(TradePlan.signal)).order_by(desc(TradePlan.created_at))

    if status:
        stmt = stmt.where(TradePlan.plan_status == status)
    if symbol:
        stmt = stmt.where(TradePlan.symbol == symbol)
    if is_executed is not None:
        stmt = stmt.where(TradePlan.is_manually_executed == is_executed)

    stmt = stmt.offset(offset).limit(limit)
    plans = (await db.scalars(stmt)).all()

    return [serialize_trade_plan(p, p.signal.raw_message if p.signal else None) for p in plans]

@router.get("/{plan_id}")
async def get_trade_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a single Trade Plan by ID."""
    stmt = select(TradePlan).options(selectinload(TradePlan.signal)).where(TradePlan.id == plan_id)
    plan = await db.scalar(stmt)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Trade plan {plan_id} not found")

    return serialize_trade_plan(plan, plan.signal.raw_message if plan.signal else None)

@router.patch("/{plan_id}")
async def override_trade_plan(
    plan_id: str,
    payload: TradePlanOverrideRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually override Entry, SL, TP1, TP2, TP3 on a Trade Plan.
    Recalculates position size, risk, and RR without altering the raw Telegram signal.
    """
    stmt = select(TradePlan).options(selectinload(TradePlan.signal)).where(TradePlan.id == plan_id)
    plan = await db.scalar(stmt)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Trade plan {plan_id} not found")

    if not plan.signal:
        raise HTTPException(status_code=400, detail="Associated signal record is missing")

    overrides = payload.model_dump(exclude_unset=True)
    if payload.notes is not None:
        plan.notes = payload.notes

    updated_plan = await trade_plan_service.generate_or_update_plan(
        db=db,
        signal=plan.signal,
        user_overrides=overrides
    )

    return serialize_trade_plan(updated_plan, plan.signal.raw_message)

@router.post("/{plan_id}/mark-executed")
async def mark_plan_executed(
    plan_id: str,
    payload: Optional[MarkExecutedRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark Trade Plan as manually executed elsewhere by the user.
    This does NOT execute live broker orders.
    """
    stmt = select(TradePlan).options(selectinload(TradePlan.signal)).where(TradePlan.id == plan_id)
    plan = await db.scalar(stmt)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Trade plan {plan_id} not found")

    plan.is_manually_executed = True
    plan.plan_status = TradePlanStatus.MARKED_EXECUTED.value
    plan.executed_at = datetime.now(timezone.utc)
    if payload and payload.notes:
        plan.notes = payload.notes

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return serialize_trade_plan(plan, plan.signal.raw_message if plan.signal else None)

@router.post("/{plan_id}/unmark-executed")
async def unmark_plan_executed(plan_id: str, db: AsyncSession = Depends(get_db)):
    """Unmark a trade plan from manually executed state."""
    stmt = select(TradePlan).options(selectinload(TradePlan.signal)).where(TradePlan.id == plan_id)
    plan = await db.scalar(stmt)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Trade plan {plan_id} not found")

    plan.is_manually_executed = False
    plan.executed_at = None

    # Re-evaluate status
    updated_plan = await trade_plan_service.generate_or_update_plan(db=db, signal=plan.signal)
    return serialize_trade_plan(updated_plan, plan.signal.raw_message if plan.signal else None)


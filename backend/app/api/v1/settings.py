from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.config import settings
from app.config.instruments import (
    get_instrument_specification,
    update_instrument_specification,
    list_instrument_specifications,
    InstrumentSpec
)
from app.database.session import get_db
from app.database.models import TradePlan

router = APIRouter(prefix="/settings", tags=["Settings & Account"])

# In-memory runtime settings cache (initialized from app config)
runtime_settings = {
    "account_currency": settings.ACCOUNT_CURRENCY,
    "initial_balance": float(settings.INITIAL_BALANCE),
    "current_balance": float(settings.CURRENT_BALANCE),
    "daily_starting_balance": float(settings.DAILY_STARTING_BALANCE),
    "risk_percent": float(settings.RISK_PER_TRADE_PCT),
    "max_daily_risk_pct": float(settings.MAX_DAILY_RISK_PCT),
    "max_open_trades": int(settings.MAX_OPEN_TRADES),
    "usd_inr_conversion_mode": settings.USD_INR_CONVERSION_MODE,
    "manual_usd_inr_rate": float(settings.MANUAL_USD_INR_RATE),
    "default_r_multiple": float(settings.DEFAULT_TP_R_MULTIPLE),
    "alternative_r_multiples": [float(r) for r in settings.ALTERNATIVE_TP_R_MULTIPLES],
    "min_risk_reward_ratio": float(getattr(settings, "MIN_RR", 1.5)),
}

class UpdateAccountSettingsV1Request(BaseModel):
    initial_balance: Optional[float] = None
    current_balance: Optional[float] = None
    daily_starting_balance: Optional[float] = None
    risk_percent: Optional[float] = None
    max_daily_risk_pct: Optional[float] = None
    max_open_trades: Optional[int] = None
    manual_usd_inr_rate: Optional[float] = None
    usd_inr_conversion_mode: Optional[str] = None

class InstrumentSpecUpdate(BaseModel):
    contract_size: Optional[float] = None
    tick_size: Optional[float] = None
    min_volume: Optional[float] = None
    volume_step: Optional[float] = None
    profit_currency: Optional[str] = None
    description: Optional[str] = None

@router.get("/account-v1")
async def get_account_v1(db: AsyncSession = Depends(get_db)):
    """Retrieve V1 Account Risk & Budget status."""
    current_balance = runtime_settings["current_balance"]
    daily_starting_balance = runtime_settings["daily_starting_balance"]
    risk_pct = runtime_settings["risk_percent"]
    max_daily_risk_pct = runtime_settings["max_daily_risk_pct"]

    max_risk_per_trade = round(current_balance * (risk_pct / 100.0), 2)
    daily_risk_limit = round(daily_starting_balance * (max_daily_risk_pct / 100.0), 2)

    # Query daily risk used & open trades count
    stmt_open = select(func.count(TradePlan.id)).where(
        TradePlan.is_manually_executed == True,
        TradePlan.plan_status.in_(("MARKED_EXECUTED", "OPEN"))
    )
    open_trades_count = (await db.scalar(stmt_open)) or 0

    stmt_daily_risk = select(func.sum(TradePlan.monetary_risk_inr)).where(
        TradePlan.is_manually_executed == True
    )
    daily_risk_used = float((await db.scalar(stmt_daily_risk)) or 0.0)
    daily_risk_remaining = max(0.0, daily_risk_limit - daily_risk_used)

    return {
        "account_currency": runtime_settings["account_currency"],
        "initial_balance": runtime_settings["initial_balance"],
        "current_balance": current_balance,
        "daily_starting_balance": daily_starting_balance,
        "risk_percent": risk_pct,
        "max_risk_per_trade_inr": max_risk_per_trade,
        "max_daily_risk_pct": max_daily_risk_pct,
        "daily_risk_limit_inr": daily_risk_limit,
        "daily_risk_used_inr": round(daily_risk_used, 2),
        "daily_risk_remaining_inr": round(daily_risk_remaining, 2),
        "open_trades_count": open_trades_count,
        "max_open_trades": runtime_settings["max_open_trades"],
        "usd_inr_conversion_mode": runtime_settings["usd_inr_conversion_mode"],
        "manual_usd_inr_rate": runtime_settings["manual_usd_inr_rate"]
    }

@router.patch("/account-v1")
async def update_account_v1(payload: UpdateAccountSettingsV1Request, db: AsyncSession = Depends(get_db)):
    """Update V1 Account Risk & Budget parameters."""
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None and key in runtime_settings:
            runtime_settings[key] = value

    # Sync settings object
    settings.CURRENT_BALANCE = runtime_settings["current_balance"]
    settings.RISK_PER_TRADE_PCT = runtime_settings["risk_percent"]
    settings.MANUAL_USD_INR_RATE = runtime_settings["manual_usd_inr_rate"]
    settings.DAILY_STARTING_BALANCE = runtime_settings["daily_starting_balance"]

    return await get_account_v1(db)

@router.get("/instruments")
async def get_instruments():
    """List all configured instruments."""
    specs = list_instrument_specifications()
    return {k: v.model_dump() for k, v in specs.items()}

@router.patch("/instruments/{symbol}")
async def update_instrument(symbol: str, payload: InstrumentSpecUpdate):
    """Update instrument specifications for a given symbol."""
    spec = get_instrument_specification(symbol)
    updates = payload.model_dump(exclude_unset=True)
    if "contract_size" in updates and updates["contract_size"] is not None:
        spec.contract_size = Decimal(str(updates["contract_size"]))
    if "tick_size" in updates and updates["tick_size"] is not None:
        spec.tick_size = Decimal(str(updates["tick_size"]))
    if "min_volume" in updates and updates["min_volume"] is not None:
        spec.min_volume = Decimal(str(updates["min_volume"]))
    if "volume_step" in updates and updates["volume_step"] is not None:
        spec.volume_step = Decimal(str(updates["volume_step"]))
    if "profit_currency" in updates and updates["profit_currency"] is not None:
        spec.profit_currency = updates["profit_currency"]
    if "description" in updates and updates["description"] is not None:
        spec.description = updates["description"]

    updated = update_instrument_specification(symbol, spec)
    return updated.model_dump()

# Legacy endpoints for compatibility
@router.get("/account")
async def get_account(db: AsyncSession = Depends(get_db)):
    return await get_account_v1(db)

@router.get("/system")
async def get_system_settings():
    return runtime_settings

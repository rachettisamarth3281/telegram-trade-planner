from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List

from app.database import get_db
from app.database.models import PaperTrade
from app.analytics.service import TradeJournalAnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/report")
async def get_complete_report(db: AsyncSession = Depends(get_db)):
    """Comprehensive trade journal and statistical analytics report."""
    report = await TradeJournalAnalyticsService.generate_complete_report(db)
    return report.to_dict()

@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Summary KPI statistics for signals, paper trades, and risk metrics."""
    report = await TradeJournalAnalyticsService.generate_complete_report(db)
    data = report.to_dict()
    return {
        "signals": data["signals"],
        "trades": data["trades"],
        "performance": data["performance"],
        "provider_comparison": data["provider_comparison"],
    }

@router.get("/by-symbol")
async def get_by_symbol(db: AsyncSession = Depends(get_db)):
    """Performance breakdown grouped by trading instrument."""
    report = await TradeJournalAnalyticsService.generate_complete_report(db)
    return report.to_dict()["trades_by_symbol"]

@router.get("/by-side")
async def get_by_side(db: AsyncSession = Depends(get_db)):
    """Performance breakdown grouped by trade side (BUY vs SELL)."""
    report = await TradeJournalAnalyticsService.generate_complete_report(db)
    return report.to_dict()["trades_by_side"]

@router.get("/by-date")
async def get_by_date(db: AsyncSession = Depends(get_db)):
    """Performance breakdown grouped by date (UTC)."""
    report = await TradeJournalAnalyticsService.generate_complete_report(db)
    return report.to_dict()["trades_by_date"]

@router.get("/by-hour")
async def get_by_hour(db: AsyncSession = Depends(get_db)):
    """Performance breakdown grouped by hour of the day (0-23 UTC)."""
    report = await TradeJournalAnalyticsService.generate_complete_report(db)
    return report.to_dict()["trades_by_hour"]

@router.get("/equity-curve")
async def get_equity_curve(db: AsyncSession = Depends(get_db)):
    """Calculates chronological cumulative P&L and cumulative R curve."""
    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.status.startswith("CLOSED")
        ).order_by(PaperTrade.closed_at)
    )
    closed_trades = result.scalars().all()

    points = []
    cumulative_pnl = 0.0
    cumulative_r = 0.0

    for i, t in enumerate(closed_trades, 1):
        cumulative_pnl = round(cumulative_pnl + float(t.realized_pnl or 0.0), 2)
        cumulative_r = round(cumulative_r + float(t.realized_r or 0.0), 2)
        points.append({
            "trade_index": i,
            "trade_id": t.id,
            "symbol": t.symbol,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            "realized_pnl": float(t.realized_pnl) if t.realized_pnl is not None else 0.0,
            "realized_r": float(t.realized_r) if t.realized_r is not None else 0.0,
            "cumulative_pnl": cumulative_pnl,
            "cumulative_r": cumulative_r
        })

    return {
        "total_trades": len(closed_trades),
        "cumulative_pnl": cumulative_pnl,
        "cumulative_r": cumulative_r,
        "curve": points
    }

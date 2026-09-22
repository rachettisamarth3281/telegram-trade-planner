from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.models import Signal, PaperTrade

class AnalyticsEngine:
    """
    Analytics and Performance Metrics Engine.
    Computes statistical edge, expectancy, profit factor, win rate, R-distribution, and symbol rankings.
    """

    @classmethod
    async def get_summary_metrics(cls, db: AsyncSession) -> Dict[str, Any]:
        total_signals = await db.scalar(select(func.count(Signal.id))) or 0
        valid_signals = await db.scalar(select(func.count(Signal.id)).where(Signal.status == "VALID")) or 0
        invalid_signals = await db.scalar(select(func.count(Signal.id)).where(Signal.status == "INVALID")) or 0
        skipped_signals = await db.scalar(select(func.count(Signal.id)).where(Signal.status.like("SKIPPED%"))) or 0

        trades_result = await db.execute(select(PaperTrade))
        all_trades = trades_result.scalars().all()

        total_trades = len(all_trades)
        open_trades = [t for t in all_trades if t.status == "OPEN"]
        closed_trades = [t for t in all_trades if t.status.startswith("CLOSED")]

        winning_trades = [t for t in closed_trades if (t.realized_pnl or 0) > 0]
        losing_trades = [t for t in closed_trades if (t.realized_pnl or 0) < 0]
        breakeven_trades = [t for t in closed_trades if (t.realized_pnl or 0) == 0]

        total_closed = len(closed_trades)
        win_rate = (len(winning_trades) / total_closed * 100) if total_closed > 0 else 0.0

        gross_profit = sum(t.realized_pnl for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
        net_pnl = sum(t.realized_pnl for t in closed_trades)
        total_pips = sum(t.realized_pips for t in closed_trades)
        total_r = sum(t.realized_r for t in closed_trades)

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 1.0)

        avg_win_r = (sum(t.realized_r for t in winning_trades) / len(winning_trades)) if winning_trades else 0.0
        avg_loss_r = (abs(sum(t.realized_r for t in losing_trades)) / len(losing_trades)) if losing_trades else 0.0

        win_prob = len(winning_trades) / total_closed if total_closed > 0 else 0.0
        loss_prob = len(losing_trades) / total_closed if total_closed > 0 else 0.0
        expectancy_r = (win_prob * avg_win_r) - (loss_prob * avg_loss_r)

        return {
            "signals": {
                "total_received": total_signals,
                "total_signals": total_signals,
                "valid": valid_signals,
                "invalid": invalid_signals,
                "skipped": skipped_signals,
                "validity_rate": round((valid_signals / total_signals * 100) if total_signals > 0 else 0.0, 1)
            },
            "paper_trading": {
                "total_trades": total_trades,
                "open_trades": len(open_trades),
                "closed_trades": total_closed,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "breakeven_trades": len(breakeven_trades),
                "win_rate_pct": round(win_rate, 1),
                "net_pnl_usd": round(net_pnl, 2),
                "total_pips": round(total_pips, 1),
                "total_r_multiple": round(total_r, 2),
                "profit_factor": round(profit_factor, 2),
                "expectancy_r": round(expectancy_r, 2),
                "avg_win_r": round(avg_win_r, 2),
                "avg_loss_r": round(avg_loss_r, 2)
            }
        }

    @classmethod
    async def get_performance_by_symbol(cls, db: AsyncSession) -> List[Dict[str, Any]]:
        trades_result = await db.execute(select(PaperTrade))
        trades = trades_result.scalars().all()

        symbol_groups: Dict[str, List[PaperTrade]] = {}
        for t in trades:
            sym = t.symbol or "UNKNOWN"
            symbol_groups.setdefault(sym, []).append(t)

        results = []
        for sym, sym_trades in symbol_groups.items():
            closed = [t for t in sym_trades if t.status.startswith("CLOSED")]
            wins = [t for t in closed if (t.realized_pnl or 0) > 0]
            total_closed = len(closed)
            win_rate = (len(wins) / total_closed * 100) if total_closed > 0 else 0.0
            net_pnl = sum(t.realized_pnl for t in closed)
            total_r = sum(t.realized_r for t in closed)

            results.append({
                "symbol": sym,
                "total_trades": len(sym_trades),
                "closed_trades": total_closed,
                "win_rate_pct": round(win_rate, 1),
                "net_pnl_usd": round(net_pnl, 2),
                "total_r_multiple": round(total_r, 2)
            })

        return sorted(results, key=lambda x: x["net_pnl_usd"], reverse=True)

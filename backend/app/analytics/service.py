from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database.models import Signal, PaperTrade
from app.analytics.models import (
    SignalOverview,
    TradeOverview,
    PerformanceMetrics,
    ProviderTPComparison,
    SymbolPerformance,
    SidePerformance,
    DatePerformance,
    HourPerformance,
    CompleteAnalyticsReport,
)

class TradeJournalAnalyticsService:
    """
    Trade Journal & Objective Analytics Service.
    
    Principles:
    - Pure statistical reporting (NO subjective 'good' / 'bad' labels).
    - Preserves all historical records without lookahead bias.
    - Explicitly timezone-aware (UTC).
    """

    @classmethod
    async def generate_complete_report(cls, db: AsyncSession) -> CompleteAnalyticsReport:
        """Generates the full comprehensive analytics report."""
        # 1. Query all Signals
        signals_res = await db.execute(select(Signal).options(selectinload(Signal.paper_trades)))
        all_signals = list(signals_res.scalars().all())

        # 2. Query all Paper Trades
        trades_res = await db.execute(select(PaperTrade).options(selectinload(PaperTrade.signal)))
        all_trades = list(trades_res.scalars().all())

        signals_overview = cls._compute_signals_overview(all_signals)
        trades_overview = cls._compute_trades_overview(all_trades)
        performance = cls._compute_performance_metrics(all_trades)
        provider_comparison = cls._compute_provider_comparison(all_trades)
        trades_by_symbol = cls._compute_trades_by_symbol(all_trades)
        trades_by_side = cls._compute_trades_by_side(all_trades)
        trades_by_date = cls._compute_trades_by_date(all_trades)
        trades_by_hour = cls._compute_trades_by_hour(all_trades)

        return CompleteAnalyticsReport(
            signals=signals_overview,
            trades=trades_overview,
            performance=performance,
            provider_comparison=provider_comparison,
            trades_by_symbol=trades_by_symbol,
            trades_by_side=trades_by_side,
            trades_by_date=trades_by_date,
            trades_by_hour=trades_by_hour,
        )

    @classmethod
    def _compute_signals_overview(cls, all_signals: List[Signal]) -> SignalOverview:
        total = len(all_signals)
        valid_statuses = {"VALID", "PAPER_TRADE_CREATED"}
        valid_signals = [s for s in all_signals if s.status in valid_statuses]
        invalid_signals = [s for s in all_signals if s.status not in valid_statuses]

        reasons_map: Dict[str, int] = {}
        for s in invalid_signals:
            reason = s.rejection_reason or s.status or "UNKNOWN_REASON"
            # Extract primary reason code if joined by semicolon
            primary = reason.split(";")[0].strip()
            reasons_map[primary] = reasons_map.get(primary, 0) + 1

        val_rate = (len(valid_signals) / total * 100.0) if total > 0 else 0.0

        return SignalOverview(
            total_signals=total,
            valid_signals=len(valid_signals),
            invalid_signals=len(invalid_signals),
            validity_rate_pct=round(val_rate, 2),
            invalid_signal_reasons=reasons_map,
        )

    @classmethod
    def _compute_trades_overview(cls, all_trades: List[PaperTrade]) -> TradeOverview:
        total = len(all_trades)
        open_trades = [t for t in all_trades if t.status in ("OPEN", "PENDING")]
        closed_trades = [
            t for t in all_trades
            if t.status in ("TP_HIT", "SL_HIT", "MANUAL_CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL", "CANCELLED")
            or t.closed_at is not None
        ]

        wins = [t for t in closed_trades if (t.realized_pnl or 0) > 0 or (t.realized_r or 0) > 0.05]
        losses = [t for t in closed_trades if (t.realized_pnl or 0) < 0 or (t.realized_r or 0) < -0.05]
        breakeven = [t for t in closed_trades if t not in wins and t not in losses]

        win_rate = (len(wins) / len(closed_trades) * 100.0) if len(closed_trades) > 0 else 0.0

        return TradeOverview(
            paper_trades=total,
            open_trades=len(open_trades),
            closed_trades=len(closed_trades),
            wins=len(wins),
            losses=len(losses),
            breakeven=len(breakeven),
            win_rate_pct=round(win_rate, 2),
        )

    @classmethod
    def _compute_performance_metrics(cls, all_trades: List[PaperTrade]) -> PerformanceMetrics:
        closed_trades = [
            t for t in all_trades
            if t.status in ("TP_HIT", "SL_HIT", "MANUAL_CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL", "CANCELLED")
            or t.closed_at is not None
        ]

        if not closed_trades:
            avg_rr = (sum(t.target_r_multiple or 2.0 for t in all_trades) / len(all_trades)) if all_trades else 0.0
            return PerformanceMetrics(average_risk_reward=round(avg_rr, 2))

        wins = [t for t in closed_trades if (t.realized_pnl or 0) > 0 or (t.realized_r or 0) > 0.05]
        losses = [t for t in closed_trades if (t.realized_pnl or 0) < 0 or (t.realized_r or 0) < -0.05]

        total_r = sum(t.realized_r or 0.0 for t in closed_trades)
        avg_r = total_r / len(closed_trades)
        avg_win_r = (sum(t.realized_r or 0.0 for t in wins) / len(wins)) if wins else 0.0
        avg_loss_r = (abs(sum(t.realized_r or 0.0 for t in losses)) / len(losses)) if losses else 0.0

        gross_profit = sum(t.realized_pnl or 0.0 for t in wins)
        gross_loss = abs(sum(t.realized_pnl or 0.0 for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        # Chronological streak and drawdown calculations (Lookahead-free)
        sorted_trades = sorted(
            closed_trades,
            key=lambda t: t.closed_at or t.opened_at or t.created_at or datetime.min.replace(tzinfo=timezone.utc)
        )

        max_win_streak = 0
        max_loss_streak = 0
        curr_win_streak = 0
        curr_loss_streak = 0

        cum_r = 0.0
        peak_r = 0.0
        max_dd_r = 0.0

        cum_usd = 0.0
        peak_usd = 0.0
        max_dd_usd = 0.0

        for t in sorted_trades:
            pnl = t.realized_pnl or 0.0
            r_val = t.realized_r or 0.0

            # Win/Loss Streak tracking
            if pnl > 0 or r_val > 0.05:
                curr_win_streak += 1
                curr_loss_streak = 0
                if curr_win_streak > max_win_streak:
                    max_win_streak = curr_win_streak
            elif pnl < 0 or r_val < -0.05:
                curr_loss_streak += 1
                curr_win_streak = 0
                if curr_loss_streak > max_loss_streak:
                    max_loss_streak = curr_loss_streak
            else:
                curr_win_streak = 0
                curr_loss_streak = 0

            # Drawdown in R
            cum_r += r_val
            if cum_r > peak_r:
                peak_r = cum_r
            dd_r = peak_r - cum_r
            if dd_r > max_dd_r:
                max_dd_r = dd_r

            # Drawdown in USD
            cum_usd += pnl
            if cum_usd > peak_usd:
                peak_usd = cum_usd
            dd_usd = peak_usd - cum_usd
            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd

        avg_rr = (sum(t.target_r_multiple or 2.0 for t in all_trades) / len(all_trades)) if all_trades else 0.0
        net_pnl = sum(t.realized_pnl or 0.0 for t in closed_trades)
        total_pips = sum(t.realized_pips or 0.0 for t in closed_trades)

        return PerformanceMetrics(
            total_realized_r=round(total_r, 2),
            average_r_per_trade=round(avg_r, 2),
            average_win_r=round(avg_win_r, 2),
            average_loss_r=round(avg_loss_r, 2),
            profit_factor=round(profit_factor, 2),
            max_winning_streak=max_win_streak,
            max_losing_streak=max_loss_streak,
            max_drawdown_r=round(max_dd_r, 2),
            max_drawdown_usd=round(max_dd_usd, 2),
            average_risk_reward=round(avg_rr, 2),
            net_pnl_usd=round(net_pnl, 2),
            total_pips=round(total_pips, 2),
        )

    @classmethod
    def _compute_provider_comparison(cls, all_trades: List[PaperTrade]) -> ProviderTPComparison:
        provider_trades: List[PaperTrade] = []
        calculated_trades: List[PaperTrade] = []

        for t in all_trades:
            sig = t.signal
            tp_source = None
            if sig and sig.take_profits and isinstance(sig.take_profits, dict):
                tp_source = sig.take_profits.get("tp_source")

            if tp_source == "PROVIDER":
                provider_trades.append(t)
            else:
                calculated_trades.append(t)

        def _stats(trade_list: List[PaperTrade]):
            closed = [
                t for t in trade_list
                if t.status in ("TP_HIT", "SL_HIT", "MANUAL_CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL", "CANCELLED")
                or t.closed_at is not None
            ]
            wins = [t for t in closed if (t.realized_pnl or 0) > 0 or (t.realized_r or 0) > 0.05]
            win_rate = (len(wins) / len(closed) * 100.0) if closed else 0.0
            tot_r = sum(t.realized_r or 0.0 for t in closed)
            avg_rrr = (sum(t.target_r_multiple or 2.0 for t in trade_list) / len(trade_list)) if trade_list else 0.0
            return len(closed), win_rate, tot_r, avg_rrr

        p_cnt, p_wr, p_r, p_rrr = _stats(provider_trades)
        c_cnt, c_wr, c_r, c_rrr = _stats(calculated_trades)

        return ProviderTPComparison(
            provider_tp_trades_count=len(provider_trades),
            calculated_tp_trades_count=len(calculated_trades),
            provider_tp_win_rate_pct=round(p_wr, 2),
            calculated_tp_win_rate_pct=round(c_wr, 2),
            provider_tp_total_r=round(p_r, 2),
            calculated_tp_total_r=round(c_r, 2),
            provider_tp_avg_rrr=round(p_rrr, 2),
            calculated_tp_avg_rrr=round(c_rrr, 2),
        )

    @classmethod
    def _compute_trades_by_symbol(cls, all_trades: List[PaperTrade]) -> List[SymbolPerformance]:
        groups: Dict[str, List[PaperTrade]] = {}
        for t in all_trades:
            sym = (t.symbol or "UNKNOWN").upper().strip()
            groups.setdefault(sym, []).append(t)

        result: List[SymbolPerformance] = []
        for sym, sym_trades in groups.items():
            closed = [
                t for t in sym_trades
                if t.status in ("TP_HIT", "SL_HIT", "MANUAL_CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL", "CANCELLED")
                or t.closed_at is not None
            ]
            wins = [t for t in closed if (t.realized_pnl or 0) > 0 or (t.realized_r or 0) > 0.05]
            losses = [t for t in closed if (t.realized_pnl or 0) < 0 or (t.realized_r or 0) < -0.05]
            win_rate = (len(wins) / len(closed) * 100.0) if closed else 0.0
            tot_r = sum(t.realized_r or 0.0 for t in closed)
            net_pnl = sum(t.realized_pnl or 0.0 for t in closed)

            result.append(SymbolPerformance(
                symbol=sym,
                trades_count=len(sym_trades),
                closed_trades=len(closed),
                wins=len(wins),
                losses=len(losses),
                win_rate_pct=round(win_rate, 2),
                total_r=round(tot_r, 2),
                net_pnl_usd=round(net_pnl, 2),
            ))

        return sorted(result, key=lambda x: x.total_r, reverse=True)

    @classmethod
    def _compute_trades_by_side(cls, all_trades: List[PaperTrade]) -> List[SidePerformance]:
        groups: Dict[str, List[PaperTrade]] = {"BUY": [], "SELL": []}
        for t in all_trades:
            side = (t.side or "BUY").upper().strip()
            groups.setdefault(side, []).append(t)

        result: List[SidePerformance] = []
        for side, side_trades in groups.items():
            closed = [
                t for t in side_trades
                if t.status in ("TP_HIT", "SL_HIT", "MANUAL_CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL", "CANCELLED")
                or t.closed_at is not None
            ]
            wins = [t for t in closed if (t.realized_pnl or 0) > 0 or (t.realized_r or 0) > 0.05]
            losses = [t for t in closed if (t.realized_pnl or 0) < 0 or (t.realized_r or 0) < -0.05]
            win_rate = (len(wins) / len(closed) * 100.0) if closed else 0.0
            tot_r = sum(t.realized_r or 0.0 for t in closed)
            net_pnl = sum(t.realized_pnl or 0.0 for t in closed)

            result.append(SidePerformance(
                side=side,
                trades_count=len(side_trades),
                closed_trades=len(closed),
                wins=len(wins),
                losses=len(losses),
                win_rate_pct=round(win_rate, 2),
                total_r=round(tot_r, 2),
                net_pnl_usd=round(net_pnl, 2),
            ))

        return sorted(result, key=lambda x: x.side)

    @classmethod
    def _compute_trades_by_date(cls, all_trades: List[PaperTrade]) -> List[DatePerformance]:
        groups: Dict[str, List[PaperTrade]] = {}
        for t in all_trades:
            ts = t.opened_at or t.created_at or datetime.now(timezone.utc)
            date_str = ts.astimezone(timezone.utc).strftime("%Y-%m-%d")
            groups.setdefault(date_str, []).append(t)

        result: List[DatePerformance] = []
        for date_str in sorted(groups.keys()):
            date_trades = groups[date_str]
            closed = [
                t for t in date_trades
                if t.status in ("TP_HIT", "SL_HIT", "MANUAL_CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL", "CANCELLED")
                or t.closed_at is not None
            ]
            wins = [t for t in closed if (t.realized_pnl or 0) > 0 or (t.realized_r or 0) > 0.05]
            losses = [t for t in closed if (t.realized_pnl or 0) < 0 or (t.realized_r or 0) < -0.05]
            tot_r = sum(t.realized_r or 0.0 for t in closed)
            net_pnl = sum(t.realized_pnl or 0.0 for t in closed)

            result.append(DatePerformance(
                date_str=date_str,
                trades_count=len(date_trades),
                wins=len(wins),
                losses=len(losses),
                total_r=round(tot_r, 2),
                net_pnl_usd=round(net_pnl, 2),
            ))

        return result

    @classmethod
    def _compute_trades_by_hour(cls, all_trades: List[PaperTrade]) -> List[HourPerformance]:
        hourly: Dict[int, List[PaperTrade]] = {h: [] for h in range(24)}
        for t in all_trades:
            ts = t.opened_at or t.created_at or datetime.now(timezone.utc)
            hour = ts.astimezone(timezone.utc).hour
            hourly[hour].append(t)

        result: List[HourPerformance] = []
        for h in range(24):
            h_trades = hourly[h]
            closed = [
                t for t in h_trades
                if t.status in ("TP_HIT", "SL_HIT", "MANUAL_CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL", "CANCELLED")
                or t.closed_at is not None
            ]
            tot_r = sum(t.realized_r or 0.0 for t in closed)
            net_pnl = sum(t.realized_pnl or 0.0 for t in closed)

            result.append(HourPerformance(
                hour=h,
                trades_count=len(h_trades),
                total_r=round(tot_r, 2),
                net_pnl_usd=round(net_pnl, 2),
            ))

        return result

# Global instance
analytics_service = TradeJournalAnalyticsService()

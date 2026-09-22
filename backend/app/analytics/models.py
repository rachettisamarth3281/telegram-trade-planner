from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class SignalOverview:
    total_signals: int = 0
    valid_signals: int = 0
    invalid_signals: int = 0
    validity_rate_pct: float = 0.0
    invalid_signal_reasons: Dict[str, int] = field(default_factory=dict)

@dataclass
class TradeOverview:
    paper_trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate_pct: float = 0.0

@dataclass
class PerformanceMetrics:
    total_realized_r: float = 0.0
    average_r_per_trade: float = 0.0
    average_win_r: float = 0.0
    average_loss_r: float = 0.0
    profit_factor: float = 0.0
    max_winning_streak: int = 0
    max_losing_streak: int = 0
    max_drawdown_r: float = 0.0
    max_drawdown_usd: float = 0.0
    average_risk_reward: float = 0.0
    net_pnl_usd: float = 0.0
    total_pips: float = 0.0

@dataclass
class ProviderTPComparison:
    provider_tp_trades_count: int = 0
    calculated_tp_trades_count: int = 0
    provider_tp_win_rate_pct: float = 0.0
    calculated_tp_win_rate_pct: float = 0.0
    provider_tp_total_r: float = 0.0
    calculated_tp_total_r: float = 0.0
    provider_tp_avg_rrr: float = 0.0
    calculated_tp_avg_rrr: float = 0.0

@dataclass
class SymbolPerformance:
    symbol: str
    trades_count: int
    closed_trades: int
    wins: int
    losses: int
    win_rate_pct: float
    total_r: float
    net_pnl_usd: float

@dataclass
class SidePerformance:
    side: str
    trades_count: int
    closed_trades: int
    wins: int
    losses: int
    win_rate_pct: float
    total_r: float
    net_pnl_usd: float

@dataclass
class DatePerformance:
    date_str: str  # YYYY-MM-DD
    trades_count: int
    wins: int
    losses: int
    total_r: float
    net_pnl_usd: float

@dataclass
class HourPerformance:
    hour: int  # 0 to 23 UTC
    trades_count: int
    total_r: float
    net_pnl_usd: float

@dataclass
class CompleteAnalyticsReport:
    signals: SignalOverview
    trades: TradeOverview
    performance: PerformanceMetrics
    provider_comparison: ProviderTPComparison
    trades_by_symbol: List[SymbolPerformance] = field(default_factory=list)
    trades_by_side: List[SidePerformance] = field(default_factory=list)
    trades_by_date: List[DatePerformance] = field(default_factory=list)
    trades_by_hour: List[HourPerformance] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signals": {
                "total_signals": self.signals.total_signals,
                "valid_signals": self.signals.valid_signals,
                "invalid_signals": self.signals.invalid_signals,
                "validity_rate_pct": self.signals.validity_rate_pct,
                "invalid_signal_reasons": self.signals.invalid_signal_reasons,
            },
            "trades": {
                "paper_trades": self.trades.paper_trades,
                "open_trades": self.trades.open_trades,
                "closed_trades": self.trades.closed_trades,
                "wins": self.trades.wins,
                "losses": self.trades.losses,
                "breakeven": self.trades.breakeven,
                "win_rate_pct": self.trades.win_rate_pct,
            },
            "performance": {
                "total_realized_r": self.performance.total_realized_r,
                "average_r_per_trade": self.performance.average_r_per_trade,
                "average_win_r": self.performance.average_win_r,
                "average_loss_r": self.performance.average_loss_r,
                "profit_factor": self.performance.profit_factor,
                "max_winning_streak": self.performance.max_winning_streak,
                "max_losing_streak": self.performance.max_losing_streak,
                "max_drawdown_r": self.performance.max_drawdown_r,
                "max_drawdown_usd": self.performance.max_drawdown_usd,
                "average_risk_reward": self.performance.average_risk_reward,
                "net_pnl_usd": self.performance.net_pnl_usd,
                "total_pips": self.performance.total_pips,
            },
            "provider_comparison": {
                "provider_tp_trades_count": self.provider_comparison.provider_tp_trades_count,
                "calculated_tp_trades_count": self.provider_comparison.calculated_tp_trades_count,
                "provider_tp_win_rate_pct": self.provider_comparison.provider_tp_win_rate_pct,
                "calculated_tp_win_rate_pct": self.provider_comparison.calculated_tp_win_rate_pct,
                "provider_tp_total_r": self.provider_comparison.provider_tp_total_r,
                "calculated_tp_total_r": self.provider_comparison.calculated_tp_total_r,
                "provider_tp_avg_rrr": self.provider_comparison.provider_tp_avg_rrr,
                "calculated_tp_avg_rrr": self.provider_comparison.calculated_tp_avg_rrr,
            },
            "trades_by_symbol": [
                {
                    "symbol": s.symbol,
                    "trades_count": s.trades_count,
                    "closed_trades": s.closed_trades,
                    "wins": s.wins,
                    "losses": s.losses,
                    "win_rate_pct": s.win_rate_pct,
                    "total_r": s.total_r,
                    "net_pnl_usd": s.net_pnl_usd,
                }
                for s in self.trades_by_symbol
            ],
            "trades_by_side": [
                {
                    "side": s.side,
                    "trades_count": s.trades_count,
                    "closed_trades": s.closed_trades,
                    "wins": s.wins,
                    "losses": s.losses,
                    "win_rate_pct": s.win_rate_pct,
                    "total_r": s.total_r,
                    "net_pnl_usd": s.net_pnl_usd,
                }
                for s in self.trades_by_side
            ],
            "trades_by_date": [
                {
                    "date": d.date_str,
                    "trades_count": d.trades_count,
                    "wins": d.wins,
                    "losses": d.losses,
                    "total_r": d.total_r,
                    "net_pnl_usd": d.net_pnl_usd,
                }
                for d in self.trades_by_date
            ],
            "trades_by_hour": [
                {
                    "hour": h.hour,
                    "trades_count": h.trades_count,
                    "total_r": h.total_r,
                    "net_pnl_usd": h.net_pnl_usd,
                }
                for h in self.trades_by_hour
            ],
        }

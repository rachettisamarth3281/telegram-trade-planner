import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Signal, PaperTrade
from app.analytics import TradeJournalAnalyticsService

@pytest.fixture
async def deterministic_analytics_dataset(db_session: AsyncSession):
    """
    Creates a deterministic dataset of 10 signals and 6 paper trades.
    """
    base_time = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Signals (7 Valid, 3 Invalid)
    s1 = Signal(
        id="sig-1",
        raw_message="BUY EURUSD 1.0850 SL 1.0800 TP 1.0950",
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
        status="PAPER_TRADE_CREATED",
        take_profits={"tp_source": "PROVIDER"},
        created_at=base_time,
    )
    s2 = Signal(
        id="sig-2",
        raw_message="BUY EURUSD 1.0850 SL 1.0800 TP 1.0950",
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
        status="PAPER_TRADE_CREATED",
        take_profits={"tp_source": "PROVIDER"},
        created_at=base_time + timedelta(hours=1),
    )
    s3 = Signal(
        id="sig-3",
        raw_message="SELL XAUUSD 4350 SL 4358",
        symbol="XAUUSD",
        side="SELL",
        entry_price=4350.0,
        stop_loss=4358.0,
        status="PAPER_TRADE_CREATED",
        take_profits={"tp_source": "CALCULATED"},
        created_at=base_time + timedelta(hours=2),
    )
    s4 = Signal(
        id="sig-4",
        raw_message="SELL XAUUSD 4350 SL 4358",
        symbol="XAUUSD",
        side="SELL",
        entry_price=4350.0,
        stop_loss=4358.0,
        status="PAPER_TRADE_CREATED",
        take_profits={"tp_source": "CALCULATED"},
        created_at=base_time + timedelta(hours=3),
    )
    s5 = Signal(
        id="sig-5",
        raw_message="BUY XAUUSD 4340 SL 4330 TP 4370",
        symbol="XAUUSD",
        side="BUY",
        entry_price=4340.0,
        stop_loss=4330.0,
        take_profit=4370.0,
        status="PAPER_TRADE_CREATED",
        take_profits={"tp_source": "PROVIDER"},
        created_at=base_time + timedelta(hours=4),
    )
    s6 = Signal(
        id="sig-6",
        raw_message="BUY US30 38000 SL 37900",
        symbol="US30",
        side="BUY",
        entry_price=38000.0,
        stop_loss=37900.0,
        status="PAPER_TRADE_CREATED",
        created_at=base_time + timedelta(hours=5),
    )
    s7 = Signal(
        id="sig-7",
        raw_message="BUY GBPUSD 1.2500 SL 1.2450",
        symbol="GBPUSD",
        side="BUY",
        entry_price=1.2500,
        stop_loss=1.2450,
        status="VALID",
        created_at=base_time + timedelta(hours=6),
    )
    # Invalid Signals
    s8 = Signal(
        id="sig-8",
        raw_message="BUY GOLD 4350",
        status="REJECTED",
        rejection_reason="MISSING_SL; Stop loss is missing",
        created_at=base_time + timedelta(hours=7),
    )
    s9 = Signal(
        id="sig-9",
        raw_message="SELL XAUUSD 4350 SL 4340",
        status="REJECTED",
        rejection_reason="INVALID_SL; Stop loss must be strictly above entry",
        created_at=base_time + timedelta(hours=8),
    )
    s10 = Signal(
        id="sig-10",
        raw_message="BUY UNKNOWNSYMBOL @ 100",
        status="REJECTED",
        rejection_reason="UNSUPPORTED_SYMBOL; Unsupported instrument",
        created_at=base_time + timedelta(hours=9),
    )

    db_session.add_all([s1, s2, s3, s4, s5, s6, s7, s8, s9, s10])
    await db_session.flush()

    # 2. Paper Trades
    # Trade 1: Win (+2R, +$200)
    t1 = PaperTrade(
        id="t-1",
        signal_id=s1.id,
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
        target_r_multiple=2.0,
        position_size=1.0,
        status="TP_HIT",
        exit_price=1.0950,
        exit_reason="TAKE_PROFIT",
        realized_pnl=200.0,
        realized_pips=20.0,
        realized_r=2.0,
        opened_at=base_time,
        closed_at=base_time + timedelta(minutes=30),
    )
    # Trade 2: Win (+2R, +$200)
    t2 = PaperTrade(
        id="t-2",
        signal_id=s2.id,
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
        target_r_multiple=2.0,
        position_size=1.0,
        status="TP_HIT",
        exit_price=1.0950,
        exit_reason="TAKE_PROFIT",
        realized_pnl=200.0,
        realized_pips=20.0,
        realized_r=2.0,
        opened_at=base_time + timedelta(hours=1),
        closed_at=base_time + timedelta(hours=1, minutes=30),
    )
    # Trade 3: Loss (-1R, -$100)
    t3 = PaperTrade(
        id="t-3",
        signal_id=s3.id,
        symbol="XAUUSD",
        side="SELL",
        entry_price=4350.0,
        stop_loss=4358.0,
        take_profit=4334.0,
        target_r_multiple=2.0,
        position_size=1.0,
        status="SL_HIT",
        exit_price=4358.0,
        exit_reason="STOP_LOSS",
        realized_pnl=-100.0,
        realized_pips=-10.0,
        realized_r=-1.0,
        opened_at=base_time + timedelta(hours=2),
        closed_at=base_time + timedelta(hours=2, minutes=30),
    )
    # Trade 4: Loss (-1R, -$100)
    t4 = PaperTrade(
        id="t-4",
        signal_id=s4.id,
        symbol="XAUUSD",
        side="SELL",
        entry_price=4350.0,
        stop_loss=4358.0,
        take_profit=4334.0,
        target_r_multiple=2.0,
        position_size=1.0,
        status="SL_HIT",
        exit_price=4358.0,
        exit_reason="STOP_LOSS",
        realized_pnl=-100.0,
        realized_pips=-10.0,
        realized_r=-1.0,
        opened_at=base_time + timedelta(hours=3),
        closed_at=base_time + timedelta(hours=3, minutes=30),
    )
    # Trade 5: Win (+3R, +$300)
    t5 = PaperTrade(
        id="t-5",
        signal_id=s5.id,
        symbol="XAUUSD",
        side="BUY",
        entry_price=4340.0,
        stop_loss=4330.0,
        take_profit=4370.0,
        target_r_multiple=3.0,
        position_size=1.0,
        status="TP_HIT",
        exit_price=4370.0,
        exit_reason="TAKE_PROFIT",
        realized_pnl=300.0,
        realized_pips=30.0,
        realized_r=3.0,
        opened_at=base_time + timedelta(hours=4),
        closed_at=base_time + timedelta(hours=4, minutes=30),
    )
    # Trade 6: Still Open
    t6 = PaperTrade(
        id="t-6",
        signal_id=s6.id,
        symbol="US30",
        side="BUY",
        entry_price=38000.0,
        stop_loss=37900.0,
        position_size=1.0,
        status="OPEN",
        opened_at=base_time + timedelta(hours=5),
        closed_at=None,
    )

    db_session.add_all([t1, t2, t3, t4, t5, t6])
    await db_session.commit()

@pytest.mark.asyncio
async def test_analytics_signal_and_trade_counts(db_session: AsyncSession, deterministic_analytics_dataset):
    """
    Verify signal counts, trade counts, validity rate, and invalid reasons map.
    """
    report = await TradeJournalAnalyticsService.generate_complete_report(db_session)

    # Signals
    assert report.signals.total_signals == 10
    assert report.signals.valid_signals == 7
    assert report.signals.invalid_signals == 3
    assert report.signals.validity_rate_pct == 70.0
    assert report.signals.invalid_signal_reasons == {
        "MISSING_SL": 1,
        "INVALID_SL": 1,
        "UNSUPPORTED_SYMBOL": 1
    }

    # Trades
    assert report.trades.paper_trades == 6
    assert report.trades.open_trades == 1
    assert report.trades.closed_trades == 5
    assert report.trades.wins == 3
    assert report.trades.losses == 2
    assert report.trades.breakeven == 0
    assert report.trades.win_rate_pct == 60.0

@pytest.mark.asyncio
async def test_analytics_performance_and_drawdown(db_session: AsyncSession, deterministic_analytics_dataset):
    """
    Verify Realized R, Win/Loss Averages, Profit Factor, Streaks, and Max Drawdown.
    """
    report = await TradeJournalAnalyticsService.generate_complete_report(db_session)
    perf = report.performance

    # 1. Total Realized R: 2 + 2 - 1 - 1 + 3 = 5.0R
    assert perf.total_realized_r == 5.0
    # 2. Average R per trade: 5.0 / 5 = 1.0R
    assert perf.average_r_per_trade == 1.0
    # 3. Average Win R: (2 + 2 + 3) / 3 = 2.33R
    assert perf.average_win_r == pytest.approx(2.33, abs=0.01)
    # 4. Average Loss R: (1 + 1) / 2 = 1.0R
    assert perf.average_loss_r == 1.0

    # 5. Profit Factor: $700 / $200 = 3.5
    assert perf.profit_factor == 3.5
    assert perf.net_pnl_usd == 500.0

    # 6. Streaks
    assert perf.max_winning_streak == 2  # Trades 1 & 2
    assert perf.max_losing_streak == 2   # Trades 3 & 4

    # 7. Max Drawdown: Peak was 4.0R (after trade 2), dropped to 2.0R (after trade 4) -> Drawdown = 2.0R ($200)
    assert perf.max_drawdown_r == 2.0
    assert perf.max_drawdown_usd == 200.0

@pytest.mark.asyncio
async def test_analytics_provider_vs_calculated_comparison(db_session: AsyncSession, deterministic_analytics_dataset):
    """
    Verify comparison metrics between Provider TP signals and Calculated TP signals.
    """
    report = await TradeJournalAnalyticsService.generate_complete_report(db_session)
    comp = report.provider_comparison

    # Provider TP: 3 trades (all won: +2, +2, +3 = +7.0R)
    assert comp.provider_tp_trades_count == 3
    assert comp.provider_tp_win_rate_pct == 100.0
    assert comp.provider_tp_total_r == 7.0

    # Calculated TP: 2 trades (both lost: -1, -1 = -2.0R)
    assert comp.calculated_tp_trades_count == 3  # (t3, t4 closed, and t6 open)
    assert comp.calculated_tp_win_rate_pct == 0.0
    assert comp.calculated_tp_total_r == -2.0

@pytest.mark.asyncio
async def test_analytics_symbol_side_and_date_breakdowns(db_session: AsyncSession, deterministic_analytics_dataset):
    """
    Verify symbol, side, date, and hour breakdowns.
    """
    report = await TradeJournalAnalyticsService.generate_complete_report(db_session)

    # By Symbol
    sym_map = {s.symbol: s for s in report.trades_by_symbol}
    assert "EURUSD" in sym_map
    assert sym_map["EURUSD"].total_r == 4.0
    assert sym_map["EURUSD"].win_rate_pct == 100.0

    assert "XAUUSD" in sym_map
    assert sym_map["XAUUSD"].total_r == 1.0  # -1 - 1 + 3 = 1.0R
    assert sym_map["XAUUSD"].win_rate_pct == pytest.approx(33.33, abs=0.01)

    # By Side
    side_map = {s.side: s for s in report.trades_by_side}
    assert side_map["BUY"].total_r == 7.0   # 2 + 2 + 3
    assert side_map["SELL"].total_r == -2.0 # -1 - 1

    # By Date
    assert len(report.trades_by_date) == 1
    assert report.trades_by_date[0].date_str == "2026-09-21"
    assert report.trades_by_date[0].total_r == 5.0

    # Serialization
    d = report.to_dict()
    assert d["signals"]["total_signals"] == 10
    assert d["performance"]["profit_factor"] == 3.5

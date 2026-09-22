import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Signal, PaperTrade, PriceSnapshot, TradeEvent
from app.market_data import MockMarketDataProvider, TickData, CandleData, PriceSnapshotService
from app.paper_trading import (
    PaperTradeEngine,
    PriceMonitor,
    CandleExecutionPolicy,
    TradeStatus,
    ExitReason,
)

@pytest.mark.asyncio
async def test_price_monitor_tick_triggers_buy_tp(db_session: AsyncSession):
    """
    Test PriceMonitor receiving live tick and closing BUY trade at TP.
    """
    signal = Signal(
        raw_message="BUY EURUSD 1.0850 SL 1.0800 TP 1.0950",
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
        status="VALID",
    )
    db_session.add(signal)
    await db_session.commit()

    engine = PaperTradeEngine()
    trade = await engine.create_paper_trade(db_session, signal)
    assert trade.status == TradeStatus.OPEN.value

    provider = MockMarketDataProvider()
    monitor = PriceMonitor(market_data_provider=provider, paper_trade_engine=engine)

    # Inject winning tick
    tick = await provider.simulate_tick("EURUSD", bid=1.0950, ask=1.0952)
    closed = await monitor.on_tick_received(db_session, tick)

    assert len(closed) == 1
    assert closed[0].status == TradeStatus.TP_HIT.value
    assert closed[0].exit_reason == ExitReason.TAKE_PROFIT.value
    assert closed[0].realized_r == pytest.approx(2.0, abs=0.05)

@pytest.mark.asyncio
async def test_candle_dual_breach_conservative_policy(db_session: AsyncSession):
    """
    Test candle touching BOTH SL and TP under CONSERVATIVE policy:
    - BUY EURUSD: Entry = 1.0850, SL = 1.0800, TP = 1.0950
    - Wide candle: Low = 1.0790 (<= SL), High = 1.0960 (>= TP)
    - CONSERVATIVE policy must close at SL and record AMBIGUOUS_CANDLE_EVALUATION event.
    """
    signal = Signal(
        raw_message="BUY EURUSD 1.0850 SL 1.0800 TP 1.0950",
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
    )
    db_session.add(signal)
    await db_session.commit()

    engine = PaperTradeEngine()
    trade = await engine.create_paper_trade(db_session, signal)

    provider = MockMarketDataProvider()
    monitor = PriceMonitor(
        market_data_provider=provider,
        paper_trade_engine=engine,
        candle_policy=CandleExecutionPolicy.CONSERVATIVE
    )

    candle = CandleData(
        symbol="EURUSD",
        open=1.0850,
        high=1.0960,  # Touches TP
        low=1.0790,   # Touches SL
        close=1.0900,
        volume=500.0
    )

    evaluated = await monitor.evaluate_candle(db_session, trade, candle)

    assert evaluated.status == TradeStatus.SL_HIT.value
    assert evaluated.exit_reason == ExitReason.STOP_LOSS.value
    assert evaluated.realized_r == pytest.approx(-1.0, abs=0.05)

    # Verify ambiguity audit event was recorded
    events_stmt = select(TradeEvent).where(
        TradeEvent.paper_trade_id == trade.id,
        TradeEvent.event_type == "AMBIGUOUS_CANDLE_EVALUATION"
    )
    events = (await db_session.scalars(events_stmt)).all()
    assert len(events) == 1
    assert events[0].details.get("is_ambiguous") is True
    assert "Both SL and TP touched" in events[0].details.get("ambiguity_note", "")

@pytest.mark.asyncio
async def test_candle_dual_breach_tp_first_policy(db_session: AsyncSession):
    """
    Test candle touching BOTH SL and TP under TP_FIRST policy:
    - Closes at TP.
    """
    signal = Signal(
        raw_message="BUY EURUSD 1.0850 SL 1.0800 TP 1.0950",
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
    )
    db_session.add(signal)
    await db_session.commit()

    engine = PaperTradeEngine()
    trade = await engine.create_paper_trade(db_session, signal)

    provider = MockMarketDataProvider()
    monitor = PriceMonitor(
        market_data_provider=provider,
        paper_trade_engine=engine,
        candle_policy=CandleExecutionPolicy.TP_FIRST
    )

    candle = CandleData(
        symbol="EURUSD",
        open=1.0850,
        high=1.0960,
        low=1.0790,
        close=1.0900,
    )

    evaluated = await monitor.evaluate_candle(db_session, trade, candle)

    assert evaluated.status == TradeStatus.TP_HIT.value
    assert evaluated.exit_reason == ExitReason.TAKE_PROFIT.value
    assert evaluated.realized_r == pytest.approx(2.0, abs=0.05)

@pytest.mark.asyncio
async def test_stale_price_detection():
    """
    Test that prices with older source timestamps are flagged as stale.
    """
    provider = MockMarketDataProvider(stale_threshold_seconds=10.0)

    old_time = datetime.now(timezone.utc) - timedelta(seconds=25)
    tick = await provider.simulate_tick("XAUUSD", bid=4350.0, ask=4350.5, source_timestamp=old_time)

    assert tick.is_stale is True

@pytest.mark.asyncio
async def test_price_snapshot_throttling(db_session: AsyncSession):
    """
    Test that high frequency ticks are throttled from generating excessive DB writes.
    """
    snapshot_service = PriceSnapshotService(interval_seconds=2.0)
    provider = MockMarketDataProvider()

    now = datetime.now(timezone.utc)
    tick1 = TickData(symbol="XAUUSD", bid=4350.0, ask=4350.5, timestamp=now)
    snap1 = await snapshot_service.record_snapshot(db_session, tick1)
    assert snap1 is not None

    # Immediate next tick within interval should be throttled
    tick2 = TickData(symbol="XAUUSD", bid=4350.2, ask=4350.7, timestamp=now + timedelta(milliseconds=100))
    snap2 = await snapshot_service.record_snapshot(db_session, tick2)
    assert snap2 is None

    # Tick after 3 seconds should be recorded
    tick3 = TickData(symbol="XAUUSD", bid=4351.0, ask=4351.5, timestamp=now + timedelta(seconds=3))
    snap3 = await snapshot_service.record_snapshot(db_session, tick3)
    assert snap3 is not None

    # Verify database records
    count = len((await db_session.scalars(select(PriceSnapshot))).all())
    assert count == 2

@pytest.mark.asyncio
async def test_provider_reconnection_and_error_handling():
    """
    Test provider error handling and disconnect/connect lifecycle.
    """
    provider = MockMarketDataProvider()
    assert await provider.is_connected() is True

    await provider.disconnect()
    assert await provider.is_connected() is False
    assert await provider.get_current_price("EURUSD") is None

    await provider.connect()
    assert await provider.is_connected() is True

    # Error injection
    provider.simulate_error_on_next_call = True
    with pytest.raises(ConnectionError):
        await provider.get_current_price("EURUSD")

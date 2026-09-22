import pytest
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Signal, PaperTrade
from app.paper_trading import (
    PaperTradeEngine,
    PaperTradeConfig,
    PositionSizingConfig,
    PositionSizingMode,
    PositionSizingService,
    TradeStatus,
    ExitReason,
)
from app.market_data import SimulatedMarketDataProvider, TickData

@pytest.mark.asyncio
async def test_buy_tp_hit(db_session: AsyncSession):
    """
    Test BUY Paper Trade hitting Take Profit:
    - BUY EURUSD @ 1.0850, SL = 1.0800, TP = 1.0950 (Risk = 0.0050, 2R)
    - Tick bid = 1.0950
    - Status -> TP_HIT, Exit Reason -> TAKE_PROFIT, Realized R -> ~ +2.0
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
    assert trade.entry_price == 1.0850
    assert trade.risk_distance == pytest.approx(0.0050)
    assert trade.opened_at is not None

    # Price hits TP
    evaluated = await engine.evaluate_tick(db_session, trade, current_bid=1.0950, current_ask=1.0952)

    assert evaluated.status == TradeStatus.TP_HIT.value
    assert evaluated.exit_reason == ExitReason.TAKE_PROFIT.value
    assert evaluated.exit_price == 1.0950
    assert evaluated.realized_pnl > 0
    assert evaluated.realized_r == pytest.approx(2.0, abs=0.05)

@pytest.mark.asyncio
async def test_buy_sl_hit(db_session: AsyncSession):
    """
    Test BUY Paper Trade hitting Stop Loss:
    - BUY EURUSD @ 1.0850, SL = 1.0800, TP = 1.0950
    - Tick bid = 1.0800
    - Status -> SL_HIT, Exit Reason -> STOP_LOSS, Realized R -> ~ -1.0
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

    # Price hits SL
    evaluated = await engine.evaluate_tick(db_session, trade, current_bid=1.0800, current_ask=1.0802)

    assert evaluated.status == TradeStatus.SL_HIT.value
    assert evaluated.exit_reason == ExitReason.STOP_LOSS.value
    assert evaluated.exit_price == 1.0800
    assert evaluated.realized_pnl < 0
    assert evaluated.realized_r == pytest.approx(-1.0, abs=0.05)

@pytest.mark.asyncio
async def test_sell_tp_hit(db_session: AsyncSession):
    """
    Test SELL Paper Trade hitting Take Profit:
    - SELL XAUUSD @ 4350.53, SL = 4358.00, TP = 4335.59 (Risk = 7.47, 2R)
    - Tick ask = 4335.59
    - Status -> TP_HIT, Exit Reason -> TAKE_PROFIT, Realized R -> ~ +2.0
    """
    signal = Signal(
        raw_message="SELL XAUUSD 4350.53 SL 4358 TP 4335.59",
        symbol="XAUUSD",
        side="SELL",
        entry_price=4350.53,
        stop_loss=4358.00,
        take_profit=4335.59,
        status="VALID",
    )
    db_session.add(signal)
    await db_session.commit()

    engine = PaperTradeEngine()
    trade = await engine.create_paper_trade(db_session, signal)

    assert trade.status == TradeStatus.OPEN.value
    assert trade.risk_distance == pytest.approx(7.47)

    # Price reaches TP for SELL (ask drops to TP)
    evaluated = await engine.evaluate_tick(db_session, trade, current_bid=4335.55, current_ask=4335.59)

    assert evaluated.status == TradeStatus.TP_HIT.value
    assert evaluated.exit_reason == ExitReason.TAKE_PROFIT.value
    assert evaluated.exit_price == 4335.59
    assert evaluated.realized_pnl > 0
    assert evaluated.realized_r == pytest.approx(2.0, abs=0.05)

@pytest.mark.asyncio
async def test_sell_sl_hit(db_session: AsyncSession):
    """
    Test SELL Paper Trade hitting Stop Loss:
    - SELL XAUUSD @ 4350.53, SL = 4358.00, TP = 4335.59
    - Tick ask = 4358.00
    - Status -> SL_HIT, Exit Reason -> STOP_LOSS, Realized R -> ~ -1.0
    """
    signal = Signal(
        raw_message="SELL XAUUSD 4350.53 SL 4358 TP 4335.59",
        symbol="XAUUSD",
        side="SELL",
        entry_price=4350.53,
        stop_loss=4358.00,
        take_profit=4335.59,
        status="VALID",
    )
    db_session.add(signal)
    await db_session.commit()

    engine = PaperTradeEngine()
    trade = await engine.create_paper_trade(db_session, signal)

    # Price rises to SL for SELL
    evaluated = await engine.evaluate_tick(db_session, trade, current_bid=4357.90, current_ask=4358.00)

    assert evaluated.status == TradeStatus.SL_HIT.value
    assert evaluated.exit_reason == ExitReason.STOP_LOSS.value
    assert evaluated.exit_price == 4358.00
    assert evaluated.realized_pnl < 0
    assert evaluated.realized_r == pytest.approx(-1.0, abs=0.05)

@pytest.mark.asyncio
async def test_invalid_trade_zero_or_negative_risk(db_session: AsyncSession):
    """
    Test that invalid geometry (e.g. BUY where SL >= Entry) is marked INVALID and not opened.
    """
    signal = Signal(
        raw_message="BUY XAUUSD 4350 SL 4355",  # SL above BUY entry
        symbol="XAUUSD",
        side="BUY",
        entry_price=4350.0,
        stop_loss=4355.0,
        status="INVALID",
    )
    db_session.add(signal)
    await db_session.commit()

    engine = PaperTradeEngine()
    trade = await engine.create_paper_trade(db_session, signal)

    assert trade.status == TradeStatus.INVALID.value
    assert trade.exit_reason == ExitReason.INVALID.value
    assert trade.position_size == 0.0

@pytest.mark.asyncio
async def test_duplicate_trade_idempotency(db_session: AsyncSession):
    """
    Creating a paper trade twice for the same signal must return the existing trade.
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
    trade1 = await engine.create_paper_trade(db_session, signal)
    trade2 = await engine.create_paper_trade(db_session, signal)

    assert trade1.id == trade2.id

@pytest.mark.asyncio
async def test_partial_data_missing_sl(db_session: AsyncSession):
    """
    Signals with missing SL must be marked INVALID in trade engine without fabricating SL.
    """
    signal = Signal(
        raw_message="BUY EURUSD 1.0850",
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        stop_loss=None,
    )
    db_session.add(signal)
    await db_session.commit()

    engine = PaperTradeEngine()
    trade = await engine.create_paper_trade(db_session, signal)

    assert trade.status == TradeStatus.INVALID.value
    assert trade.position_size == 0.0

def test_position_sizing_service_fixed_lot():
    """
    Test FIXED_LOT position sizing.
    """
    service = PositionSizingService()
    cfg = PositionSizingConfig(mode=PositionSizingMode.FIXED_LOT, fixed_lot=Decimal("0.50"))

    result = service.calculate_position_size(
        symbol="XAUUSD",
        risk_distance=Decimal("7.47"),
        config=cfg,
    )

    assert result.position_size == Decimal("0.50")
    # Gold contract size = 100 -> monetary risk per unit = 7.47 * 100 = 747.0
    # Risk amount = 0.50 * 747.0 = 373.50
    assert result.risk_amount == Decimal("373.50")

def test_position_sizing_service_fixed_risk_amount():
    """
    Test FIXED_RISK_AMOUNT with variable broker contract sizes.
    """
    # 1. Standard broker: 100 oz per Gold lot
    service_std = PositionSizingService()
    cfg = PositionSizingConfig(
        mode=PositionSizingMode.FIXED_RISK_AMOUNT,
        fixed_risk_amount=Decimal("100.00"),
        position_size_step=Decimal("0.01"),
    )

    # Risk distance = 10.0. Contract size = 100 -> Risk per lot = $1000.
    # Lots = 100 / 1000 = 0.10 lots.
    res_std = service_std.calculate_position_size(
        symbol="XAUUSD",
        risk_distance=Decimal("10.00"),
        config=cfg,
    )
    assert res_std.position_size == Decimal("0.10")
    assert res_std.risk_amount == Decimal("100.00")

    # 2. Mini broker: 10 oz per Gold lot
    service_mini = PositionSizingService(custom_contract_sizes={"XAUUSD": Decimal("10.0")})
    # Risk distance = 10.0. Contract size = 10 -> Risk per lot = $100.
    # Lots = 100 / 100 = 1.00 lot.
    res_mini = service_mini.calculate_position_size(
        symbol="XAUUSD",
        risk_distance=Decimal("10.00"),
        config=cfg,
    )
    assert res_mini.position_size == Decimal("1.00")
    assert res_mini.risk_amount == Decimal("100.00")

@pytest.mark.asyncio
async def test_simulated_market_data_provider():
    """
    Test SimulatedMarketDataProvider tick injection and subscriber callbacks.
    """
    provider = SimulatedMarketDataProvider()
    received_ticks = []

    async def on_tick(tick: TickData):
        received_ticks.append(tick)

    await provider.subscribe_ticks("EURUSD", on_tick)

    tick = await provider.simulate_tick("EURUSD", bid=1.0850, ask=1.0852)
    latest = await provider.get_latest_price("EURUSD")

    assert latest is not None
    assert latest.bid == 1.0850
    assert latest.ask == 1.0852
    assert latest.mid == pytest.approx(1.0851)
    assert len(received_ticks) == 1
    assert received_ticks[0].bid == 1.0850

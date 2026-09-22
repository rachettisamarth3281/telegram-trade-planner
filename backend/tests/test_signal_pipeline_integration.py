import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Signal, PaperTrade, SystemEvent, TradeEvent
from app.signals import (
    SignalPipelineService,
    PipelineProcessRequest,
    DecisionReason,
)
from app.market_data import MockMarketDataProvider
from app.paper_trading import PriceMonitor, TradeStatus, ExitReason

@pytest.mark.asyncio
async def test_prompt_benchmark_pipeline_sell_gold(db_session: AsyncSession):
    """
    Test exact prompt benchmark scenario through the complete pipeline:
    Original:
    "Sell gold @ 4350.53
    SL 4358"

    Expected Result:
    symbol = XAUUSD
    side = SELL
    entry = 4350.53
    sl = 4358
    provider_tp = None
    calculated_tp = 4335.59
    tp_source = CALCULATED
    risk = 7.47
    rr = 2.0
    status = PAPER_TRADE_CREATED
    """
    raw_text = "Sell gold @ 4350.53\nSL 4358"
    pipeline = SignalPipelineService()

    request = PipelineProcessRequest(
        raw_text=raw_text,
        telegram_message_id=101,
        source_chat_id="-100998877",
        source_chat_title="Gold Signals VIP",
    )

    result = await pipeline.process_message(db_session, request)

    # 1. Verify Pipeline Execution Result fields
    assert result.symbol == "XAUUSD"
    assert result.side == "SELL"
    assert result.entry_price == 4350.53
    assert result.stop_loss == 4358.0
    assert result.provider_tp is None
    assert result.calculated_tp == 4335.59
    assert result.tp_source == "CALCULATED"
    assert result.risk_distance == 7.47
    assert result.risk_reward_ratio == 2.0
    assert result.status == "PAPER_TRADE_CREATED"
    assert result.decision_reason == DecisionReason.PAPER_TRADE_CREATED
    assert result.is_paper_trade_created is True
    assert result.trade_id is not None

    # 2. Verify Database Persistence (Original message preserved)
    signal = await db_session.get(Signal, result.signal_id)
    assert signal is not None
    assert signal.raw_message == raw_text
    assert signal.symbol == "XAUUSD"
    assert signal.side == "SELL"
    assert signal.entry_price == 4350.53
    assert signal.stop_loss == 4358.0
    assert signal.take_profit == 4335.59
    assert signal.status == "PAPER_TRADE_CREATED"

    # 3. Verify Created Paper Trade
    trade = await db_session.get(PaperTrade, result.trade_id)
    assert trade is not None
    assert trade.symbol == "XAUUSD"
    assert trade.side == "SELL"
    assert trade.entry_price == 4350.53
    assert trade.stop_loss == 4358.0
    assert trade.take_profit == 4335.59
    assert trade.status == TradeStatus.OPEN.value
    assert trade.risk_distance == pytest.approx(7.47)

    # 4. Verify System Audit Event
    stmt = select(SystemEvent).where(
        SystemEvent.component == "signal_pipeline",
        SystemEvent.event_type == "SIGNAL_PROCESSED"
    )
    events = (await db_session.scalars(stmt)).all()
    assert len(events) >= 1
    assert events[-1].payload.get("decision_reason") == "PAPER_TRADE_CREATED"

@pytest.mark.asyncio
async def test_buy_pipeline_with_provider_tp(db_session: AsyncSession):
    """
    Test BUY pipeline with provider TP:
    "BUY EURUSD 1.0850 SL 1.0800 TP 1.0950"
    """
    raw_text = "BUY EURUSD 1.0850 SL 1.0800 TP 1.0950"
    pipeline = SignalPipelineService()

    request = PipelineProcessRequest(
        raw_text=raw_text,
        telegram_message_id=202,
        source_chat_id="-100112233",
    )

    result = await pipeline.process_message(db_session, request)

    assert result.symbol == "EURUSD"
    assert result.side == "BUY"
    assert result.entry_price == 1.0850
    assert result.stop_loss == 1.0800
    assert result.provider_tp == 1.0950
    assert result.tp_source == "PROVIDER"
    assert result.risk_distance == pytest.approx(0.0050)
    assert result.risk_reward_ratio == 2.0
    assert result.decision_reason == DecisionReason.PAPER_TRADE_CREATED
    assert result.is_paper_trade_created is True

@pytest.mark.asyncio
async def test_pipeline_missing_sl_rejection(db_session: AsyncSession):
    """
    Signal without SL must be rejected under zero-assumption policy with MISSING_SL reason.
    Original signal must still be preserved in database.
    """
    raw_text = "BUY GOLD 4350"
    pipeline = SignalPipelineService()

    request = PipelineProcessRequest(
        raw_text=raw_text,
        telegram_message_id=303,
        source_chat_id="-100998877",
    )

    result = await pipeline.process_message(db_session, request)

    assert result.decision_reason in (DecisionReason.MISSING_SL, DecisionReason.WAITING_FOR_SL)
    assert result.is_paper_trade_created is False
    assert result.trade_id is None
    assert result.status in ("REJECTED", "WAITING_FOR_DETAILS")

    # Verify Signal preserved in DB
    signal = await db_session.get(Signal, result.signal_id)
    assert signal is not None
    assert signal.raw_message == raw_text
    assert signal.status in ("REJECTED", "WAITING_FOR_DETAILS")

@pytest.mark.asyncio
async def test_pipeline_invalid_sl_geometry(db_session: AsyncSession):
    """
    SELL signal where SL is below entry must be rejected with INVALID_SL.
    """
    raw_text = "SELL XAUUSD 4350.00 SL 4340.00"
    pipeline = SignalPipelineService()

    request = PipelineProcessRequest(
        raw_text=raw_text,
        telegram_message_id=404,
        source_chat_id="-100998877",
    )

    result = await pipeline.process_message(db_session, request)

    assert result.decision_reason == DecisionReason.INVALID_SL
    assert result.is_paper_trade_created is False
    assert result.status == "REJECTED"

@pytest.mark.asyncio
async def test_pipeline_unsupported_symbol(db_session: AsyncSession):
    """
    Unrecognized or unsupported instruments must be rejected with UNSUPPORTED_SYMBOL.
    """
    raw_text = "BUY UNKNOWNSYMBOL @ 100 SL 90"
    pipeline = SignalPipelineService()

    request = PipelineProcessRequest(
        raw_text=raw_text,
        telegram_message_id=505,
        source_chat_id="-100998877",
    )

    result = await pipeline.process_message(db_session, request)

    assert result.decision_reason == DecisionReason.UNSUPPORTED_SYMBOL
    assert result.is_paper_trade_created is False

@pytest.mark.asyncio
async def test_pipeline_duplicate_signal_idempotency(db_session: AsyncSession):
    """
    Ingesting the same Telegram message twice must return DUPLICATE_SIGNAL on second attempt.
    """
    raw_text = "BUY EURUSD 1.0850 SL 1.0800 TP 1.0950"
    pipeline = SignalPipelineService()

    req = PipelineProcessRequest(
        raw_text=raw_text,
        telegram_message_id=888,
        source_chat_id="-100777",
    )

    res1 = await pipeline.process_message(db_session, req)
    assert res1.decision_reason == DecisionReason.PAPER_TRADE_CREATED

    # Second ingestion of the exact same message
    res2 = await pipeline.process_message(db_session, req)
    assert res2.decision_reason == DecisionReason.DUPLICATE_SIGNAL
    assert res2.signal_id == res1.signal_id
    assert res2.trade_id == res1.trade_id

@pytest.mark.asyncio
async def test_full_pipeline_end_to_end_with_market_closure(db_session: AsyncSession):
    """
    Complete end-to-end integration:
    Telegram Signal -> Ingestion -> Parser -> Risk Calc -> Paper Trade -> Market Price Monitor -> Trade Closure.
    """
    # 1. Signal Ingestion & Trade Creation
    raw_text = "Sell gold @ 4350.53\nSL 4358"
    pipeline = SignalPipelineService()

    request = PipelineProcessRequest(
        raw_text=raw_text,
        telegram_message_id=999,
        source_chat_id="-100998877",
    )

    result = await pipeline.process_message(db_session, request)
    assert result.is_paper_trade_created is True
    trade_id = result.trade_id

    # 2. Market Monitoring Setup
    provider = MockMarketDataProvider()
    monitor = PriceMonitor(market_data_provider=provider)

    # 3. Inject Winning Market Tick (Price drops to 2R TP = 4335.59 for SELL)
    tick = await provider.simulate_tick("XAUUSD", bid=4335.50, ask=4335.59)
    closed_trades = await monitor.on_tick_received(db_session, tick)

    # 4. Verify Trade Closure
    assert len(closed_trades) == 1
    closed_trade = closed_trades[0]
    assert closed_trade.id == trade_id
    assert closed_trade.status == TradeStatus.TP_HIT.value
    assert closed_trade.exit_reason == ExitReason.TAKE_PROFIT.value
    assert closed_trade.exit_price == 4335.59
    assert closed_trade.realized_pnl > 0
    assert closed_trade.realized_r == pytest.approx(2.0, abs=0.05)

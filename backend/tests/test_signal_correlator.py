import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from app.database.session import AsyncSessionLocal, init_db
from app.signals.correlator import SignalCorrelator
from app.signals.models import PipelineProcessRequest
from app.signals.enums import DecisionReason
from app.database.models import Signal, PaperTrade
from sqlalchemy import select
from sqlalchemy.orm import selectinload

@pytest.mark.asyncio
async def test_correlate_separate_entry_and_sl_messages():
    await init_db()
    correlator = SignalCorrelator()

    async with AsyncSessionLocal() as db:
        chat_id = "test_chat_corr_1"

        # 1. First Message: Entry Zone
        req1 = PipelineProcessRequest(
            raw_text="Buy gold @ 4401_4398",
            telegram_message_id=9001,
            source_chat_id=chat_id
        )
        res1 = await correlator.correlate_and_process(db, req1)
        assert res1.is_paper_trade_created is False
        assert res1.decision_reason == DecisionReason.WAITING_FOR_SL
        assert res1.status == "WAITING_FOR_DETAILS"

        # 2. Second Message 1 minute later: Separate SL
        req2 = PipelineProcessRequest(
            raw_text="SL 4393",
            telegram_message_id=9002,
            source_chat_id=chat_id
        )
        res2 = await correlator.correlate_and_process(db, req2)
        assert res2.is_paper_trade_created is True
        assert res2.decision_reason == DecisionReason.PAPER_TRADE_CREATED
        assert res2.stop_loss == 4393.0
        assert res2.symbol == "XAUUSD"
        assert res2.side == "BUY"

@pytest.mark.asyncio
async def test_correlate_targets_and_risk_free_management():
    await init_db()
    correlator = SignalCorrelator()

    async with AsyncSessionLocal() as db:
        chat_id = "test_chat_corr_2"

        # 1. Entry + SL (Sell Gold)
        req1 = PipelineProcessRequest(
            raw_text="Sell gold @ 4350_53\nSL 4358",
            telegram_message_id=9010,
            source_chat_id=chat_id
        )
        res1 = await correlator.correlate_and_process(db, req1)
        assert res1.is_paper_trade_created is True
        trade_id = res1.trade_id

        # 2. Target Update message
        req2 = PipelineProcessRequest(
            raw_text="Target 🎯 \n\n4343\n\n4335\n\n4328",
            telegram_message_id=9011,
            source_chat_id=chat_id
        )
        res2 = await correlator.correlate_and_process(db, req2)
        assert res2.decision_reason == DecisionReason.TRADE_UPDATED

        # 3. Risk Free Management message
        req3 = PipelineProcessRequest(
            raw_text="Risk free",
            telegram_message_id=9012,
            source_chat_id=chat_id
        )
        res3 = await correlator.correlate_and_process(db, req3)
        assert res3.decision_reason == DecisionReason.TRADE_UPDATED

        # Verify trade in database has SL moved to Entry (Break-even)
        trade = await db.scalar(select(PaperTrade).where(PaperTrade.id == trade_id))
        assert trade.is_risk_free_moved is True
        assert trade.stop_loss == trade.entry_price

@pytest.mark.asyncio
async def test_correlate_provider_outcome_pips():
    await init_db()
    correlator = SignalCorrelator()

    async with AsyncSessionLocal() as db:
        chat_id = "test_chat_corr_3"

        req1 = PipelineProcessRequest(
            raw_text="Buy gold @ 4581_78\nSL 4573",
            telegram_message_id=9020,
            source_chat_id=chat_id
        )
        res1 = await correlator.correlate_and_process(db, req1)
        trade_id = res1.trade_id

        # Outcome claims
        await correlator.correlate_and_process(db, PipelineProcessRequest(raw_text="30 pips ✅", telegram_message_id=9021, source_chat_id=chat_id))
        await correlator.correlate_and_process(db, PipelineProcessRequest(raw_text="70 pips ✅🔥🔥", telegram_message_id=9022, source_chat_id=chat_id))
        await correlator.correlate_and_process(db, PipelineProcessRequest(raw_text="120 pips done ✅🔥🔥", telegram_message_id=9023, source_chat_id=chat_id))

        trade = await db.scalar(select(PaperTrade).where(PaperTrade.id == trade_id))
        assert trade.provider_claimed_pips == 120.0

@pytest.mark.asyncio
async def test_ambiguous_continuation_when_no_pending_signal():
    await init_db()
    correlator = SignalCorrelator()

    async with AsyncSessionLocal() as db:
        chat_id = "test_chat_corr_4"
        req = PipelineProcessRequest(
            raw_text="SL 4358",
            telegram_message_id=9030,
            source_chat_id=chat_id
        )
        res = await correlator.correlate_and_process(db, req)
        assert res.is_paper_trade_created is False
        assert res.decision_reason == DecisionReason.AMBIGUOUS_CONTINUATION


import pytest
from datetime import datetime, timezone
from sqlalchemy import select, func

from app.database import init_db, AsyncSessionLocal
from app.database.models import Signal, SystemEvent
from app.telegram.schemas import RawTelegramMessage
from app.telegram.ingestion_service import telegram_ingestion_service

@pytest.fixture(autouse=True)
async def setup_database():
    await init_db()

@pytest.mark.asyncio
async def test_ingest_valid_telegram_message_stores_exact_fields():
    raw = RawTelegramMessage(
        message_id=5001,
        chat_id="-1009988776655",
        chat_title="Gold VIP Signals",
        sender_id="user_88",
        sender_username="trader_joe",
        text="Sell gold @ 4350.53\nSL 4358",
        telegram_timestamp=datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc),
        source="TEST_SUITE"
    )

    result = await telegram_ingestion_service.ingest_message(raw)
    assert result.status == "INGESTED"
    assert result.signal_id is not None
    assert result.message_id == 5001
    assert result.chat_id == "-1009988776655"

    # Verify exact database record
    async with AsyncSessionLocal() as session:
        signal = await session.get(Signal, result.signal_id)
        assert signal is not None
        assert signal.telegram_message_id == 5001
        assert signal.source_chat_id == "-1009988776655"
        assert signal.source_chat_title == "Gold VIP Signals"
        assert signal.sender_id == "user_88"
        assert signal.sender_username == "trader_joe"
        assert signal.raw_message == "Sell gold @ 4350.53\nSL 4358"
        assert signal.status == "RECEIVED"
        assert signal.received_at is not None
        assert signal.created_at is not None

        # Verify audit system event was recorded
        sys_event_res = await session.execute(
            select(SystemEvent).where(SystemEvent.event_type == "MESSAGE_INGESTED")
        )
        sys_event = sys_event_res.scalars().first()
        assert sys_event is not None
        assert sys_event.component == "telegram_ingestion"

@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_signal_creation():
    raw = RawTelegramMessage(
        message_id=7777,
        chat_id="-1001122334455",
        chat_title="Forex VIP",
        text="BUY EURUSD @ 1.0850 SL 1.0800 TP 1.0950"
    )

    # First ingestion
    first_res = await telegram_ingestion_service.ingest_message(raw)
    assert first_res.status == "INGESTED"
    signal_id = first_res.signal_id

    # Second ingestion of the exact same message
    second_res = await telegram_ingestion_service.ingest_message(raw)
    assert second_res.status == "DUPLICATE"
    assert second_res.signal_id == signal_id
    assert "already exists" in second_res.reason

    # Verify database still only has 1 record for this message
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.source_chat_id == "-1001122334455",
                Signal.telegram_message_id == 7777
            )
        )
        assert count == 1

@pytest.mark.asyncio
async def test_ingest_ignored_message_does_not_persist_signal():
    raw = RawTelegramMessage(
        message_id=8888,
        chat_id="-1001122334455",
        text=None,
        has_media=True
    )

    result = await telegram_ingestion_service.ingest_message(raw)
    assert result.status == "IGNORED"
    assert result.reason == "MEDIA_WITHOUT_TEXT_CAPTION"

    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.source_chat_id == "-1001122334455",
                Signal.telegram_message_id == 8888
            )
        )
        assert count == 0


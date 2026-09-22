import logging
from datetime import datetime, timezone
from typing import Optional, Callable, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models.signal import Signal
from app.database.models.system_event import SystemEvent
from app.database.session import AsyncSessionLocal
from app.telegram.schemas import RawTelegramMessage, TelegramIngestionEvent, IngestionResult
from app.telegram.filter import TelegramMessageFilter
from app.utils.logging import get_logger

logger = get_logger("app.telegram.ingestion")

class TelegramIngestionService:
    """
    Core Ingestion Service for processing and persisting raw Telegram signals.
    Enforces idempotency, message filtering, and audit trail generation.
    """

    def __init__(self):
        self._listeners: List[Callable[[TelegramIngestionEvent], None]] = []

    def register_pipeline_listener(self, callback: Callable[[TelegramIngestionEvent], None]):
        """Register downstream pipeline listeners (e.g. parser service when active in Phase 3)."""
        self._listeners.append(callback)

    async def ingest_message(
        self,
        raw: RawTelegramMessage,
        db: Optional[AsyncSession] = None
    ) -> IngestionResult:
        """
        Processes an incoming Telegram message through filtering, deduplication, and persistence.
        """
        received_at = datetime.now(timezone.utc)

        # 1. Evaluate message filter rules
        is_acceptable, rejection_reason = TelegramMessageFilter.evaluate(raw)
        if not is_acceptable:
            logger.info(
                "TELEGRAM_MESSAGE_IGNORED",
                extra={
                    "event_type": "TELEGRAM_MESSAGE_IGNORED",
                    "chat_id": raw.chat_id,
                    "message_id": raw.message_id,
                    "reason": rejection_reason
                }
            )
            return IngestionResult(
                status="IGNORED",
                reason=rejection_reason,
                message_id=raw.message_id,
                chat_id=raw.chat_id
            )

        # Handle DB session lifecycle
        if db is not None:
            return await self._process_persistence(raw, received_at, db)
        else:
            async with AsyncSessionLocal() as session:
                return await self._process_persistence(raw, received_at, session)

    async def _process_persistence(
        self,
        raw: RawTelegramMessage,
        received_at: datetime,
        session: AsyncSession
    ) -> IngestionResult:
        """Internal worker executing the idempotent database write."""
        # 2. Check Idempotency (prevent duplicate processing of the same message)
        stmt = select(Signal).where(
            Signal.source_chat_id == str(raw.chat_id),
            Signal.telegram_message_id == raw.message_id
        )
        result = await session.execute(stmt)
        existing_signal = result.scalar_one_or_none()

        if existing_signal:
            logger.warning(
                "TELEGRAM_MESSAGE_DUPLICATE",
                extra={
                    "event_type": "TELEGRAM_MESSAGE_DUPLICATE",
                    "chat_id": raw.chat_id,
                    "message_id": raw.message_id,
                    "existing_signal_id": existing_signal.id
                }
            )
            return IngestionResult(
                status="DUPLICATE",
                signal_id=existing_signal.id,
                reason=f"Message ID {raw.message_id} from chat {raw.chat_id} already exists.",
                message_id=raw.message_id,
                chat_id=raw.chat_id
            )

        # 3. Create and persist Signal record preserving the exact original text
        signal = Signal(
            telegram_message_id=raw.message_id,
            source_chat_id=str(raw.chat_id),
            source_chat_title=raw.chat_title,
            sender_id=raw.sender_id,
            sender_username=raw.sender_username,
            source=raw.source,
            raw_message=raw.text or "",
            status="RECEIVED",
            telegram_timestamp=raw.telegram_timestamp,
            received_at=received_at
        )
        session.add(signal)
        await session.flush()

        # 4. Create System Audit Event
        system_event = SystemEvent(
            component="telegram_ingestion",
            event_type="MESSAGE_INGESTED",
            severity="INFO",
            message=f"Signal message ingested from chat {raw.chat_id}",
            payload={
                "signal_id": signal.id,
                "message_id": raw.message_id,
                "chat_id": str(raw.chat_id),
                "chat_title": raw.chat_title,
                "sender_id": raw.sender_id,
                "text_length": len(raw.text or "")
            }
        )
        session.add(system_event)
        await session.commit()
        await session.refresh(signal)

        # 5. Build normalized ingestion event
        event = TelegramIngestionEvent(
            signal_id=signal.id,
            telegram_message_id=raw.message_id,
            chat_id=str(raw.chat_id),
            chat_title=raw.chat_title,
            sender_id=raw.sender_id,
            sender_username=raw.sender_username,
            raw_message=signal.raw_message,
            telegram_timestamp=signal.telegram_timestamp,
            received_at=signal.received_at,
            source=raw.source
        )

        logger.info(
            "TELEGRAM_MESSAGE_RECEIVED",
            extra={
                "event_type": "TELEGRAM_MESSAGE_RECEIVED",
                "signal_id": signal.id,
                "chat_id": raw.chat_id,
                "message_id": raw.message_id,
                "chat_title": raw.chat_title,
                "sender_id": raw.sender_id,
                "received_at": received_at.isoformat()
            }
        )

        # Notify downstream pipeline listeners
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Downstream pipeline listener error: {e}", exc_info=True)

        return IngestionResult(
            status="INGESTED",
            signal_id=signal.id,
            event=event,
            message_id=raw.message_id,
            chat_id=raw.chat_id
        )

# Global singleton
telegram_ingestion_service = TelegramIngestionService()


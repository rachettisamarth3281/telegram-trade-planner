from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.telegram.schemas import RawTelegramMessage, IngestionResult
from app.telegram.ingestion_service import telegram_ingestion_service
from app.telegram.client import telegram_service

router = APIRouter(prefix="/telegram", tags=["Telegram Ingestion"])

class MockTelegramMessageRequest(BaseModel):
    message_id: int = Field(..., description="Unique message ID within chat")
    chat_id: str = Field(default="-1001234567890", description="Telegram channel/group ID")
    chat_title: Optional[str] = Field(default="VIP Trading Signals", description="Channel title")
    sender_id: Optional[str] = Field(default="user_vip", description="Sender user ID")
    sender_username: Optional[str] = Field(default="vip_provider", description="Sender username")
    text: Optional[str] = Field(default=None, description="Signal message text")
    has_media: bool = Field(default=False, description="Whether message includes photo/document")
    is_service: bool = Field(default=False, description="Whether message is a service notification")
    telegram_timestamp: Optional[datetime] = None

@router.get("/status")
async def get_telegram_status():
    """Retrieve current Telegram listener connection status and configuration (safely masked)."""
    return telegram_service.get_status()

@router.post("/mock-ingest", response_model=IngestionResult)
async def mock_ingest_message(
    payload: MockTelegramMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulates receiving a Telegram message in development / mock mode.
    Tests filtering, idempotency, and exact message persistence.
    """
    raw = RawTelegramMessage(
        message_id=payload.message_id,
        chat_id=payload.chat_id,
        chat_title=payload.chat_title,
        sender_id=payload.sender_id,
        sender_username=payload.sender_username,
        text=payload.text,
        has_media=payload.has_media,
        is_service=payload.is_service,
        telegram_timestamp=payload.telegram_timestamp,
        source="MOCK_DEVELOPMENT"
    )
    result = await telegram_ingestion_service.ingest_message(raw, db=db)
    return result


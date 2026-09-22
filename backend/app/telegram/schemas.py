from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class RawTelegramMessage(BaseModel):
    """Raw incoming Telegram message representation before filtering and persistence."""
    message_id: int = Field(..., description="Unique Telegram message ID within the chat")
    chat_id: str = Field(..., description="Unique Telegram chat/channel ID")
    chat_title: Optional[str] = Field(default=None, description="Title of the Telegram group/channel")
    sender_id: Optional[str] = Field(default=None, description="Sender's unique ID")
    sender_username: Optional[str] = Field(default=None, description="Sender username if available")
    text: Optional[str] = Field(default=None, description="Message text or media caption")
    has_media: bool = Field(default=False, description="Whether the message includes media (photo/document/video)")
    is_service: bool = Field(default=False, description="Whether this is a Telegram system/service message")
    is_edit: bool = Field(default=False, description="Whether this is an edited message update")
    telegram_timestamp: Optional[datetime] = Field(default=None, description="Original Telegram message creation timestamp")
    source: str = Field(default="TELEGRAM_USERBOT", description="Ingestion source identifier")
    extra_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional raw payload attributes")

class TelegramIngestionEvent(BaseModel):
    """Normalized ingestion event payload ready to be passed to future pipeline stages."""
    signal_id: str
    telegram_message_id: int
    chat_id: str
    chat_title: Optional[str] = None
    sender_id: Optional[str] = None
    sender_username: Optional[str] = None
    raw_message: str
    telegram_timestamp: Optional[datetime] = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "TELEGRAM_USERBOT"

class IngestionResult(BaseModel):
    """Result of processing an incoming Telegram message."""
    status: str = Field(..., description="'INGESTED', 'DUPLICATE', 'IGNORED', or 'ERROR'")
    signal_id: Optional[str] = None
    reason: Optional[str] = None
    event: Optional[TelegramIngestionEvent] = None
    message_id: int
    chat_id: str


import asyncio
import logging
from typing import Optional, List, Union
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.errors import RPCError

from app.config import settings
from app.telegram.schemas import RawTelegramMessage, IngestionResult
from app.telegram.ingestion_service import telegram_ingestion_service
from app.utils.logging import get_logger

logger = get_logger("app.telegram.client")

def mask_credential(val: Optional[Union[str, int]], show_chars: int = 3) -> str:
    """Mask sensitive credentials for safe structured logging."""
    if val is None:
        return "[NOT CONFIGURED]"
    str_val = str(val)
    if len(str_val) <= show_chars * 2:
        return "***"
    return f"{str_val[:show_chars]}***{str_val[-show_chars:]}"

class TelegramListenerService:
    """
    MTProto Client Listener for Telegram VIP Channels and Groups.
    Manages connection lifecycles, reconnects with exponential backoff, masks credentials in logs,
    and supports a development mock mode.
    """

    def __init__(self):
        self.api_id: Optional[int] = settings.TELEGRAM_API_ID
        self.api_hash: Optional[str] = settings.TELEGRAM_API_HASH
        self.session_name: str = settings.TELEGRAM_SESSION
        self.source_chat_id: Optional[str] = settings.TELEGRAM_SOURCE_CHAT_ID
        self.phone: Optional[str] = settings.TELEGRAM_PHONE
        self.bot_token: Optional[str] = settings.TELEGRAM_BOT_TOKEN
        self.mock_mode: bool = settings.TELEGRAM_MOCK_MODE

        self.client: Optional[TelegramClient] = None
        self._is_running: bool = False
        self._retry_count: int = 0
        self._shutdown_event = asyncio.Event()

    @property
    def is_configured(self) -> bool:
        """Returns True if API credentials are provided or if running in mock mode."""
        if self.mock_mode:
            return True
        return bool(self.api_id and self.api_hash)

    def get_status(self) -> dict:
        """Returns a safe, masked connection status dictionary."""
        return {
            "configured": self.is_configured,
            "mock_mode": self.mock_mode,
            "api_id": mask_credential(self.api_id),
            "api_hash": mask_credential(self.api_hash),
            "session": self.session_name,
            "source_chat_id": self.source_chat_id or "[ALL_INCOMING]",
            "phone": mask_credential(self.phone),
            "is_running": self._is_running,
            "retry_count": self._retry_count
        }

    async def start(self) -> None:
        """Starts the Telegram listener or activates mock development mode."""
        if self.mock_mode:
            self._is_running = True
            logger.info(
                "Telegram listener active in MOCK_MODE (Development). Awaiting mock events or API triggers.",
                extra={"mode": "MOCK_DEVELOPMENT"}
            )
            return

        if not self.is_configured:
            logger.info(
                "Telegram credentials not configured. Ingestion layer running in standby mode. "
                "Use mock API endpoints or supply TELEGRAM_API_ID / TELEGRAM_API_HASH to activate live listening.",
                extra={"status": "STANDBY"}
            )
            return

        self._shutdown_event.clear()
        self._is_running = True
        logger.info(
            "Initializing Telegram MTProto Client",
            extra={
                "api_id": mask_credential(self.api_id),
                "api_hash": mask_credential(self.api_hash),
                "source_chat_id": self.source_chat_id or "[ALL]"
            }
        )

        while self._is_running and not self._shutdown_event.is_set():
            try:
                self.client = TelegramClient(
                    self.session_name,
                    self.api_id,
                    self.api_hash
                )

                # Determine target chats filter
                chats = [int(self.source_chat_id)] if self.source_chat_id and self.source_chat_id.lstrip("-").isdigit() else (
                    [self.source_chat_id] if self.source_chat_id else None
                )

                @self.client.on(events.NewMessage(chats=chats))
                async def handle_new_message(event):
                    await self._on_message_received(event)

                await self.client.start(phone=self.phone, bot_token=self.bot_token)
                self._retry_count = 0
                logger.info("Telegram MTProto listener successfully connected and listening.")
                await self.client.run_until_disconnected()

            except (RPCError, ConnectionError, OSError, asyncio.CancelledError) as e:
                if self._shutdown_event.is_set():
                    break
                self._retry_count += 1
                delay = min(settings.TELEGRAM_RETRY_DELAY * (2 ** (self._retry_count - 1)), 60.0)
                logger.error(
                    "TELEGRAM_CONNECTION_ERROR",
                    extra={
                        "event_type": "TELEGRAM_CONNECTION_ERROR",
                        "error": str(e),
                        "retry_count": self._retry_count,
                        "next_retry_delay": delay
                    }
                )
                if self._retry_count > settings.TELEGRAM_RETRY_ATTEMPTS:
                    logger.critical(
                        f"Telegram listener exceeded maximum retry attempts ({settings.TELEGRAM_RETRY_ATTEMPTS}). Pausing listener."
                    )
                    self._is_running = False
                    break
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Unexpected Telegram client error: {e}", exc_info=True)
                break

    async def _on_message_received(self, event) -> IngestionResult:
        """Translates a Telethon event to a RawTelegramMessage and passes it to ingestion."""
        msg = event.message
        chat = await event.get_chat()
        sender = await event.get_sender()

        chat_id = str(event.chat_id)
        chat_title = getattr(chat, "title", None) or getattr(chat, "username", None) or str(chat_id)
        sender_id = str(getattr(sender, "id", None)) if sender else None
        sender_username = getattr(sender, "username", None)

        # Check if message is a service message
        is_service = getattr(msg, "action", None) is not None

        raw_msg = RawTelegramMessage(
            message_id=msg.id,
            chat_id=chat_id,
            chat_title=chat_title,
            sender_id=sender_id,
            sender_username=sender_username,
            text=msg.message,
            has_media=bool(msg.media),
            is_service=is_service,
            telegram_timestamp=msg.date.replace(tzinfo=timezone.utc) if msg.date else None,
            source="TELEGRAM_USERBOT"
        )

        return await telegram_ingestion_service.ingest_message(raw_msg)

    async def ingest_mock_message(
        self,
        message_id: int,
        text: str,
        chat_id: Optional[str] = None,
        chat_title: Optional[str] = None,
        sender_id: Optional[str] = None,
        sender_username: Optional[str] = None,
        has_media: bool = False,
        is_service: bool = False,
        telegram_timestamp: Optional[datetime] = None
    ) -> IngestionResult:
        """Direct helper to inject mock Telegram messages for development, staging, or automated testing."""
        raw_msg = RawTelegramMessage(
            message_id=message_id,
            chat_id=chat_id or self.source_chat_id or "-1001234567890",
            chat_title=chat_title or "VIP Forex Signals (Mock)",
            sender_id=sender_id or "user_101",
            sender_username=sender_username or "vip_admin",
            text=text,
            has_media=has_media,
            is_service=is_service,
            telegram_timestamp=telegram_timestamp or datetime.now(timezone.utc),
            source="MOCK_DEVELOPMENT"
        )
        return await telegram_ingestion_service.ingest_message(raw_msg)

    async def stop(self) -> None:
        """Gracefully disconnects and stops the listener."""
        self._is_running = False
        self._shutdown_event.set()
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        logger.info("Telegram listener service stopped.")

# Global singleton
telegram_service = TelegramListenerService()

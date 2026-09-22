import logging
import asyncio
from typing import Optional
from telethon import TelegramClient, events
from app.config import settings
from app.database import AsyncSessionLocal
from app.schemas.signal_schema import SignalIngestRequest
from app.api.v1.signals import ingest_signal

logger = logging.getLogger(__name__)

class TelegramListenerService:
    """
    MTProto Client listener for Telegram VIP channels and Groups.
    Listens for new text messages and forwards them into the ingestion and paper trading pipeline.
    """

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._is_running = False

    async def start(self):
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            logger.info("Telegram API credentials not configured. Live Telegram MTProto listener in standby mode.")
            return

        try:
            self.client = TelegramClient(
                settings.TELEGRAM_SESSION_NAME,
                settings.TELEGRAM_API_ID,
                settings.TELEGRAM_API_HASH
            )

            @self.client.on(events.NewMessage)
            async def handler(event):
                try:
                    text = event.message.message
                    if not text:
                        return

                    chat = await event.get_chat()
                    chat_title = getattr(chat, 'title', None) or getattr(chat, 'username', 'Unknown')
                    channel_id = str(event.chat_id)

                    logger.info(f"Received Telegram message from channel [{chat_title} ({channel_id})]: {text[:40]}...")

                    async with AsyncSessionLocal() as db:
                        req = SignalIngestRequest(
                            raw_text=text,
                            telegram_message_id=event.id,
                            channel_id=channel_id,
                            channel_title=chat_title,
                            source="TELEGRAM_USERBOT",
                            target_r_multiple=settings.DEFAULT_R_TARGET
                        )
                        await ingest_signal(req, db)

                except Exception as e:
                    logger.error(f"Error processing incoming Telegram event: {e}", exc_info=True)

            await self.client.start(phone=settings.TELEGRAM_PHONE, bot_token=settings.TELEGRAM_BOT_TOKEN)
            self._is_running = True
            logger.info("Telegram MTProto listener successfully started and listening for VIP signals.")

        except Exception as e:
            logger.warning(f"Failed to start Telegram client: {e}. REST Webhook ingestion remains fully operational.")

    async def stop(self):
        if self.client and self._is_running:
            await self.client.disconnect()
            self._is_running = False
            logger.info("Telegram MTProto listener stopped.")

telegram_listener = TelegramListenerService()


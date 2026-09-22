from typing import Tuple, Optional
from app.telegram.schemas import RawTelegramMessage
from app.utils.logging import get_logger

logger = get_logger("app.telegram.filter")

class TelegramMessageFilter:
    """
    Evaluates incoming Telegram messages to determine if they contain actionable trading text.
    Filters out system service messages, empty messages, photos without captions, and reactions.
    """

    @classmethod
    def evaluate(cls, message: RawTelegramMessage) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_acceptable, rejection_reason).
        If is_acceptable is True, the message is passed to the ingestion persistence pipeline.
        """
        # 1. Ignore system / service messages (e.g. pinned message, user joined, group photo changed)
        if message.is_service:
            return False, "SYSTEM_SERVICE_MESSAGE"

        # 2. Check for empty or None text
        if message.text is None:
            if message.has_media:
                return False, "MEDIA_WITHOUT_TEXT_CAPTION"
            return False, "EMPTY_MESSAGE_TEXT"

        stripped_text = message.text.strip()
        if not stripped_text:
            if message.has_media:
                return False, "MEDIA_WITHOUT_TEXT_CAPTION"
            return False, "WHITESPACE_ONLY_MESSAGE"

        # 3. Minimum length sanity check (e.g. single character emojis or reactions)
        if len(stripped_text) < 3:
            return False, "MESSAGE_TOO_SHORT_NON_SIGNAL"

        return True, None


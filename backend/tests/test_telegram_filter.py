import pytest
from app.telegram.schemas import RawTelegramMessage
from app.telegram.filter import TelegramMessageFilter

def test_filter_accepts_valid_signal_text():
    msg = RawTelegramMessage(
        message_id=101,
        chat_id="-1001234567890",
        text="Sell gold @ 4350.53\nSL 4358"
    )
    is_ok, reason = TelegramMessageFilter.evaluate(msg)
    assert is_ok is True
    assert reason is None

def test_filter_accepts_photo_with_text_caption():
    msg = RawTelegramMessage(
        message_id=102,
        chat_id="-1001234567890",
        text="BUY EURUSD @ 1.08500 SL 1.08000 TP 1.09500",
        has_media=True
    )
    is_ok, reason = TelegramMessageFilter.evaluate(msg)
    assert is_ok is True
    assert reason is None

def test_filter_ignores_photo_without_text():
    msg = RawTelegramMessage(
        message_id=103,
        chat_id="-1001234567890",
        text=None,
        has_media=True
    )
    is_ok, reason = TelegramMessageFilter.evaluate(msg)
    assert is_ok is False
    assert reason == "MEDIA_WITHOUT_TEXT_CAPTION"

def test_filter_ignores_empty_text():
    msg = RawTelegramMessage(
        message_id=104,
        chat_id="-1001234567890",
        text="   \n  "
    )
    is_ok, reason = TelegramMessageFilter.evaluate(msg)
    assert is_ok is False
    assert reason == "WHITESPACE_ONLY_MESSAGE"

def test_filter_ignores_system_service_message():
    msg = RawTelegramMessage(
        message_id=105,
        chat_id="-1001234567890",
        text="Pinned a message",
        is_service=True
    )
    is_ok, reason = TelegramMessageFilter.evaluate(msg)
    assert is_ok is False
    assert reason == "SYSTEM_SERVICE_MESSAGE"

def test_filter_ignores_reaction_or_tiny_emoji():
    msg = RawTelegramMessage(
        message_id=106,
        chat_id="-1001234567890",
        text="👍"
    )
    is_ok, reason = TelegramMessageFilter.evaluate(msg)
    assert is_ok is False
    assert reason == "MESSAGE_TOO_SHORT_NON_SIGNAL"


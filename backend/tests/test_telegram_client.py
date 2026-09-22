import pytest
from app.telegram.client import mask_credential, telegram_service

def test_credential_masking():
    assert mask_credential("1234567890", show_chars=3) == "123***890"
    assert mask_credential("abcdef1234567890abcdef", show_chars=4) == "abcd***cdef"
    assert mask_credential(None) == "[NOT CONFIGURED]"
    assert mask_credential("short") == "***"

def test_telegram_status_does_not_leak_credentials():
    status = telegram_service.get_status()
    assert "configured" in status
    assert "mock_mode" in status
    assert "api_id" in status
    assert "api_hash" in status
    assert "session" in status

    # Ensure unmasked secret strings are never raw
    if status["api_hash"] != "[NOT CONFIGURED]":
        assert "***" in status["api_hash"]

@pytest.mark.asyncio
async def test_telegram_service_mock_ingest():
    result = await telegram_service.ingest_mock_message(
        message_id=9901,
        text="Sell gold @ 4350.53\nSL 4358",
        chat_id="-100990011",
        chat_title="Mock Gold Channel"
    )
    assert result.status == "INGESTED"
    assert result.message_id == 9901
    assert result.chat_id == "-100990011"


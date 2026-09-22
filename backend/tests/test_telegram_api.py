import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.asyncio
async def test_telegram_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/telegram/status")
        assert res.status_code == 200
        data = res.json()
        assert "configured" in data
        assert "mock_mode" in data
        assert "is_running" in data

@pytest.mark.asyncio
async def test_telegram_mock_ingest_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Ingest valid mock message
        res = await client.post("/api/v1/telegram/mock-ingest", json={
            "message_id": 12001,
            "chat_id": "-10055443322",
            "chat_title": "VIP Telegram Tests",
            "sender_username": "pro_trader",
            "text": "BUY XAUUSD @ 4350.00 SL 4340.00 TP 4370.00"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "INGESTED"
        assert data["signal_id"] is not None
        assert data["message_id"] == 12001

        # 2. Test duplicate rejection via API
        dup_res = await client.post("/api/v1/telegram/mock-ingest", json={
            "message_id": 12001,
            "chat_id": "-10055443322",
            "text": "BUY XAUUSD @ 4350.00 SL 4340.00 TP 4370.00"
        })
        assert dup_res.status_code == 200
        dup_data = dup_res.json()
        assert dup_data["status"] == "DUPLICATE"

        # 3. Test ignored photo without caption
        ign_res = await client.post("/api/v1/telegram/mock-ingest", json={
            "message_id": 12002,
            "chat_id": "-10055443322",
            "text": None,
            "has_media": True
        })
        assert ign_res.status_code == 200
        ign_data = ign_res.json()
        assert ign_data["status"] == "IGNORED"


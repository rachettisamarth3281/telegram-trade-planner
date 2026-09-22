import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["mode"] == "PAPER_TRADING_ONLY"

@pytest.mark.asyncio
async def test_parse_preview_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/signals/parse-preview", json={
            "raw_text": "Sell gold @ 4350.53\nSL 4358"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "XAUUSD"
        assert data["side"] == "SELL"
        assert data["entry_price"] == 4350.53
        assert data["provider_sl"] == 4358.00
        assert data["is_valid"] is True
        assert data["metrics"]["r1_target"] == 4343.06
        assert data["metrics"]["r2_target"] == 4335.59

@pytest.mark.asyncio
async def test_ingest_valid_signal_creates_paper_trade():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/signals/ingest", json={
            "raw_text": "BUY EURUSD CMP 1.08500 SL 1.08000 TP1 1.09500",
            "channel_title": "VIP Telegram",
            "target_r_multiple": 2.0
        })
        assert res.status_code == 200
        data = res.json()
        assert data["validation_status"] == "VALID"
        assert data["paper_trade_id"] is not None
        trade_id = data["paper_trade_id"]

        # Check paper trade created
        trade_res = await client.get(f"/api/v1/trades/{trade_id}")
        assert trade_res.status_code == 200
        trade_data = trade_res.json()
        assert trade_data["symbol"] == "EURUSD"
        assert trade_data["side"] == "BUY"
        assert trade_data["status"] == "OPEN"

@pytest.mark.asyncio
async def test_ingest_invalid_signal_audited_without_trade():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # BUY with SL above entry
        res = await client.post("/api/v1/signals/ingest", json={
            "raw_text": "BUY EURUSD @ 1.08500 SL 1.09000"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["validation_status"] == "INVALID"
        assert data["paper_trade_id"] is None
        assert "Stop Loss" in data["rejection_reason"]

@pytest.mark.asyncio
async def test_simulate_tick_triggers_tp_closure():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a trade
        sig_res = await client.post("/api/v1/signals/ingest", json={
            "raw_text": "BUY XAUUSD @ 4350.00 SL 4340.00 TP1 4370.00"
        })
        trade_id = sig_res.json()["paper_trade_id"]

        # 2. Simulate price tick hitting TP
        tick_res = await client.post("/api/v1/trades/simulate-tick", json={
            "symbol": "XAUUSD",
            "bid": 4370.50
        })
        assert tick_res.status_code == 200

        # 3. Verify trade is closed with profit
        trade_res = await client.get(f"/api/v1/trades/{trade_id}")
        trade_data = trade_res.json()
        assert trade_data["status"] == "CLOSED_TP"
        assert trade_data["exit_reason"] == "TP_HIT"
        assert trade_data["realized_pnl_usd"] > 0

@pytest.mark.asyncio
async def test_analytics_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Ingest a signal & simulate closure
        sig_res = await client.post("/api/v1/signals/ingest", json={
            "raw_text": "BUY GBPUSD @ 1.25000 SL 1.24000 TP1 1.27000"
        })
        assert sig_res.status_code == 200
        
        await client.post("/api/v1/trades/simulate-tick", json={
            "symbol": "GBPUSD",
            "bid": 1.27500
        })

        # 2. Query complete report
        rep_res = await client.get("/api/v1/analytics/report")
        assert rep_res.status_code == 200
        rep_data = rep_res.json()
        assert "signals" in rep_data
        assert "trades" in rep_data
        assert "performance" in rep_data
        assert "provider_comparison" in rep_data
        assert "trades_by_symbol" in rep_data
        assert "trades_by_side" in rep_data
        assert "trades_by_date" in rep_data
        assert "trades_by_hour" in rep_data

        # 3. Query summary endpoint
        summary_res = await client.get("/api/v1/analytics/summary")
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["signals"]["total_signals"] >= 1
        assert summary_data["trades"]["paper_trades"] >= 1


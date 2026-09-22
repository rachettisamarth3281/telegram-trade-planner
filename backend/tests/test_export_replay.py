import pytest
from app.database.session import AsyncSessionLocal, init_db
from app.services.replay_engine import TelegramExportReplayEngine
from tests.fixtures.real_telegram_messages import REAL_TELEGRAM_MESSAGES

@pytest.mark.asyncio
async def test_replay_real_telegram_export():
    await init_db()
    replay_engine = TelegramExportReplayEngine()

    async with AsyncSessionLocal() as db:
        stats = await replay_engine.replay_messages(
            db=db,
            messages=REAL_TELEGRAM_MESSAGES,
            chat_id="SHUBHAM_VIP_TEST_REPLAY"
        )

        print("\n=== REPLAY ENGINE STATISTICS ===")
        print(f"Total Messages: {stats['total_messages']}")
        print(f"Classified Breakdown: {stats['classified_types']}")
        print(f"Signals Created: {stats['signals_created']}")
        print(f"Trades Created: {stats['trades_created']}")
        print(f"SL Updates Correlated: {stats['sl_updates_correlated']}")
        print(f"Targets Configured: {stats['targets_configured']}")
        print(f"Management Events: {stats['management_events']}")
        print(f"Provider Outcomes: {stats['provider_outcomes']}")

        assert stats["total_messages"] == len(REAL_TELEGRAM_MESSAGES)
        assert stats["signals_created"] > 0
        assert stats["trades_created"] > 0
        assert stats["sl_updates_correlated"] > 0
        assert stats["management_events"] > 0
        assert stats["provider_outcomes"] > 0


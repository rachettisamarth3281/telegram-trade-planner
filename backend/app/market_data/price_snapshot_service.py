from typing import Optional, Dict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import PriceSnapshot
from app.market_data.interface import TickData
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("price_snapshot_service")

class PriceSnapshotService:
    """
    Throttled persistence service for PriceSnapshots.
    Avoids excessive database writes on high-frequency market tick streams.
    """

    def __init__(self, interval_seconds: Optional[float] = None):
        self.interval_seconds = interval_seconds or getattr(settings, "PRICE_SNAPSHOT_INTERVAL_SECONDS", 5.0)
        self._last_snapshot_time: Dict[str, datetime] = {}

    def should_record_snapshot(self, symbol: str, current_time: Optional[datetime] = None) -> bool:
        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        now = current_time or datetime.now(timezone.utc)
        last_time = self._last_snapshot_time.get(clean)

        if last_time is None:
            return True

        elapsed = (now - last_time).total_seconds()
        return elapsed >= self.interval_seconds

    async def record_snapshot(
        self,
        db: AsyncSession,
        tick: TickData,
        force: bool = False
    ) -> Optional[PriceSnapshot]:
        clean = tick.symbol.upper().strip().replace("/", "").replace("-", "")
        now = tick.timestamp or datetime.now(timezone.utc)

        if not force and not self.should_record_snapshot(clean, now):
            return None

        snapshot = PriceSnapshot(
            symbol=clean,
            bid_price=tick.bid,
            ask_price=tick.ask,
            spread=tick.spread,
            provider=tick.provider,
            snapshot_time=now,
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)

        self._last_snapshot_time[clean] = now
        logger.debug(
            "PRICE_SNAPSHOT_SAVED",
            symbol=clean,
            bid=tick.bid,
            ask=tick.ask,
            provider=tick.provider
        )
        return snapshot

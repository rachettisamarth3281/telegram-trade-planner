import asyncio
from typing import Optional, Callable, Awaitable, Dict, List
from datetime import datetime, timezone, timedelta
from app.market_data.interface import MarketDataProvider, TickData, CandleData
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("mock_market_data")

class MockMarketDataProvider(MarketDataProvider):
    """
    Mock & Simulated In-Memory Market Data Provider.
    Used for development, simulation, testing, and replay.
    """

    def __init__(self, stale_threshold_seconds: Optional[float] = None):
        self._prices: Dict[str, TickData] = {}
        self._candles: Dict[str, List[CandleData]] = {}
        self._subscribers: Dict[str, List[Callable[[TickData], Awaitable[None]]]] = {}
        self._connected = True
        self.stale_threshold_seconds = stale_threshold_seconds or getattr(settings, "STALE_PRICE_THRESHOLD_SECONDS", 60.0)
        self.simulate_error_on_next_call = False

    async def connect(self) -> bool:
        self._connected = True
        logger.info("MARKET_DATA_CONNECTED", provider="MockMarketDataProvider")
        return True

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("MARKET_DATA_DISCONNECTED", provider="MockMarketDataProvider")

    async def is_connected(self) -> bool:
        return self._connected

    async def get_current_price(self, symbol: str) -> Optional[TickData]:
        if self.simulate_error_on_next_call:
            self.simulate_error_on_next_call = False
            raise ConnectionError("Simulated market data provider error")

        if not self._connected:
            return None

        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        tick = self._prices.get(clean)
        if tick:
            # Check stale price
            now = datetime.now(timezone.utc)
            age = (now - tick.timestamp).total_seconds()
            tick.is_stale = age > self.stale_threshold_seconds
        return tick

    async def get_latest_price(self, symbol: str) -> Optional[TickData]:
        """Alias for get_current_price."""
        return await self.get_current_price(symbol)

    async def subscribe_to_price_updates(
        self,
        symbol: str,
        callback: Callable[[TickData], Awaitable[None]]
    ) -> None:
        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        if clean not in self._subscribers:
            self._subscribers[clean] = []
        self._subscribers[clean].append(callback)

    # Alias for backward compatibility
    async def subscribe_ticks(self, symbol: str, callback: Callable[[TickData], Awaitable[None]]) -> None:
        await self.subscribe_to_price_updates(symbol, callback)

    async def get_historical_prices(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "M1"
    ) -> List[CandleData]:
        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        all_bars = self._candles.get(clean, [])
        filtered = [
            b for b in all_bars
            if start <= b.timestamp <= end and b.timeframe == timeframe
        ]
        return filtered

    async def simulate_tick(
        self,
        symbol: str,
        bid: float,
        ask: float,
        source_timestamp: Optional[datetime] = None,
        override_receipt_time: Optional[datetime] = None,
    ) -> TickData:
        """Inject a simulated price tick and notify subscribers."""
        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        now = override_receipt_time or datetime.now(timezone.utc)
        src_ts = source_timestamp or now

        age = (now - src_ts).total_seconds()
        is_stale = age > self.stale_threshold_seconds

        tick = TickData(
            symbol=clean,
            bid=bid,
            ask=ask,
            timestamp=now,
            source_timestamp=src_ts,
            provider="mock",
            is_stale=is_stale,
        )
        self._prices[clean] = tick

        logger.debug(
            "PRICE_TICK_RECEIVED",
            symbol=clean,
            bid=bid,
            ask=ask,
            spread=tick.spread,
            is_stale=is_stale
        )

        if self._connected and clean in self._subscribers:
            for cb in self._subscribers[clean]:
                try:
                    await cb(tick)
                except Exception as exc:
                    logger.error("MARKET_DATA_CALLBACK_ERROR", symbol=clean, error=str(exc))

        return tick

    async def simulate_candle(
        self,
        symbol: str,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float = 100.0,
        timestamp: Optional[datetime] = None,
        timeframe: str = "M1"
    ) -> CandleData:
        """Inject a simulated candle bar into historical collection."""
        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        candle = CandleData(
            symbol=clean,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timestamp=timestamp or datetime.now(timezone.utc),
            timeframe=timeframe,
        )
        if clean not in self._candles:
            self._candles[clean] = []
        self._candles[clean].append(candle)
        return candle

# Alias
SimulatedMarketDataProvider = MockMarketDataProvider

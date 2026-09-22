from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class TickData:
    symbol: str
    bid: float
    ask: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_timestamp: Optional[datetime] = None
    provider: str = "simulated"
    is_stale: bool = False

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return round(self.ask - self.bid, 6)

@dataclass
class CandleData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeframe: str = "M1"

class MarketDataProvider(ABC):
    """
    Abstract interface for market price feeds.
    Strictly decoupled so live price integrations can be used solely for price monitoring.
    IMPORTANT: This interface does NOT support order execution.
    """

    @abstractmethod
    async def get_current_price(self, symbol: str) -> Optional[TickData]:
        """Retrieve the most recent price tick for a symbol."""
        pass

    @abstractmethod
    async def subscribe_to_price_updates(self, symbol: str, callback: Callable[[TickData], Awaitable[None]]) -> None:
        """Register a callback for incoming real-time price updates."""
        pass

    @abstractmethod
    async def get_historical_prices(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "M1"
    ) -> List[CandleData]:
        """Fetch historical candle bars for backtesting or candle monitoring."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if provider connection is healthy."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Establish provider connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close provider connection."""
        pass

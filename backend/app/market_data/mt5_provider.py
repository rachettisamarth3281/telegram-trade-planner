import asyncio
from typing import Optional, Callable, Awaitable, Dict, List
from datetime import datetime, timezone
from app.market_data.interface import MarketDataProvider, TickData, CandleData
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("mt5_market_data")

class MT5MarketDataProvider(MarketDataProvider):
    """
    MetaTrader 5 Market Data Adapter.
    
    IMPORTANT:
    - Strictly READ-ONLY for market data (ticks & rates).
    - NEVER executes trades or sends orders to MT5.
    - Gracefully handles non-Windows/headless environments or when MetaTrader5 package is absent.
    """

    def __init__(self):
        self._connected = False
        self._subscribers: Dict[str, List[Callable[[TickData], Awaitable[None]]]] = {}
        self._mt5 = None
        self._init_mt5_module()

    def _init_mt5_module(self):
        try:
            import MetaTrader5 as mt5  # type: ignore
            self._mt5 = mt5
        except ImportError:
            self._mt5 = None
            logger.info("MT5_PACKAGE_NOT_INSTALLED", message="MetaTrader5 package not available in environment; MT5 provider will remain in fallback mode.")

    async def connect(self) -> bool:
        if not self._mt5:
            logger.warning("MT5_CONNECT_SKIPPED", reason="MetaTrader5 package not available.")
            return False

        try:
            kwargs = {}
            if settings.MT5_PATH:
                kwargs["path"] = settings.MT5_PATH
            if settings.MT5_LOGIN:
                kwargs["login"] = settings.MT5_LOGIN
            if settings.MT5_PASSWORD:
                kwargs["password"] = settings.MT5_PASSWORD
            if settings.MT5_SERVER:
                kwargs["server"] = settings.MT5_SERVER

            initialized = self._mt5.initialize(**kwargs)
            if initialized:
                self._connected = True
                logger.info("MT5_CONNECTED_SUCCESSFULLY", server=settings.MT5_SERVER or "default")
                return True
            else:
                last_error = self._mt5.last_error()
                logger.error("MT5_INIT_FAILED", error=str(last_error))
                self._connected = False
                return False
        except Exception as exc:
            logger.error("MT5_CONNECT_ERROR", error=str(exc))
            self._connected = False
            return False

    async def disconnect(self) -> None:
        if self._mt5 and self._connected:
            try:
                self._mt5.shutdown()
            except Exception:
                pass
        self._connected = False
        logger.info("MT5_DISCONNECTED")

    async def is_connected(self) -> bool:
        return self._connected

    async def get_current_price(self, symbol: str) -> Optional[TickData]:
        if not self._mt5 or not self._connected:
            return None

        try:
            clean = symbol.upper().strip().replace("/", "").replace("-", "")
            tick_info = self._mt5.symbol_info_tick(clean)
            if tick_info is None:
                return None

            src_time = datetime.fromtimestamp(tick_info.time, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            is_stale = (now - src_time).total_seconds() > settings.STALE_PRICE_THRESHOLD_SECONDS

            return TickData(
                symbol=clean,
                bid=float(tick_info.bid),
                ask=float(tick_info.ask),
                timestamp=now,
                source_timestamp=src_time,
                provider="mt5",
                is_stale=is_stale,
            )
        except Exception as exc:
            logger.error("MT5_GET_PRICE_ERROR", symbol=symbol, error=str(exc))
            return None

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

    async def get_historical_prices(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "M1"
    ) -> List[CandleData]:
        if not self._mt5 or not self._connected:
            return []

        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        try:
            # Map timeframe string to MT5 timeframe constant
            tf_map = {
                "M1": getattr(self._mt5, "TIMEFRAME_M1", 1),
                "M5": getattr(self._mt5, "TIMEFRAME_M5", 5),
                "M15": getattr(self._mt5, "TIMEFRAME_M15", 15),
                "H1": getattr(self._mt5, "TIMEFRAME_H1", 60),
                "D1": getattr(self._mt5, "TIMEFRAME_D1", 1440),
            }
            mt5_tf = tf_map.get(timeframe.upper(), getattr(self._mt5, "TIMEFRAME_M1", 1))
            rates = self._mt5.copy_rates_range(clean, mt5_tf, start, end)
            if rates is None or len(rates) == 0:
                return []

            candles: List[CandleData] = []
            for r in rates:
                c_ts = datetime.fromtimestamp(r["time"], tz=timezone.utc)
                candles.append(CandleData(
                    symbol=clean,
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r["tick_volume"]),
                    timestamp=c_ts,
                    timeframe=timeframe,
                ))
            return candles
        except Exception as exc:
            logger.error("MT5_HISTORICAL_RATES_ERROR", symbol=symbol, error=str(exc))
            return []

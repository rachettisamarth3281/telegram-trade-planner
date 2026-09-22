import random
from typing import Dict, List, Optional, Callable, Awaitable
from datetime import datetime, timezone
from app.utils.instrument_specs import get_instrument_spec

class PriceMonitor:
    """
    Market Price Monitor.
    Provides live / simulated Ask and Bid quotes for all active currency pairs and metals.
    """

    # Base reference prices for simulation
    DEFAULT_PRICES: Dict[str, float] = {
        "XAUUSD": 4350.00,
        "XAGUSD": 32.50,
        "EURUSD": 1.08500,
        "GBPUSD": 1.30500,
        "USDJPY": 155.200,
        "GBPJPY": 198.500,
        "AUDUSD": 0.65500,
        "USDCAD": 1.38000,
        "USDCHF": 0.88500,
        "US30": 39500.0,
        "NAS100": 18200.0,
        "SPX500": 5350.0,
        "GER40": 18500.0,
        "BTCUSD": 67500.0,
        "ETHUSD": 3500.0
    }

    def __init__(self):
        self._current_prices: Dict[str, Dict[str, float]] = {}
        self._running = False
        self._subscribers: List[Callable[[str, float, float], Awaitable[None]]] = []
        self._initialize_prices()

    def _initialize_prices(self):
        now_ts = datetime.now(timezone.utc).timestamp()
        for sym, price in self.DEFAULT_PRICES.items():
            spec = get_instrument_spec(sym) or {"pip_size": 0.0001, "digits": 5}
            spread = spec["pip_size"] * 1.5
            self._current_prices[sym] = {
                "bid": round(price, spec["digits"]),
                "ask": round(price + spread, spec["digits"]),
                "last_update": now_ts
            }

    def get_price(self, symbol: str) -> Dict[str, float]:
        sym = symbol.upper()
        now_ts = datetime.now(timezone.utc).timestamp()
        if sym not in self._current_prices:
            self._current_prices[sym] = {"bid": 100.0, "ask": 100.02, "last_update": now_ts}
        return self._current_prices[sym]

    def set_price(self, symbol: str, bid: float, ask: Optional[float] = None) -> Dict[str, float]:
        """Manually update or inject a tick for a symbol (for backtesting / testing / simulation)."""
        sym = symbol.upper()
        spec = get_instrument_spec(sym) or {"pip_size": 0.0001, "digits": 5}
        if ask is None:
            spread = spec["pip_size"] * 1.5
            ask = bid + spread

        quote = {
            "bid": round(bid, spec["digits"]),
            "ask": round(ask, spec["digits"]),
            "last_update": datetime.now(timezone.utc).timestamp()
        }
        self._current_prices[sym] = quote
        return quote

    def subscribe_tick(self, callback: Callable[[str, float, float], Awaitable[None]]):
        self._subscribers.append(callback)

    async def broadcast_tick(self, symbol: str, bid: float, ask: float):
        for sub in self._subscribers:
            try:
                await sub(symbol, bid, ask)
            except Exception:
                pass

    def simulate_random_walk_step(self, symbol: str) -> Dict[str, float]:
        """Generates a small realistic micro-tick fluctuation."""
        sym = symbol.upper()
        spec = get_instrument_spec(sym) or {"pip_size": 0.0001, "digits": 5}
        current = self.get_price(sym)
        pip = spec["pip_size"]
        delta_pips = random.uniform(-0.5, 0.5)
        new_bid = round(current["bid"] + (delta_pips * pip), spec["digits"])
        new_ask = round(new_bid + (1.2 * pip), spec["digits"])

        self._current_prices[sym] = {
            "bid": new_bid,
            "ask": new_ask,
            "last_update": datetime.now(timezone.utc).timestamp()
        }
        return self._current_prices[sym]

price_monitor = PriceMonitor()

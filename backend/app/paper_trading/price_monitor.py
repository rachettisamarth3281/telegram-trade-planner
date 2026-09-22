import asyncio
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PaperTrade, TradeEvent, Signal
from app.market_data.interface import MarketDataProvider, TickData, CandleData
from app.market_data.price_snapshot_service import PriceSnapshotService
from app.paper_trading.enums import TradeStatus, ExitReason
from app.paper_trading.engine import PaperTradeEngine
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("price_monitor")

class CandleExecutionPolicy(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"  # Assumes SL hit first on dual breach (worst-case assumption)
    SL_FIRST = "SL_FIRST"          # Strictly prioritizes SL
    TP_FIRST = "TP_FIRST"          # Optimistic: prioritizes TP
    BAR_CLOSE = "BAR_CLOSE"        # Evaluates candle close price

class PriceMonitor:
    """
    Market Price Monitor & Paper Trade Lifecycle Evaluator.
    
    Responsibilities:
    - Listens to MarketDataProvider price streams.
    - Evaluates open simulated paper trades on every tick or candle.
    - Resolves dual-breach candle ambiguity using configurable execution policies.
    - Throttles PriceSnapshot database persistence.
    - Detects stale prices and provider disconnection errors.
    """

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        paper_trade_engine: Optional[PaperTradeEngine] = None,
        snapshot_service: Optional[PriceSnapshotService] = None,
        candle_policy: Optional[CandleExecutionPolicy] = None,
    ):
        self.provider = market_data_provider
        self.engine = paper_trade_engine or PaperTradeEngine()
        self.snapshot_service = snapshot_service or PriceSnapshotService()
        
        policy_str = getattr(settings, "CANDLE_EXECUTION_POLICY", "CONSERVATIVE").upper()
        self.candle_policy = candle_policy or CandleExecutionPolicy(policy_str)
        self._is_running = False

    async def on_tick_received(self, db: AsyncSession, tick: TickData) -> List[PaperTrade]:
        """
        Processes an incoming price tick:
        1. Logs structured event and checks for stale prices.
        2. Throttled persistence of PriceSnapshot.
        3. Evaluates all open paper trades for the symbol in sequential tick order.
        """
        symbol = tick.symbol.upper().strip().replace("/", "").replace("-", "")

        # 1. Stale price check
        if tick.is_stale:
            logger.warning(
                "STALE_PRICE_DETECTED",
                symbol=symbol,
                source_time=tick.source_timestamp.isoformat() if tick.source_timestamp else None,
                receipt_time=tick.timestamp.isoformat()
            )

        # 2. Throttled Price Snapshot record
        try:
            await self.snapshot_service.record_snapshot(db, tick)
        except Exception as exc:
            logger.error("SNAPSHOT_SAVE_ERROR", symbol=symbol, error=str(exc))

        # 3. Query all OPEN paper trades for this symbol
        stmt = select(PaperTrade).where(
            PaperTrade.symbol == symbol,
            PaperTrade.status == TradeStatus.OPEN.value
        )
        result = await db.scalars(stmt)
        open_trades = list(result.all())

        closed_trades: List[PaperTrade] = []
        for trade in open_trades:
            evaluated = await self.engine.evaluate_tick(
                db=db,
                trade=trade,
                current_bid=tick.bid,
                current_ask=tick.ask
            )
            if evaluated and evaluated.status in (TradeStatus.TP_HIT.value, TradeStatus.SL_HIT.value):
                closed_trades.append(evaluated)
                logger.info(
                    "PRICE_MONITOR_EVALUATED",
                    trade_id=evaluated.id,
                    symbol=symbol,
                    status=evaluated.status,
                    exit_reason=evaluated.exit_reason,
                    exit_price=evaluated.exit_price,
                    realized_r=evaluated.realized_r
                )

        return closed_trades

    async def evaluate_candle(
        self,
        db: AsyncSession,
        trade: PaperTrade,
        candle: CandleData
    ) -> Optional[PaperTrade]:
        """
        Evaluates a historical or live candle bar against an open paper position.
        Explicitly handles and records simultaneous SL and TP touch ambiguity.
        """
        if trade.status != TradeStatus.OPEN.value:
            return trade

        entry = trade.entry_price
        sl = trade.stop_loss
        tp = trade.take_profit
        high = candle.high
        low = candle.low
        close = candle.close

        sl_touched = False
        tp_touched = False

        if trade.side == "BUY":
            if low <= sl:
                sl_touched = True
            if tp is not None and high >= tp:
                tp_touched = True
        else:  # SELL
            if high >= sl:
                sl_touched = True
            if tp is not None and low <= tp:
                tp_touched = True

        # Case 1: Dual Breach (Candle touched BOTH SL and TP)
        if sl_touched and tp_touched:
            logger.warning(
                "CANDLE_DUAL_BREACH_DETECTED",
                trade_id=trade.id,
                symbol=trade.symbol,
                sl=sl,
                tp=tp,
                candle_low=low,
                candle_high=high,
                policy=self.candle_policy.value
            )

            # Resolve based on configured policy
            if self.candle_policy in (CandleExecutionPolicy.CONSERVATIVE, CandleExecutionPolicy.SL_FIRST):
                # Close at SL
                simulated_bid = sl if trade.side == "BUY" else high
                simulated_ask = high if trade.side == "BUY" else sl
            elif self.candle_policy == CandleExecutionPolicy.TP_FIRST:
                # Close at TP
                simulated_bid = tp if trade.side == "BUY" else low
                simulated_ask = low if trade.side == "BUY" else tp
            elif self.candle_policy == CandleExecutionPolicy.BAR_CLOSE:
                # Close based on close price
                if trade.side == "BUY":
                    simulated_bid = sl if close <= sl else (tp if tp and close >= tp else close)
                    simulated_ask = simulated_bid
                else:
                    simulated_ask = sl if close >= sl else (tp if tp and close <= tp else close)
                    simulated_bid = simulated_ask
            else:
                simulated_bid = sl
                simulated_ask = sl

            evaluated = await self.engine.evaluate_tick(db, trade, simulated_bid, simulated_ask)

            # Record ambiguity flag & audit note
            ambiguity_event = TradeEvent(
                paper_trade_id=trade.id,
                event_type="AMBIGUOUS_CANDLE_EVALUATION",
                price=evaluated.exit_price or close,
                details={
                    "is_ambiguous": True,
                    "ambiguity_note": "Both SL and TP touched within single candle range without tick sequence",
                    "candle_high": high,
                    "candle_low": low,
                    "candle_close": close,
                    "policy_applied": self.candle_policy.value,
                    "resolved_exit": evaluated.status
                }
            )
            db.add(ambiguity_event)
            await db.commit()
            return evaluated

        # Case 2: Only SL touched
        elif sl_touched:
            simulated_bid = sl if trade.side == "BUY" else low
            simulated_ask = high if trade.side == "BUY" else sl
            return await self.engine.evaluate_tick(db, trade, simulated_bid, simulated_ask)

        # Case 3: Only TP touched
        elif tp_touched and tp is not None:
            simulated_bid = tp if trade.side == "BUY" else low
            simulated_ask = high if trade.side == "BUY" else tp
            return await self.engine.evaluate_tick(db, trade, simulated_bid, simulated_ask)

        # Case 4: Neither touched - update excursions
        else:
            if trade.side == "BUY":
                if trade.highest_favorable_price is None or high > trade.highest_favorable_price:
                    trade.highest_favorable_price = high
                if trade.lowest_favorable_price is None or low < trade.lowest_favorable_price:
                    trade.lowest_favorable_price = low
            else:
                if trade.highest_favorable_price is None or low < trade.highest_favorable_price:
                    trade.highest_favorable_price = low
                if trade.lowest_favorable_price is None or high > trade.lowest_favorable_price:
                    trade.lowest_favorable_price = high
            await db.commit()
            return trade

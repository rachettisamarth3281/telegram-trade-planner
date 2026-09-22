from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import PaperTrade, TradeEvent, Signal
from app.utils.instrument_specs import get_instrument_spec

class PaperTradeEngine:
    """
    Simulated Paper Trading Engine.
    Manages order creation, lifecycle state transitions, SL/TP hit detection, P&L, and MFE/MAE tracking.
    """

    @classmethod
    async def create_trade(
        cls,
        db: AsyncSession,
        signal: Signal,
        effective_sl: float,
        target_r: float = 2.0
    ) -> PaperTrade:
        now = datetime.now(timezone.utc)
        active_tp: Optional[float] = signal.take_profit

        trade = PaperTrade(
            signal_id=signal.id,
            symbol=signal.symbol or "XAUUSD",
            side=signal.side or "BUY",
            status="OPEN",
            lot_size=1.0,
            entry_price=signal.entry_price or 0.0,
            stop_loss=effective_sl,
            take_profit=active_tp,
            target_r_multiple=target_r,
            opened_at=now
        )
        db.add(trade)
        await db.flush()

        event = TradeEvent(
            paper_trade_id=trade.id,
            event_type="ORDER_OPENED",
            price=trade.entry_price,
            details={
                "symbol": trade.symbol,
                "side": trade.side,
                "lot_size": trade.lot_size,
                "stop_loss": trade.stop_loss,
                "take_profit": trade.take_profit
            }
        )
        db.add(event)
        await db.commit()
        await db.refresh(trade)
        return trade

    @classmethod
    async def evaluate_trade_tick(
        cls,
        db: AsyncSession,
        trade: PaperTrade,
        current_bid: float,
        current_ask: float
    ) -> Optional[PaperTrade]:
        if trade.status != "OPEN":
            return None

        spec = get_instrument_spec(trade.symbol) or {
            "digits": 5,
            "pip_size": 0.0001,
            "contract_size": 100000.0
        }
        digits = spec["digits"]
        contract_size = spec["contract_size"]
        pip_size = spec["pip_size"]

        entry = trade.entry_price
        sl = trade.stop_loss
        tp = trade.take_profit
        initial_risk_dist = abs(entry - sl) or 0.0001

        is_closed = False
        exit_price: Optional[float] = None
        exit_reason: Optional[str] = None
        current_price = current_bid if trade.side == "BUY" else current_ask

        if trade.side == "BUY":
            price_delta = current_price - entry
            current_r = price_delta / initial_risk_dist
            trade.max_favorable_r = max(trade.max_favorable_r, round(current_r, 2))
            trade.max_adverse_r = min(trade.max_adverse_r, round(current_r, 2))

            if current_bid <= sl:
                is_closed = True
                exit_price = sl
                exit_reason = "SL_HIT"
                trade.status = "CLOSED_SL"
            elif tp is not None and current_bid >= tp:
                is_closed = True
                exit_price = tp
                exit_reason = "TP_HIT"
                trade.status = "CLOSED_TP"

        else:  # SELL
            price_delta = entry - current_price
            current_r = price_delta / initial_risk_dist
            trade.max_favorable_r = max(trade.max_favorable_r, round(current_r, 2))
            trade.max_adverse_r = min(trade.max_adverse_r, round(current_r, 2))

            if current_ask >= sl:
                is_closed = True
                exit_price = sl
                exit_reason = "SL_HIT"
                trade.status = "CLOSED_SL"
            elif tp is not None and current_ask <= tp:
                is_closed = True
                exit_price = tp
                exit_reason = "TP_HIT"
                trade.status = "CLOSED_TP"

        if is_closed and exit_price is not None:
            trade.exit_price = round(exit_price, digits)
            trade.exit_reason = exit_reason
            trade.closed_at = datetime.now(timezone.utc)

            pnl_dist = (exit_price - entry) if trade.side == "BUY" else (entry - exit_price)
            trade.realized_pips = round(pnl_dist / pip_size, 2)
            trade.realized_pnl = round(pnl_dist * trade.lot_size * contract_size, 2)
            trade.realized_r = round(pnl_dist / initial_risk_dist, 2)

            event = TradeEvent(
                paper_trade_id=trade.id,
                event_type="ORDER_CLOSED",
                price=trade.exit_price,
                details={
                    "exit_reason": exit_reason,
                    "exit_price": trade.exit_price,
                    "realized_pnl": trade.realized_pnl,
                    "realized_pips": trade.realized_pips,
                    "realized_r": trade.realized_r
                }
            )
            db.add(event)

        await db.commit()
        await db.refresh(trade)
        return trade

    @classmethod
    async def manual_close(
        cls,
        db: AsyncSession,
        trade: PaperTrade,
        current_price: float
    ) -> PaperTrade:
        if trade.status != "OPEN":
            return trade

        spec = get_instrument_spec(trade.symbol) or {
            "digits": 5,
            "pip_size": 0.0001,
            "contract_size": 100000.0
        }
        digits = spec["digits"]
        contract_size = spec["contract_size"]
        pip_size = spec["pip_size"]

        entry = trade.entry_price
        sl = trade.stop_loss
        initial_risk_dist = abs(entry - sl) or 0.0001

        trade.status = "CLOSED_MANUAL"
        trade.exit_price = round(current_price, digits)
        trade.exit_reason = "MANUAL_CLOSE"
        trade.closed_at = datetime.now(timezone.utc)

        pnl_dist = (current_price - entry) if trade.side == "BUY" else (entry - current_price)
        trade.realized_pips = round(pnl_dist / pip_size, 2)
        trade.realized_pnl = round(pnl_dist * trade.lot_size * contract_size, 2)
        trade.realized_r = round(pnl_dist / initial_risk_dist, 2)

        event = TradeEvent(
            paper_trade_id=trade.id,
            event_type="MANUAL_CLOSE",
            price=trade.exit_price,
            details={
                "exit_price": trade.exit_price,
                "realized_pnl": trade.realized_pnl,
                "realized_r": trade.realized_r
            }
        )
        db.add(event)
        await db.commit()
        await db.refresh(trade)
        return trade

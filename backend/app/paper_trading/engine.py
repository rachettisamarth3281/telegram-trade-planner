from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PaperTrade, TradeEvent, Signal
from app.paper_trading.enums import TradeStatus, ExitReason, PositionSizingMode
from app.paper_trading.models import PaperTradeConfig, PositionSizingConfig, TradeTickEvaluationResult
from app.paper_trading.position_sizing import PositionSizingService
from app.risk.models import RiskCalculationResult
from app.risk.enums import Side
from app.utils.instrument_specs import get_instrument_spec

class PaperTradeEngine:
    """
    Virtual Paper Trading Simulation Engine.
    
    IMPORTANT:
    - NEVER executes real broker orders or live trades.
    - Manages lifecycle of virtual paper positions (PENDING, OPEN, TP_HIT, SL_HIT, etc.).
    - Tracks high/low excursion metrics, P&L, and realized R-multiples.
    - Enforces idempotency per signal.
    """

    def __init__(self, position_sizing_service: Optional[PositionSizingService] = None):
        self.position_sizing_service = position_sizing_service or PositionSizingService()

    async def create_paper_trade(
        self,
        db: AsyncSession,
        signal: Signal,
        risk_result: Optional[RiskCalculationResult] = None,
        config: Optional[PaperTradeConfig] = None,
    ) -> PaperTrade:
        """
        Creates a virtual simulated trade from a validated Signal.
        Guarantees idempotency (will not duplicate trade for the same signal).
        """
        cfg = config or PaperTradeConfig()

        # 1. Idempotency check: Do not create duplicate trades for the same signal
        stmt = select(PaperTrade).where(PaperTrade.signal_id == signal.id)
        existing = await db.scalar(stmt)
        if existing:
            return existing

        # 2. Validate essential fields
        symbol = signal.symbol or "UNKNOWN"
        raw_side = (signal.side or "").upper().strip()
        side = "BUY" if raw_side in ("BUY", "LONG") else "SELL" if raw_side in ("SELL", "SHORT") else None

        entry_price = float(signal.entry_price or 0.0)
        stop_loss = float(signal.stop_loss or 0.0)
        take_profit = float(signal.take_profit) if signal.take_profit is not None else None

        # Determine risk distance
        if risk_result and risk_result.risk_distance is not None:
            risk_distance = float(risk_result.risk_distance)
        elif side == "BUY":
            risk_distance = entry_price - stop_loss
        elif side == "SELL":
            risk_distance = stop_loss - entry_price
        else:
            risk_distance = 0.0

        # Check for invalid geometry / zero risk
        is_invalid = False
        rejection_reason = None
        if not side:
            is_invalid = True
            rejection_reason = "Invalid or missing side"
        elif entry_price <= 0.0 or stop_loss <= 0.0:
            is_invalid = True
            rejection_reason = "Non-positive entry price or stop loss"
        elif risk_distance <= 0.0:
            is_invalid = True
            rejection_reason = "Zero or negative risk distance"

        now = datetime.now(timezone.utc)

        if is_invalid:
            trade = PaperTrade(
                signal_id=signal.id,
                symbol=symbol,
                side=side or "BUY",
                status=TradeStatus.INVALID.value,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_distance=risk_distance if risk_distance > 0 else 0.0,
                position_size=0.0,
                risk_amount=0.0,
                exit_reason=ExitReason.INVALID.value,
                closed_at=now,
            )
            db.add(trade)
            await db.flush()
            event = TradeEvent(
                paper_trade_id=trade.id,
                event_type="TRADE_INVALID",
                price=entry_price,
                details={"reason": rejection_reason}
            )
            db.add(event)
            await db.commit()
            await db.refresh(trade)
            return trade

        # 3. Calculate Position Size and Monetary Risk
        risk_dist_d = Decimal(str(risk_distance))
        pos_result = self.position_sizing_service.calculate_position_size(
            symbol=symbol,
            risk_distance=risk_dist_d,
            config=cfg.position_sizing
        )

        position_size = float(pos_result.position_size)
        risk_amount = float(pos_result.risk_amount)

        # 4. Create Simulated Trade
        initial_status = TradeStatus.OPEN.value if cfg.immediate_entry else TradeStatus.PENDING.value
        opened_at = now if cfg.immediate_entry else None

        trade = PaperTrade(
            signal_id=signal.id,
            symbol=symbol,
            side=side,
            order_type=signal.order_type or "MARKET",
            status=initial_status,
            entry_price=entry_price,  # Recorded as signal entry price
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_distance=risk_distance,
            position_size=position_size,
            risk_amount=risk_amount,
            target_r_multiple=float(cfg.default_target_r),
            opened_at=opened_at,
            highest_favorable_price=entry_price if cfg.immediate_entry else None,
            lowest_favorable_price=entry_price if cfg.immediate_entry else None,
        )
        db.add(trade)
        await db.flush()

        event = TradeEvent(
            paper_trade_id=trade.id,
            event_type="ORDER_OPENED" if cfg.immediate_entry else "ORDER_PENDING",
            price=entry_price,
            details={
                "symbol": symbol,
                "side": side,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "position_size": position_size,
                "risk_amount": risk_amount,
                "risk_distance": risk_distance,
                "sizing_details": pos_result.details,
            }
        )
        db.add(event)
        await db.commit()
        await db.refresh(trade)
        return trade

    async def evaluate_tick(
        self,
        db: AsyncSession,
        trade: PaperTrade,
        current_bid: float,
        current_ask: float,
    ) -> Optional[PaperTrade]:
        """
        Evaluates a market tick against an active simulated position.
        Checks for SL/TP hits, tracks excursion metrics (MFE/MAE), and computes P&L and Realized R.
        """
        if trade.status != TradeStatus.OPEN.value:
            return trade

        spec = get_instrument_spec(trade.symbol) or {
            "digits": 5,
            "pip_size": 0.0001,
            "contract_size": 1.0,
        }
        digits = spec.get("digits", 5)
        pip_size = spec.get("pip_size", 0.0001)
        contract_size = spec.get("contract_size", 1.0)

        entry = trade.entry_price
        sl = trade.stop_loss
        tp = trade.take_profit
        risk_dist = trade.risk_distance or abs(entry - sl) or 0.0001

        is_closed = False
        exit_price: Optional[float] = None
        exit_reason: Optional[str] = None
        now = datetime.now(timezone.utc)

        if trade.side == "BUY":
            price_for_pnl = current_bid
            # Update Excursion Metrics
            if trade.highest_favorable_price is None or current_bid > trade.highest_favorable_price:
                trade.highest_favorable_price = current_bid
            if trade.lowest_favorable_price is None or current_bid < trade.lowest_favorable_price:
                trade.lowest_favorable_price = current_bid

            current_r = (current_bid - entry) / risk_dist
            trade.max_favorable_r = max(trade.max_favorable_r, round(current_r, 2))
            trade.max_adverse_r = min(trade.max_adverse_r, round(current_r, 2))

            # Stop Loss Hit
            if current_bid <= sl:
                is_closed = True
                exit_price = sl
                exit_reason = ExitReason.STOP_LOSS.value
                trade.status = TradeStatus.SL_HIT.value
            # Take Profit Hit
            elif tp is not None and current_bid >= tp:
                is_closed = True
                exit_price = tp
                exit_reason = ExitReason.TAKE_PROFIT.value
                trade.status = TradeStatus.TP_HIT.value

        else:  # SELL
            price_for_pnl = current_ask
            # Update Excursion Metrics
            if trade.highest_favorable_price is None or current_ask < trade.highest_favorable_price:
                trade.highest_favorable_price = current_ask
            if trade.lowest_favorable_price is None or current_ask > trade.lowest_favorable_price:
                trade.lowest_favorable_price = current_ask

            current_r = (entry - current_ask) / risk_dist
            trade.max_favorable_r = max(trade.max_favorable_r, round(current_r, 2))
            trade.max_adverse_r = min(trade.max_adverse_r, round(current_r, 2))

            # Stop Loss Hit
            if current_ask >= sl:
                is_closed = True
                exit_price = sl
                exit_reason = ExitReason.STOP_LOSS.value
                trade.status = TradeStatus.SL_HIT.value
            # Take Profit Hit
            elif tp is not None and current_ask <= tp:
                is_closed = True
                exit_price = tp
                exit_reason = ExitReason.TAKE_PROFIT.value
                trade.status = TradeStatus.TP_HIT.value

        if is_closed and exit_price is not None:
            trade.exit_price = round(exit_price, digits)
            trade.exit_reason = exit_reason
            trade.closed_at = now

            # P&L calculation: BUY (exit - entry), SELL (entry - exit)
            pnl_price_delta = (exit_price - entry) if trade.side == "BUY" else (entry - exit_price)
            trade.realized_pips = round(pnl_price_delta / pip_size, 2)
            trade.realized_pnl = round(pnl_price_delta * trade.position_size * contract_size, 2)

            # Realized R calculation: Realized PnL / Initial Risk Amount (or price delta / risk distance)
            if trade.risk_amount and trade.risk_amount > 0:
                trade.realized_r = round(trade.realized_pnl / trade.risk_amount, 2)
            else:
                trade.realized_r = round(pnl_price_delta / risk_dist, 2)

            event = TradeEvent(
                paper_trade_id=trade.id,
                event_type="ORDER_CLOSED",
                price=trade.exit_price,
                details={
                    "status": trade.status,
                    "exit_reason": trade.exit_reason,
                    "exit_price": trade.exit_price,
                    "realized_pnl": trade.realized_pnl,
                    "realized_pips": trade.realized_pips,
                    "realized_r": trade.realized_r,
                }
            )
            db.add(event)

        await db.commit()
        await db.refresh(trade)
        return trade

    async def manual_close(
        self,
        db: AsyncSession,
        trade: PaperTrade,
        current_price: float,
    ) -> PaperTrade:
        """Manually close an open paper position at specified market price."""
        if trade.status != TradeStatus.OPEN.value:
            return trade

        spec = get_instrument_spec(trade.symbol) or {
            "digits": 5,
            "pip_size": 0.0001,
            "contract_size": 1.0,
        }
        digits = spec.get("digits", 5)
        pip_size = spec.get("pip_size", 0.0001)
        contract_size = spec.get("contract_size", 1.0)

        entry = trade.entry_price
        risk_dist = trade.risk_distance or abs(entry - trade.stop_loss) or 0.0001

        trade.status = TradeStatus.MANUAL_CLOSED.value
        trade.exit_price = round(current_price, digits)
        trade.exit_reason = ExitReason.MANUAL.value
        trade.closed_at = datetime.now(timezone.utc)

        pnl_delta = (current_price - entry) if trade.side == "BUY" else (entry - current_price)
        trade.realized_pips = round(pnl_delta / pip_size, 2)
        trade.realized_pnl = round(pnl_delta * trade.position_size * contract_size, 2)

        if trade.risk_amount and trade.risk_amount > 0:
            trade.realized_r = round(trade.realized_pnl / trade.risk_amount, 2)
        else:
            trade.realized_r = round(pnl_delta / risk_dist, 2)

        event = TradeEvent(
            paper_trade_id=trade.id,
            event_type="MANUAL_CLOSE",
            price=trade.exit_price,
            details={
                "status": trade.status,
                "exit_reason": trade.exit_reason,
                "exit_price": trade.exit_price,
                "realized_pnl": trade.realized_pnl,
                "realized_r": trade.realized_r,
            }
        )
        db.add(event)
        await db.commit()
        await db.refresh(trade)
        return trade

    async def cancel_trade(
        self,
        db: AsyncSession,
        trade: PaperTrade,
        reason: Optional[str] = None
    ) -> PaperTrade:
        """Cancel a pending or open simulated position."""
        trade.status = TradeStatus.CANCELLED.value
        trade.exit_reason = ExitReason.CANCELLED.value
        trade.closed_at = datetime.now(timezone.utc)

        event = TradeEvent(
            paper_trade_id=trade.id,
            event_type="ORDER_CANCELLED",
            price=trade.entry_price,
            details={"reason": reason or "User requested cancellation"}
        )
        db.add(event)
        await db.commit()
        await db.refresh(trade)
        return trade

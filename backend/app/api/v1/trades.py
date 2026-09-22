from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.database import get_db
from app.database.models import PaperTrade, TradeEvent
from app.schemas.trade_schema import (
    PaperTradeResponse,
    TradeEventResponse,
    TradeAuditProvenance,
    SimulateTickRequest
)
from app.services.paper_trade_engine import PaperTradeEngine
from app.services.price_monitor import price_monitor
from app.api.websockets import ws_manager

router = APIRouter(prefix="/trades", tags=["Paper Trades"])

def build_trade_provenance(t: PaperTrade) -> TradeAuditProvenance:
    """Builds the complete traceable calculation and decision audit record for a trade."""
    sig = t.signal
    risk_dist = round(abs(t.entry_price - t.stop_loss), 5)
    pip_mult = 10.0 if t.symbol == "XAUUSD" else (100.0 if "JPY" in t.symbol else 10000.0)
    risk_pips = round(risk_dist * pip_mult, 1)

    is_provider_tp = bool(sig and sig.take_profit and abs((sig.take_profit or 0.0) - (t.take_profit or 0.0)) < 0.0001)
    tp_source = "PROVIDER" if is_provider_tp else "CALCULATED"
    
    if is_provider_tp:
        tp_formula = f"Provider Explicit Target ({t.take_profit})"
    else:
        op = "+" if t.side == "BUY" else "-"
        tp_formula = f"Entry ({t.entry_price}) {op} (Risk Distance {risk_dist} × {t.target_r_multiple}R) = {t.take_profit}"

    return TradeAuditProvenance(
        original_telegram_message=sig.raw_message if sig else "Direct Paper Trade Injection",
        telegram_message_id=sig.telegram_message_id if sig else None,
        source_chat_title=sig.source_chat_title if sig else "Simulation",
        extracted_values={
            "symbol": t.symbol,
            "side": t.side,
            "order_type": t.order_type,
            "entry_price": t.entry_price,
            "stop_loss": t.stop_loss,
            "provider_tp": sig.take_profit if sig else None,
        },
        sl_source="PROVIDER",
        tp_source=tp_source,
        tp_formula=tp_formula,
        initial_risk_distance=risk_dist,
        initial_risk_pips=risk_pips,
        initial_risk_amount_usd=t.risk_amount or 100.0,
        risk_reward_ratio=f"1:{t.target_r_multiple:.1f}",
        validation_status=sig.status if sig else "VALID",
        decision_reason=sig.rejection_reason if (sig and sig.rejection_reason) else "VALID_SIGNAL: Directional SL/TP geometry verified with zero fabricated levels",
        closing_price=t.exit_price,
        closing_reason=t.exit_reason,
        final_realized_r=t.realized_r if t.status.startswith("CLOSED") else None
    )

@router.get("", response_model=List[PaperTradeResponse])
async def list_trades(
    status: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List paper trades with complete financial calculation provenance."""
    query = select(PaperTrade).options(
        selectinload(PaperTrade.events),
        selectinload(PaperTrade.signal)
    ).order_by(desc(PaperTrade.opened_at)).limit(limit)

    if status:
        if status.upper() == "OPEN":
            query = query.where(PaperTrade.status == "OPEN")
        elif status.upper() == "CLOSED":
            query = query.where(PaperTrade.status.startswith("CLOSED"))
    if symbol:
        query = query.where(PaperTrade.symbol == symbol.upper())

    result = await db.execute(query)
    trades = result.scalars().all()

    response = []
    for t in trades:
        evs = [
            TradeEventResponse(
                id=e.id,
                event_type=e.event_type,
                price=e.price,
                details=e.details,
                created_at=e.created_at
            ) for e in sorted(t.events, key=lambda x: x.created_at)
        ]

        response.append(PaperTradeResponse(
            id=t.id,
            signal_id=t.signal_id,
            account_id="primary_account",
            symbol=t.symbol,
            side=t.side,
            status=t.status,
            lot_size=t.lot_size,
            entry_price=t.entry_price,
            effective_sl=t.stop_loss,
            active_tp=t.take_profit,
            target_r_multiple=t.target_r_multiple,
            opened_at=t.opened_at,
            closed_at=t.closed_at,
            exit_price=t.exit_price,
            exit_reason=t.exit_reason,
            realized_pnl_usd=t.realized_pnl,
            realized_pnl_pips=t.realized_pips,
            realized_r_multiple=t.realized_r,
            max_favorable_r=t.max_favorable_r,
            max_adverse_r=t.max_adverse_r,
            events=evs,
            provenance=build_trade_provenance(t)
        ))

    return response

@router.get("/{trade_id}", response_model=PaperTradeResponse)
async def get_trade(trade_id: str, db: AsyncSession = Depends(get_db)):
    """Get single paper trade detail with complete audit provenance."""
    result = await db.execute(
        select(PaperTrade).options(
            selectinload(PaperTrade.events),
            selectinload(PaperTrade.signal)
        ).where(PaperTrade.id == trade_id)
    )
    trade = result.scalars().first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    evs = [
        TradeEventResponse(
            id=e.id,
            event_type=e.event_type,
            price=e.price,
            details=e.details,
            created_at=e.created_at
        ) for e in sorted(trade.events, key=lambda x: x.created_at)
    ]

    return PaperTradeResponse(
        id=trade.id,
        signal_id=trade.signal_id,
        account_id="primary_account",
        symbol=trade.symbol,
        side=trade.side,
        status=trade.status,
        lot_size=trade.lot_size,
        entry_price=trade.entry_price,
        effective_sl=trade.stop_loss,
        active_tp=trade.take_profit,
        target_r_multiple=trade.target_r_multiple,
        opened_at=trade.opened_at,
        closed_at=trade.closed_at,
        exit_price=trade.exit_price,
        exit_reason=trade.exit_reason,
        realized_pnl_usd=trade.realized_pnl,
        realized_pnl_pips=trade.realized_pips,
        realized_r_multiple=trade.realized_r,
        max_favorable_r=trade.max_favorable_r,
        max_adverse_r=trade.max_adverse_r,
        events=evs,
        provenance=build_trade_provenance(trade)
    )

@router.post("/{trade_id}/close", response_model=PaperTradeResponse)
async def manual_close_trade(trade_id: str, db: AsyncSession = Depends(get_db)):
    """Manually close an open paper trade at the current market price."""
    trade = await db.get(PaperTrade, trade_id, options=[selectinload(PaperTrade.events)])
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "OPEN":
        raise HTTPException(status_code=400, detail="Trade is already closed")

    quote = price_monitor.get_price(trade.symbol)
    exit_price = quote["bid"] if trade.side == "BUY" else quote["ask"]

    updated_trade = await PaperTradeEngine.manual_close(db, trade, exit_price)

    await ws_manager.broadcast("TRADE_CLOSED", {
        "trade_id": updated_trade.id,
        "symbol": updated_trade.symbol,
        "exit_reason": "MANUAL_CLOSE",
        "realized_pnl_usd": updated_trade.realized_pnl,
        "realized_r_multiple": updated_trade.realized_r
    })

    return await get_trade(trade_id, db)

@router.post("/simulate-tick")
async def simulate_tick(payload: SimulateTickRequest, db: AsyncSession = Depends(get_db)):
    """
    Push a simulated market price tick.
    Evaluates all open paper trades for that symbol and triggers SL/TP closures.
    """
    quote = price_monitor.set_price(payload.symbol, payload.bid, payload.ask)

    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.symbol == payload.symbol.upper(),
            PaperTrade.status == "OPEN"
        )
    )
    open_trades = result.scalars().all()

    closed_count = 0
    for trade in open_trades:
        evaluated = await PaperTradeEngine.evaluate_trade_tick(
            db=db,
            trade=trade,
            current_bid=quote["bid"],
            current_ask=quote["ask"]
        )
        if evaluated and evaluated.status != "OPEN":
            closed_count += 1
            await ws_manager.broadcast("TRADE_CLOSED", {
                "trade_id": evaluated.id,
                "symbol": evaluated.symbol,
                "exit_reason": evaluated.exit_reason,
                "realized_pnl_usd": evaluated.realized_pnl,
                "realized_r_multiple": evaluated.realized_r
            })

    await ws_manager.broadcast("PRICE_UPDATE", {
        "symbol": payload.symbol.upper(),
        "bid": quote["bid"],
        "ask": quote["ask"]
    })

    return {
        "symbol": payload.symbol.upper(),
        "quote": quote,
        "evaluated_trades": len(open_trades),
        "closed_trades": closed_count
    }

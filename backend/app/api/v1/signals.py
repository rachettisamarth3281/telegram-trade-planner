from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.database.models import Signal, PaperTrade, SystemEvent
from app.schemas.signal_schema import (
    SignalIngestRequest,
    SignalResponse,
    SignalParsePreviewResponse,
    CalculatedMetricResponse
)
from app.services.signal_parser import SignalParser
from app.services.signal_normalizer import SignalNormalizer
from app.services.signal_validator import SignalValidator
from app.services.calculation_engine import CalculationEngine
from app.services.paper_trade_engine import PaperTradeEngine
from app.api.websockets import ws_manager

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.post("/parse-preview", response_model=SignalParsePreviewResponse)
async def parse_preview(payload: SignalIngestRequest):
    """Interactive Sandbox: parse and preview metrics without saving to database."""
    parsed = SignalParser.parse(payload.raw_text)
    norm = SignalNormalizer.normalize(parsed)
    val = SignalValidator.validate(norm)

    metrics_resp = None
    if val.effective_sl is not None and norm.entry_price is not None and val.is_valid:
        calc = CalculationEngine.calculate(
            signal=norm,
            effective_sl=val.effective_sl,
            sl_source=val.sl_source or "PROVIDER",
            account_balance=10000.0,
            risk_percent=1.0
        )
        metrics_resp = CalculatedMetricResponse(
            effective_sl=calc.effective_sl,
            sl_source=calc.sl_source,
            risk_price_diff=calc.risk_price_diff,
            risk_pips=calc.risk_pips,
            r1_target=calc.r1_target,
            r1_5_target=calc.r1_5_target,
            r2_target=calc.r2_target,
            r3_target=calc.r3_target,
            r_targets=calc.r_targets,
            provider_tp_rrrs=calc.provider_tp_rrrs,
            suggested_lot_size=calc.suggested_lot_size,
            risk_amount_usd=calc.risk_amount_usd
        )

    return SignalParsePreviewResponse(
        raw_text=payload.raw_text,
        symbol=norm.symbol if norm.symbol != "UNKNOWN" else None,
        side=norm.side if norm.side != "UNKNOWN" else None,
        order_type=norm.order_type,
        entry_price=norm.entry_price,
        provider_sl=norm.provider_sl,
        provider_tps=norm.provider_tps,
        parser_confidence=norm.confidence,
        is_valid=val.is_valid,
        validation_status=val.status,
        rejection_reasons=val.rejection_reasons,
        warnings=val.warning_notes,
        metrics=metrics_resp
    )

@router.post("/ingest", response_model=SignalResponse)
async def ingest_signal(payload: SignalIngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingests a trading signal preserving original text and running full pipeline:
    Save -> Parse -> Normalize -> Validate -> Calculate -> Paper Trade.
    """
    now = datetime.now(timezone.utc)

    # 1. Parse & Normalize
    parsed = SignalParser.parse(payload.raw_text)
    norm = SignalNormalizer.normalize(parsed)

    # 2. Validate
    val = SignalValidator.validate(norm)

    # 3. Create Signal record preserving exact raw message
    import json
    rejection_str = "; ".join(val.rejection_reasons) if val.rejection_reasons else None
    targets_json_str = json.dumps([{"price": p} for p in norm.provider_tps]) if norm.provider_tps else None
    signal = Signal(
        telegram_message_id=payload.telegram_message_id,
        source_chat_id=payload.channel_id or "VIP_CHANNEL",
        source_chat_title=payload.channel_title or "VIP Forex Signals",
        sender_id=payload.sender_id,
        source=payload.source or "MANUAL_INGEST",
        raw_message=payload.raw_text,
        symbol=norm.symbol if norm.symbol != "UNKNOWN" else None,
        side=norm.side if norm.side != "UNKNOWN" else None,
        order_type=norm.order_type,
        entry_price=norm.entry_price,
        entry_price_upper=norm.entry_price_upper,
        entry_zone_low=norm.entry_zone_low,
        entry_zone_high=norm.entry_zone_high,
        entry_reference_price=norm.entry_price,
        stop_loss=norm.provider_sl,
        take_profit=norm.provider_tps[0] if len(norm.provider_tps) >= 1 else None,
        take_profits={"tps": norm.provider_tps} if norm.provider_tps else None,
        targets_json=targets_json_str,
        parser_confidence=norm.confidence,
        status=val.status,
        rejection_reason=rejection_str,
        received_at=now
    )
    db.add(signal)
    await db.flush()

    metrics_resp = None
    created_trade_id = None

    # 4. If Valid, perform Calculation & create Paper Trade
    if val.is_valid and val.effective_sl is not None and norm.entry_price is not None:
        calc = CalculationEngine.calculate(
            signal=norm,
            effective_sl=val.effective_sl,
            sl_source=val.sl_source or "PROVIDER",
            account_balance=10000.0,
            risk_percent=1.0
        )

        target_r = payload.target_r_multiple or 2.0
        trade = PaperTrade(
            signal_id=signal.id,
            symbol=signal.symbol or "XAUUSD",
            side=signal.side or "BUY",
            status="OPEN",
            lot_size=calc.suggested_lot_size or 1.0,
            entry_price=signal.entry_price or 0.0,
            stop_loss=val.effective_sl,
            take_profit=signal.take_profit or calc.r2_target,
            target_r_multiple=target_r,
            opened_at=now
        )
        db.add(trade)
        await db.flush()
        created_trade_id = trade.id

        metrics_resp = CalculatedMetricResponse(
            effective_sl=calc.effective_sl,
            sl_source=calc.sl_source,
            risk_price_diff=calc.risk_price_diff,
            risk_pips=calc.risk_pips,
            r1_target=calc.r1_target,
            r1_5_target=calc.r1_5_target,
            r2_target=calc.r2_target,
            r3_target=calc.r3_target,
            r_targets=calc.r_targets,
            provider_tp_rrrs=calc.provider_tp_rrrs,
            suggested_lot_size=calc.suggested_lot_size,
            risk_amount_usd=calc.risk_amount_usd
        )

    # 4b. Generate/Update V1 Trade Plan
    from app.trade_plan.service import TradePlanService
    plan_service = TradePlanService()
    try:
        await plan_service.generate_or_update_plan(db, signal)
    except Exception as e:
        # Logging or soft failure so ingestion does not crash
        pass

    await db.commit()

    # 5. WebSocket Broadcast
    await ws_manager.broadcast("NEW_SIGNAL", {
        "signal_id": signal.id,
        "symbol": signal.symbol,
        "side": signal.side,
        "status": signal.status,
        "raw_text": signal.raw_message,
        "paper_trade_id": created_trade_id
    })

    return SignalResponse(
        id=signal.id,
        raw_message_id=signal.id,
        raw_text=signal.raw_message,
        symbol=signal.symbol,
        side=signal.side,
        order_type=signal.order_type,
        entry_price=signal.entry_price,
        provider_sl=signal.stop_loss,
        provider_tps=norm.provider_tps,
        parser_confidence=signal.parser_confidence,
        validation_status=signal.status,
        rejection_reason=signal.rejection_reason,
        created_at=signal.created_at,
        metrics=metrics_resp,
        paper_trade_id=created_trade_id
    )

@router.get("", response_model=List[SignalResponse])
async def list_signals(
    status: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve signals with filtering and pagination."""
    query = select(Signal).options(
        selectinload(Signal.paper_trades)
    ).order_by(desc(Signal.created_at)).offset(offset).limit(limit)

    if status:
        query = query.where(Signal.status == status)
    if symbol:
        query = query.where(Signal.symbol == symbol.upper())

    result = await db.execute(query)
    signals = result.scalars().all()

    response = []
    for s in signals:
        tps = []
        if s.take_profits and "tps" in s.take_profits:
            tps = s.take_profits["tps"]
        elif s.take_profit:
            tps.append(s.take_profit)

        trade_id = s.paper_trades[0].id if s.paper_trades else None

        response.append(SignalResponse(
            id=s.id,
            raw_message_id=s.id,
            raw_text=s.raw_message,
            symbol=s.symbol,
            side=s.side,
            order_type=s.order_type,
            entry_price=s.entry_price,
            provider_sl=s.stop_loss,
            provider_tps=tps,
            parser_confidence=s.parser_confidence,
            validation_status=s.status,
            rejection_reason=s.rejection_reason,
            created_at=s.created_at,
            metrics=None,
            paper_trade_id=trade_id
        ))

    return response

@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal_detail(signal_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve deep detail for a single signal including calculation metrics."""
    result = await db.execute(
        select(Signal).options(
            selectinload(Signal.paper_trades).selectinload(PaperTrade.events)
        ).where(Signal.id == signal_id)
    )
    s = result.scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")

    tps = []
    if s.take_profits and "tps" in s.take_profits:
        tps = s.take_profits["tps"]
    elif s.take_profit:
        tps.append(s.take_profit)

    trade_id = s.paper_trades[0].id if s.paper_trades else None

    # Reconstruct metrics if valid
    metrics_resp = None
    if s.status == "VALID" and s.entry_price is not None and s.stop_loss is not None:
        from app.services.calculation_engine import CalculationEngine
        from app.schemas.signal_schema import NormalizedSignal
        norm = NormalizedSignal(
            symbol=s.symbol or "XAUUSD",
            side=s.side or "BUY",
            order_type=s.order_type or "MARKET",
            entry_price=s.entry_price,
            provider_sl=s.stop_loss,
            provider_tps=tps,
            confidence=s.parser_confidence or 1.0,
            has_explicit_levels=True
        )
        calc = CalculationEngine.calculate(
            signal=norm,
            effective_sl=s.stop_loss,
            sl_source="PROVIDER",
            account_balance=10000.0,
            risk_percent=1.0
        )
        metrics_resp = CalculatedMetricResponse(
            effective_sl=calc.effective_sl,
            sl_source=calc.sl_source,
            risk_price_diff=calc.risk_price_diff,
            risk_pips=calc.risk_pips,
            r1_target=calc.r1_target,
            r1_5_target=calc.r1_5_target,
            r2_target=calc.r2_target,
            r3_target=calc.r3_target,
            r_targets=calc.r_targets,
            provider_tp_rrrs=calc.provider_tp_rrrs,
            suggested_lot_size=calc.suggested_lot_size,
            risk_amount_usd=calc.risk_amount_usd
        )

    return SignalResponse(
        id=s.id,
        raw_message_id=s.id,
        raw_text=s.raw_message,
        symbol=s.symbol,
        side=s.side,
        order_type=s.order_type,
        entry_price=s.entry_price,
        provider_sl=s.stop_loss,
        provider_tps=tps,
        parser_confidence=s.parser_confidence,
        validation_status=s.status,
        rejection_reason=s.rejection_reason,
        created_at=s.created_at,
        metrics=metrics_resp,
        paper_trade_id=trade_id
    )

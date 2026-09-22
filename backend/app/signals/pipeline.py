import traceback
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Signal, PaperTrade, SystemEvent
from app.parser.engine import SignalParserEngine
from app.parser.states import ParsingState
from app.risk import (
    RiskEngine,
    RiskEngineConfig,
    RiskCalculationInput,
    RiskCalculationResult,
    RiskValidationStatus,
    TPSource,
    SLSource,
)
from app.paper_trading.engine import PaperTradeEngine
from app.signals.enums import DecisionReason
from app.signals.models import PipelineProcessRequest, PipelineExecutionResult
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("signal_pipeline")

from app.signals.correlator import SignalCorrelator

class SignalPipelineService:
    """
    Unified end-to-end Signal-to-Paper-Trade Processing Pipeline with Multi-Message Correlation.
    
    Flow:
    1. Ingestion & Preservation of unaltered raw message (with Idempotency).
    2. Real-world Message Classification (SIGNAL_ENTRY, SL_UPDATE, TARGET_UPDATE, TRADE_MANAGEMENT, PROVIDER_OUTCOME, PLANNING, NOISE).
    3. Deterministic Entry Zone parsing & Abbreviated Range expansion.
    4. Multi-Message Signal Assembly & Correlation.
    5. Deterministic Validation & SL/TP + RR calculation with RiskEngine.
    6. Virtual Paper Trade Creation via PaperTradeEngine (Simulation only).
    7. Dual Outcome recording (Provider Claims vs Independently Calculated Market Outcomes).
    """

    def __init__(
        self,
        paper_trade_engine: Optional[PaperTradeEngine] = None,
        correlator: Optional[SignalCorrelator] = None
    ):
        self.paper_trade_engine = paper_trade_engine or PaperTradeEngine()
        self.correlator = correlator or SignalCorrelator(paper_trade_engine=self.paper_trade_engine)

    async def process_message(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest,
    ) -> PipelineExecutionResult:
        return await self.correlator.correlate_and_process(db, request)
        now = datetime.now(timezone.utc)
        raw_text = (request.raw_text or "").strip()

        # 1. Idempotency Check (prevent duplicate processing if message_id provided)
        if request.source_chat_id and request.telegram_message_id:
            stmt = (
                select(Signal)
                .options(selectinload(Signal.paper_trades))
                .where(
                    Signal.source_chat_id == str(request.source_chat_id),
                    Signal.telegram_message_id == request.telegram_message_id
                )
            )
            existing = await db.scalar(stmt)
            if existing:
                logger.warning(
                    "DUPLICATE_SIGNAL_DETECTED",
                    signal_id=existing.id,
                    chat_id=request.source_chat_id,
                    message_id=request.telegram_message_id
                )
                existing_trade_id = existing.paper_trades[0].id if existing.paper_trades else None
                return PipelineExecutionResult(
                    signal_id=existing.id,
                    trade_id=existing_trade_id,
                    decision_reason=DecisionReason.DUPLICATE_SIGNAL,
                    symbol=existing.symbol,
                    side=existing.side,
                    entry_price=existing.entry_price,
                    stop_loss=existing.stop_loss,
                    status=existing.status,
                    is_paper_trade_created=existing_trade_id is not None,
                )

        # 2. Persist Signal Record (Guaranteed to preserve exact original text)
        signal = Signal(
            telegram_message_id=request.telegram_message_id,
            source_chat_id=str(request.source_chat_id) if request.source_chat_id else "VIP_CHANNEL",
            source_chat_title=request.source_chat_title or "VIP Trading Signals",
            sender_id=request.sender_id,
            sender_username=request.sender_username,
            source=request.source,
            raw_message=raw_text,
            status="RECEIVED",
            received_at=now,
        )
        db.add(signal)
        await db.flush()

        try:
            # 3. Parse Unstructured Text
            parsed = SignalParserEngine.parse(raw_text)

            # Check for Unsupported Symbol or Ambiguous Signal
            if not parsed.symbol:
                decision_reason = DecisionReason.UNSUPPORTED_SYMBOL
                rejection_reasons = ["Unsupported or unidentifiable instrument symbol"]
                signal.status = "REJECTED"
                signal.rejection_reason = "; ".join(rejection_reasons)
                await db.commit()
                return self._build_rejected_result(signal, decision_reason, rejection_reasons)

            if parsed.diagnostics and parsed.diagnostics.state == ParsingState.UNKNOWN:
                decision_reason = DecisionReason.AMBIGUOUS_SIGNAL
                rejection_reasons = ["Ambiguous or unparseable trading signal structure"]
                signal.status = "REJECTED"
                signal.rejection_reason = "; ".join(rejection_reasons)
                await db.commit()
                return self._build_rejected_result(signal, decision_reason, rejection_reasons)

            # 4. Deterministic Risk & SL/TP Engine Calculation
            target_r = Decimal(str(request.target_r_multiple or settings.DEFAULT_TP_R_MULTIPLE))
            r_multiples = [Decimal(str(r)) for r in settings.ALTERNATIVE_TP_R_MULTIPLES]

            risk_config = RiskEngineConfig(
                min_rr=Decimal(str(getattr(settings, "MIN_RR", 1.5))),
                r_multiples=r_multiples,
                default_tp_r=target_r,
                allow_strategy_sl=settings.CONFIGURED_STRATEGY_SL_ENABLED,
            )

            calc_input = RiskCalculationInput(
                symbol=parsed.symbol,
                side=parsed.side,
                entry_price=parsed.entry_price,
                stop_loss=parsed.stop_loss,
                provider_take_profit=parsed.take_profit,
                provider_take_profits=parsed.take_profits if parsed.take_profits else None,
                config=risk_config,
            )

            risk_result = RiskEngine.calculate(calc_input)

            # 5. Determine Explicit Decision Reason
            decision_reason, rejection_reasons = self._evaluate_decision_reason(parsed, risk_result)

            is_valid = risk_result.is_valid and decision_reason in (DecisionReason.VALID_SIGNAL, DecisionReason.PAPER_TRADE_CREATED, DecisionReason.LOW_RR)

            # 6. Update Signal Record
            signal.symbol = parsed.symbol
            signal.side = parsed.side
            signal.entry_price = float(risk_result.entry_price) if risk_result.entry_price else parsed.entry_price
            signal.stop_loss = float(risk_result.effective_sl) if risk_result.effective_sl else parsed.stop_loss
            signal.take_profit = float(risk_result.effective_tp) if risk_result.effective_tp else parsed.take_profit
            signal.take_profits = {
                "r_targets": {k: float(v) for k, v in risk_result.r_targets.items()},
                "provider_tps": [m.to_dict() for m in risk_result.provider_tps_metrics],
                "tp_source": risk_result.tp_source.value,
            }
            signal.parser_confidence = parsed.diagnostics.confidence if parsed.diagnostics else 0.0

            trade_id = None
            if is_valid:
                signal.status = "VALID"
                signal.rejection_reason = None

                # 7. Create Paper Trade (Simulated position)
                if settings.PAPER_TRADING_ENABLED:
                    trade = await self.paper_trade_engine.create_paper_trade(
                        db=db,
                        signal=signal,
                        risk_result=risk_result
                    )
                    trade_id = trade.id
                    decision_reason = DecisionReason.PAPER_TRADE_CREATED
                    signal.status = "PAPER_TRADE_CREATED"
                else:
                    decision_reason = DecisionReason.EXECUTION_DISABLED
            else:
                signal.status = "REJECTED"
                signal.rejection_reason = "; ".join(rejection_reasons) if rejection_reasons else decision_reason.value

            # 8. Record System Audit Event
            audit_event = SystemEvent(
                component="signal_pipeline",
                event_type="SIGNAL_PROCESSED",
                severity="INFO" if is_valid else "WARNING",
                message=f"Signal {signal.id} processed with decision: {decision_reason.value}",
                payload={
                    "signal_id": signal.id,
                    "trade_id": trade_id,
                    "decision_reason": decision_reason.value,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "effective_tp": signal.take_profit,
                    "tp_source": risk_result.tp_source.value,
                    "risk_distance": float(risk_result.risk_distance) if risk_result.risk_distance else None,
                    "risk_reward_ratio": float(risk_result.risk_reward_ratio) if risk_result.risk_reward_ratio else None,
                    "rejection_reasons": rejection_reasons,
                    "warning_flags": risk_result.warning_flags,
                }
            )
            db.add(audit_event)
            await db.commit()
            await db.refresh(signal)

            # 9. Broadcast to WebSocket Subscribers (if active)
            try:
                from app.api.websockets import ws_manager
                await ws_manager.broadcast("SIGNAL_PROCESSED", {
                    "signal_id": signal.id,
                    "trade_id": trade_id,
                    "decision_reason": decision_reason.value,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "status": signal.status,
                })
            except Exception:
                pass

            return PipelineExecutionResult(
                signal_id=signal.id,
                trade_id=trade_id,
                decision_reason=decision_reason,
                symbol=signal.symbol,
                side=signal.side,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                provider_tp=parsed.take_profit,
                calculated_tp=float(risk_result.effective_tp) if risk_result.tp_source == TPSource.CALCULATED else None,
                tp_source=risk_result.tp_source.value,
                risk_distance=float(risk_result.risk_distance) if risk_result.risk_distance else None,
                risk_reward_ratio=float(risk_result.risk_reward_ratio) if risk_result.risk_reward_ratio else None,
                r_targets={k: float(v) for k, v in risk_result.r_targets.items()},
                status=signal.status,
                rejection_reasons=rejection_reasons,
                warning_flags=risk_result.warning_flags,
                parser_confidence=signal.parser_confidence,
                is_paper_trade_created=trade_id is not None,
            )

        except Exception as exc:
            # Safe exception handling: Never expose raw stack traces to users
            logger.error("SIGNAL_PIPELINE_ERROR", signal_id=signal.id, error=str(exc))
            rejection_reasons = [f"Internal signal validation error: {str(exc)}"]
            signal.status = "ERROR"
            signal.rejection_reason = "Internal processing error occurred"

            error_event = SystemEvent(
                component="signal_pipeline",
                event_type="PIPELINE_ERROR",
                severity="ERROR",
                message=f"Pipeline error for signal {signal.id}",
                payload={"error": str(exc), "trace": traceback.format_exc()}
            )
            db.add(error_event)
            await db.commit()

            return PipelineExecutionResult(
                signal_id=signal.id,
                trade_id=None,
                decision_reason=DecisionReason.AMBIGUOUS_SIGNAL,
                status="ERROR",
                rejection_reasons=rejection_reasons,
                is_paper_trade_created=False,
            )

    def _evaluate_decision_reason(self, parsed: Any, risk_result: RiskCalculationResult) -> tuple[DecisionReason, List[str]]:
        """Maps validation errors to explicit auditable decision reasons."""
        rejection_reasons = list(risk_result.rejection_reasons)

        if not parsed.side:
            return DecisionReason.INVALID_DIRECTION, ["Missing or invalid direction (must be BUY or SELL)"]

        if parsed.entry_price is None or parsed.entry_price <= 0:
            return DecisionReason.MISSING_ENTRY, ["Missing or non-positive entry price"]

        if parsed.stop_loss is None:
            return DecisionReason.MISSING_SL, ["Stop loss is missing; zero-assumption policy forbids fabricating an SL"]

        # Check geometry errors from risk result
        if not risk_result.is_valid:
            for r in rejection_reasons:
                if "Stop loss must be" in r or "SL" in r:
                    return DecisionReason.INVALID_SL, rejection_reasons
                if "entry price" in r.lower():
                    return DecisionReason.INVALID_ENTRY, rejection_reasons
                if "side" in r.lower():
                    return DecisionReason.INVALID_DIRECTION, rejection_reasons
            return DecisionReason.INVALID_SL, rejection_reasons

        # Valid signal
        if "LOW_RR" in [w.split(":")[0] for w in risk_result.warning_flags]:
            return DecisionReason.LOW_RR, []

        return DecisionReason.VALID_SIGNAL, []

    def _build_rejected_result(
        self,
        signal: Signal,
        decision_reason: DecisionReason,
        rejection_reasons: List[str]
    ) -> PipelineExecutionResult:
        return PipelineExecutionResult(
            signal_id=signal.id,
            trade_id=None,
            decision_reason=decision_reason,
            symbol=signal.symbol,
            side=signal.side,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            status=signal.status,
            rejection_reasons=rejection_reasons,
            is_paper_trade_created=False,
        )

# Global singleton
signal_pipeline_service = SignalPipelineService()

import json
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Signal, PaperTrade, TradeEvent, SystemEvent
from app.parser.classifier import MessageClassifier, MessageClassification, ManagementAction, ClassificationResult
from app.parser.zone_parser import EntryZoneParser, EntryReferencePolicy
from app.parser.engine import SignalParserEngine
from app.risk.engine import RiskEngine
from app.risk.models import RiskEngineConfig, RiskCalculationInput
from app.paper_trading.engine import PaperTradeEngine
from app.trade_plan.service import TradePlanService
from app.signals.enums import DecisionReason
from app.signals.models import PipelineProcessRequest, PipelineExecutionResult
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("signal_correlator")

class SignalCorrelator:
    """
    Deterministic Signal Assembly and Multi-Message Correlation Engine.
    
    Correlates sequences of Telegram messages:
    SIGNAL_ENTRY -> SL_UPDATE -> TARGET_UPDATE -> TRADE_MANAGEMENT -> PROVIDER_OUTCOME
    into unified Signal, TradePlan, and PaperTrade instances with strict temporal validation.
    """

    def __init__(
        self,
        paper_trade_engine: Optional[PaperTradeEngine] = None,
        trade_plan_service: Optional[TradePlanService] = None,
        correlation_window_seconds: int = 900,  # 15 minutes
        entry_policy: EntryReferencePolicy = EntryReferencePolicy.ZONE_MIDPOINT
    ):
        self.paper_trade_engine = paper_trade_engine or PaperTradeEngine()
        self.trade_plan_service = trade_plan_service or TradePlanService()
        self.correlation_window_seconds = correlation_window_seconds
        self.entry_policy = entry_policy

    async def correlate_and_process(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest
    ) -> PipelineExecutionResult:
        now = datetime.now(timezone.utc)
        raw_text = (request.raw_text or "").strip()
        chat_id = str(request.source_chat_id) if request.source_chat_id else "SHUBHAM_VIP"

        # 1. Classify Message
        classification = MessageClassifier.classify(raw_text)
        msg_type = classification.message_type

        # Check if standard parser finds valid full signal (e.g. forex pairs like BUY EURUSD 1.0850 SL 1.0800 TP 1.0950)
        parsed_std = SignalParserEngine.parse(raw_text)
        if parsed_std.symbol and parsed_std.side and parsed_std.entry_price:
            msg_type = MessageClassification.SIGNAL_ENTRY

        # Check for explicit unsupported symbols (e.g. BUY UNKNOWNSYMBOL @ 100 SL 90)
        raw_u = raw_text.upper()
        if ("BUY " in raw_u or "SELL " in raw_u) and not parsed_std.symbol and not any(k in raw_u for k in ("GOLD", "XAU", "BTC", "ETH", "OIL", "US30", "NAS100")):
            sig = Signal(
                telegram_message_id=request.telegram_message_id,
                source_chat_id=chat_id,
                raw_message=raw_text,
                message_type=MessageClassification.SIGNAL_ENTRY.value,
                status="REJECTED",
                rejection_reason="Unsupported or unidentifiable instrument symbol",
                received_at=now
            )
            db.add(sig)
            await db.commit()
            return PipelineExecutionResult(
                signal_id=sig.id,
                decision_reason=DecisionReason.UNSUPPORTED_SYMBOL,
                status="REJECTED",
                rejection_reasons=["Unsupported or unidentifiable instrument symbol"],
                is_paper_trade_created=False
            )

        # 2. Check Idempotency
        if request.source_chat_id and request.telegram_message_id:
            stmt = select(Signal).options(selectinload(Signal.paper_trades)).where(
                Signal.source_chat_id == chat_id,
                Signal.telegram_message_id == request.telegram_message_id
            )
            existing = await db.scalar(stmt)
            if existing:
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

        # 3. Handle by Message Classification
        if msg_type == MessageClassification.SIGNAL_ENTRY:
            return await self._handle_signal_entry(db, request, raw_text, chat_id, classification, now, parsed_std)

        elif msg_type == MessageClassification.SL_UPDATE:
            return await self._handle_sl_update(db, request, raw_text, chat_id, classification, now)

        elif msg_type == MessageClassification.TARGET_UPDATE:
            return await self._handle_target_update(db, request, raw_text, chat_id, classification, now)

        elif msg_type == MessageClassification.TRADE_MANAGEMENT:
            return await self._handle_trade_management(db, request, raw_text, chat_id, classification, now)

        elif msg_type == MessageClassification.PROVIDER_OUTCOME:
            return await self._handle_provider_outcome(db, request, raw_text, chat_id, classification, now)

        else:
            # PLANNING, COMMENTARY, ADD_ENTRY, PROMOTIONAL, NOISE, MEDIA_ONLY
            return await self._handle_context_message(db, request, raw_text, chat_id, classification, now)

    async def _handle_signal_entry(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest,
        raw_text: str,
        chat_id: str,
        classification: ClassificationResult,
        now: datetime,
        parsed_std: Optional[Any] = None
    ) -> PipelineExecutionResult:
        if parsed_std is None:
            parsed_std = SignalParserEngine.parse(raw_text)

        raw_u = raw_text.upper()
        symbol = parsed_std.symbol or ("BTCUSD" if "BTC" in raw_u else "XAUUSD")
        side = parsed_std.side or ("BUY" if ("BUY" in raw_u or "LONG" in raw_u) else "SELL")

        # Parse Entry Zone
        raw_entry = classification.details.get("raw_entry", "")
        if raw_entry:
            zone_low, zone_high, ref_price, prices = EntryZoneParser.parse_zone(raw_entry, side=side, policy=self.entry_policy)
        else:
            ref_price = float(parsed_std.entry_price or 0.0)
            zone_low = ref_price
            zone_high = float(parsed_std.entry_price_upper or ref_price)

        if ref_price <= 0.0 and parsed_std.entry_price:
            ref_price = float(parsed_std.entry_price)
            zone_low = ref_price
            zone_high = float(parsed_std.entry_price_upper or ref_price)

        # Detect Execution Style
        exec_style = "FAST" if ("FAST" in raw_u or "NOW" in raw_u or "BIG LOT" in raw_u) else "ZONE"

        has_sl = parsed_std.stop_loss is not None
        initial_status = "VALID" if has_sl else "WAITING_FOR_DETAILS"

        signal = Signal(
            telegram_message_id=request.telegram_message_id,
            source_chat_id=chat_id,
            source_chat_title=request.source_chat_title or "Shubham Vip Club 👑",
            sender_id=request.sender_id,
            sender_username=request.sender_username,
            source=request.source,
            raw_message=raw_text,
            symbol=symbol,
            side=side,
            entry_price=ref_price,
            entry_zone_low=zone_low,
            entry_zone_high=zone_high,
            entry_reference_price=ref_price,
            execution_style=exec_style,
            stop_loss=float(parsed_std.stop_loss) if has_sl else None,
            take_profit=float(parsed_std.take_profit) if parsed_std.take_profit else None,
            message_type=MessageClassification.SIGNAL_ENTRY.value,
            status=initial_status,
            parser_confidence=0.95,
            received_at=now,
        )
        db.add(signal)
        await db.flush()

        if has_sl:
            # SL is already provided in the same message -> assemble trade plan & trade immediately
            return await self._assemble_and_create_trade(db, signal, request)

        # Generate initial TradePlan in WAITING_FOR_SL / INCOMPLETE status
        plan = await self.trade_plan_service.generate_or_update_plan(db, signal)

        # Buffered waiting for separate SL message
        await db.commit()
        return PipelineExecutionResult(
            signal_id=signal.id,
            decision_reason=DecisionReason.WAITING_FOR_SL,
            symbol=symbol,
            side=side,
            entry_price=ref_price,
            status=signal.status,
            is_paper_trade_created=False
        )

    async def _handle_sl_update(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest,
        raw_text: str,
        chat_id: str,
        classification: ClassificationResult,
        now: datetime
    ) -> PipelineExecutionResult:
        # 1. Find recent pending signal in WAITING_FOR_DETAILS within correlation window
        window_start = now - timedelta(seconds=self.correlation_window_seconds)
        stmt = (
            select(Signal)
            .options(selectinload(Signal.paper_trades))
            .where(
                Signal.source_chat_id == chat_id,
                Signal.status == "WAITING_FOR_DETAILS",
                Signal.received_at >= window_start
            )
            .order_by(desc(Signal.received_at))
        )
        candidates = list((await db.scalars(stmt)).all())

        if not candidates:
            # Also check if this is an SL shift on an active OPEN trade
            open_trade_stmt = (
                select(PaperTrade)
                .join(PaperTrade.signal)
                .options(selectinload(PaperTrade.signal))
                .where(
                    Signal.source_chat_id == chat_id,
                    PaperTrade.status == "OPEN",
                    PaperTrade.opened_at >= window_start
                )
                .order_by(desc(PaperTrade.opened_at))
            )
            open_trades = list((await db.scalars(open_trade_stmt)).all())
            if len(open_trades) == 1:
                active_trade = open_trades[0]
                raw_sl = classification.details.get("raw_sl", "")
                new_sl = EntryZoneParser.parse_sl_value(raw_sl, side=active_trade.side)
                active_trade.stop_loss = new_sl
                active_trade.trailing_sl = new_sl
                db.add(active_trade)
                event = TradeEvent(
                    paper_trade_id=active_trade.id,
                    event_type="SL_UPDATE_SHIFT",
                    price=new_sl,
                    details={"new_sl": new_sl, "raw_message": raw_text}
                )
                db.add(event)
                await db.commit()
                return PipelineExecutionResult(
                    signal_id=active_trade.signal_id,
                    trade_id=active_trade.id,
                    decision_reason=DecisionReason.TRADE_UPDATED,
                    symbol=active_trade.symbol,
                    side=active_trade.side,
                    stop_loss=new_sl,
                    status="OPEN",
                    is_paper_trade_created=True
                )

            # No matching candidate -> Flag AMBIGUOUS_CONTINUATION
            sig = Signal(
                telegram_message_id=request.telegram_message_id,
                source_chat_id=chat_id,
                raw_message=raw_text,
                message_type=MessageClassification.SL_UPDATE.value,
                status="AMBIGUOUS_CONTINUATION",
                rejection_reason="No matching pending signal found within correlation window",
                received_at=now
            )
            db.add(sig)
            await db.commit()
            return PipelineExecutionResult(
                signal_id=sig.id,
                decision_reason=DecisionReason.AMBIGUOUS_CONTINUATION,
                status="AMBIGUOUS_CONTINUATION",
                is_paper_trade_created=False
            )

        if len(candidates) > 1:
            # Multiple conflicting pending signals -> Ambiguity guard
            sig = Signal(
                telegram_message_id=request.telegram_message_id,
                source_chat_id=chat_id,
                raw_message=raw_text,
                message_type=MessageClassification.SL_UPDATE.value,
                status="AMBIGUOUS_CONTINUATION",
                rejection_reason="Multiple conflicting pending signal candidates exist",
                received_at=now
            )
            db.add(sig)
            await db.commit()
            return PipelineExecutionResult(
                signal_id=sig.id,
                decision_reason=DecisionReason.AMBIGUOUS_CONTINUATION,
                status="AMBIGUOUS_CONTINUATION",
                is_paper_trade_created=False
            )

        # 2. Correlate with the single pending signal!
        parent_signal = candidates[0]
        raw_sl = classification.details.get("raw_sl", "")
        parsed_sl = EntryZoneParser.parse_sl_value(raw_sl, side=parent_signal.side)

        parent_signal.stop_loss = parsed_sl
        parent_signal.status = "VALID"
        db.add(parent_signal)

        # Record this SL update message as child signal linked to parent
        child_sig = Signal(
            telegram_message_id=request.telegram_message_id,
            source_chat_id=chat_id,
            raw_message=raw_text,
            parent_signal_id=parent_signal.id,
            message_type=MessageClassification.SL_UPDATE.value,
            status="CORRELATED_SL",
            received_at=now
        )
        db.add(child_sig)
        await db.flush()

        # 3. Create Virtual Paper Trade now that SL is available
        return await self._assemble_and_create_trade(db, parent_signal, request)

    async def _handle_target_update(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest,
        raw_text: str,
        chat_id: str,
        classification: ClassificationResult,
        now: datetime
    ) -> PipelineExecutionResult:
        targets = classification.details.get("targets", [])
        targets_json_str = json.dumps([{"label": f"TP{idx+1}", "price": p} for idx, p in enumerate(targets)])

        # Match active trade or signal
        window_start = now - timedelta(seconds=self.correlation_window_seconds * 2)
        trade_stmt = (
            select(PaperTrade)
            .join(PaperTrade.signal)
            .options(selectinload(PaperTrade.signal))
            .where(
                Signal.source_chat_id == chat_id,
                PaperTrade.status.in_(("OPEN", "PENDING")),
                PaperTrade.opened_at >= window_start
            )
            .order_by(desc(PaperTrade.opened_at))
        )
        active_trades = list((await db.scalars(trade_stmt)).all())
        trade = active_trades[0] if active_trades else None

        sig = Signal(
            telegram_message_id=request.telegram_message_id,
            source_chat_id=chat_id,
            raw_message=raw_text,
            parent_signal_id=trade.signal_id if trade else None,
            message_type=MessageClassification.TARGET_UPDATE.value,
            targets_json=targets_json_str,
            status="CORRELATED_TARGETS",
            received_at=now
        )
        db.add(sig)

        if trade:
            trade.signal.targets_json = targets_json_str
            if targets and trade.take_profit is None:
                trade.take_profit = targets[0]
            db.add(trade)
            db.add(trade.signal)
            event = TradeEvent(
                paper_trade_id=trade.id,
                event_type="TARGETS_CONFIGURED",
                price=targets[0] if targets else trade.entry_price,
                details={"targets": targets, "raw_message": raw_text}
            )
            db.add(event)

        await db.commit()
        return PipelineExecutionResult(
            signal_id=sig.id,
            trade_id=trade.id if trade else None,
            decision_reason=DecisionReason.TRADE_UPDATED if trade else DecisionReason.VALID_SIGNAL,
            status="TARGETS_RECORDED",
            is_paper_trade_created=trade is not None
        )

    async def _handle_trade_management(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest,
        raw_text: str,
        chat_id: str,
        classification: ClassificationResult,
        now: datetime
    ) -> PipelineExecutionResult:
        action = classification.management_action or ManagementAction.BOOK_PROFIT

        # Find active open trade in this chat
        trade_stmt = (
            select(PaperTrade)
            .join(PaperTrade.signal)
            .options(selectinload(PaperTrade.signal))
            .where(
                Signal.source_chat_id == chat_id,
                PaperTrade.status == "OPEN"
            )
            .order_by(desc(PaperTrade.opened_at))
        )
        active_trades = list((await db.scalars(trade_stmt)).all())
        trade = active_trades[0] if active_trades else None

        sig = Signal(
            telegram_message_id=request.telegram_message_id,
            source_chat_id=chat_id,
            raw_message=raw_text,
            parent_signal_id=trade.signal_id if trade else None,
            message_type=MessageClassification.TRADE_MANAGEMENT.value,
            management_events_json=json.dumps({"action": action.value, "text": raw_text, "time": now.isoformat()}),
            status="CORRELATED_MANAGEMENT",
            received_at=now
        )
        db.add(sig)

        if trade:
            if action in (ManagementAction.RISK_FREE, ManagementAction.MOVE_SL_TO_ENTRY):
                # Move Stop Loss to Entry Price (Break Even / C2C)
                trade.stop_loss = trade.entry_price
                trade.trailing_sl = trade.entry_price
                trade.is_risk_free_moved = True
                db.add(trade)
                event = TradeEvent(
                    paper_trade_id=trade.id,
                    event_type="MOVE_SL_TO_ENTRY",
                    price=trade.entry_price,
                    details={"action": action.value, "raw_message": raw_text}
                )
                db.add(event)

            elif action in (ManagementAction.EXIT, ManagementAction.PARTIAL_CLOSE):
                event = TradeEvent(
                    paper_trade_id=trade.id,
                    event_type="PROVIDER_MANAGEMENT_EXIT",
                    price=trade.entry_price,
                    details={"action": action.value, "raw_message": raw_text}
                )
                db.add(event)

            elif action == ManagementAction.BOOK_PROFIT:
                event = TradeEvent(
                    paper_trade_id=trade.id,
                    event_type="BOOK_PROFIT_INSTRUCTION",
                    price=trade.entry_price,
                    details={"action": action.value, "raw_message": raw_text}
                )
                db.add(event)

        await db.commit()
        return PipelineExecutionResult(
            signal_id=sig.id,
            trade_id=trade.id if trade else None,
            decision_reason=DecisionReason.TRADE_UPDATED if trade else DecisionReason.VALID_SIGNAL,
            status="MANAGEMENT_RECORDED",
            is_paper_trade_created=trade is not None
        )

    async def _handle_provider_outcome(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest,
        raw_text: str,
        chat_id: str,
        classification: ClassificationResult,
        now: datetime
    ) -> PipelineExecutionResult:
        pips = classification.pips_claimed
        outcome_detail = classification.details.get("outcome", f"{pips} PIPS" if pips else "OUTCOME_CLAIM")

        # Find active trade
        trade_stmt = (
            select(PaperTrade)
            .join(PaperTrade.signal)
            .options(selectinload(PaperTrade.signal))
            .where(
                Signal.source_chat_id == chat_id,
                PaperTrade.status.in_(("OPEN", "TP_HIT", "SL_HIT"))
            )
            .order_by(desc(PaperTrade.created_at))
        )
        active_trades = list((await db.scalars(trade_stmt)).all())
        trade = active_trades[0] if active_trades else None

        sig = Signal(
            telegram_message_id=request.telegram_message_id,
            source_chat_id=chat_id,
            raw_message=raw_text,
            parent_signal_id=trade.signal_id if trade else None,
            message_type=MessageClassification.PROVIDER_OUTCOME.value,
            provider_outcomes_json=json.dumps({"pips": pips, "outcome": outcome_detail, "time": now.isoformat()}),
            status="CORRELATED_OUTCOME",
            received_at=now
        )
        db.add(sig)

        if trade:
            if pips is not None and (trade.provider_claimed_pips is None or pips > trade.provider_claimed_pips):
                trade.provider_claimed_pips = pips
            trade.provider_claimed_status = outcome_detail
            db.add(trade)
            event = TradeEvent(
                paper_trade_id=trade.id,
                event_type="PROVIDER_CLAIMED_OUTCOME",
                price=trade.entry_price,
                details={"pips_claimed": pips, "outcome": outcome_detail, "raw_message": raw_text}
            )
            db.add(event)

        await db.commit()
        return PipelineExecutionResult(
            signal_id=sig.id,
            trade_id=trade.id if trade else None,
            decision_reason=DecisionReason.TRADE_UPDATED if trade else DecisionReason.VALID_SIGNAL,
            status="OUTCOME_RECORDED",
            is_paper_trade_created=trade is not None
        )

    async def _handle_context_message(
        self,
        db: AsyncSession,
        request: PipelineProcessRequest,
        raw_text: str,
        chat_id: str,
        classification: ClassificationResult,
        now: datetime
    ) -> PipelineExecutionResult:
        sig = Signal(
            telegram_message_id=request.telegram_message_id,
            source_chat_id=chat_id,
            raw_message=raw_text,
            message_type=classification.message_type.value,
            status="AUDITED_CONTEXT",
            received_at=now
        )
        db.add(sig)
        await db.commit()
        return PipelineExecutionResult(
            signal_id=sig.id,
            decision_reason=DecisionReason.AUDITED_CONTEXT,
            status="AUDITED_CONTEXT",
            is_paper_trade_created=False
        )

    async def _assemble_and_create_trade(
        self,
        db: AsyncSession,
        signal: Signal,
        request: PipelineProcessRequest
    ) -> PipelineExecutionResult:
        # Run Deterministic Risk Engine
        target_r = Decimal(str(request.target_r_multiple or settings.DEFAULT_TP_R_MULTIPLE))
        r_multiples = [Decimal(str(r)) for r in settings.ALTERNATIVE_TP_R_MULTIPLES]

        risk_config = RiskEngineConfig(
            min_rr=Decimal(str(getattr(settings, "MIN_RR", 1.5))),
            r_multiples=r_multiples,
            default_tp_r=target_r,
            allow_strategy_sl=settings.CONFIGURED_STRATEGY_SL_ENABLED,
        )

        calc_input = RiskCalculationInput(
            symbol=signal.symbol,
            side=signal.side,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            provider_take_profit=signal.take_profit,
            config=risk_config,
        )

        risk_result = RiskEngine.calculate(calc_input)

        if not risk_result.is_valid:
            signal.status = "REJECTED"
            signal.rejection_reason = "; ".join(risk_result.rejection_reasons)
            await db.commit()
            return PipelineExecutionResult(
                signal_id=signal.id,
                decision_reason=DecisionReason.INVALID_SL,
                symbol=signal.symbol,
                side=signal.side,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                status="REJECTED",
                rejection_reasons=risk_result.rejection_reasons,
                is_paper_trade_created=False
            )

        # Generate Primary V1 TradePlan with true raw Telegram provenance
        plan = await self.trade_plan_service.generate_or_update_plan(db, signal)

        # Set effective TP for simulated paper trade engine
        if signal.take_profit is None and risk_result.effective_tp is not None:
            signal.take_profit = float(risk_result.effective_tp)

        # Create Virtual Paper Trade (for simulation/historical replay)
        trade = await self.paper_trade_engine.create_paper_trade(
            db=db,
            signal=signal,
            risk_result=risk_result
        )

        # Set entry zone values on trade
        trade.entry_zone_low = signal.entry_zone_low
        trade.entry_zone_high = signal.entry_zone_high
        db.add(trade)

        signal.status = "PAPER_TRADE_CREATED"
        db.add(signal)

        # Emit System Audit Event
        system_event = SystemEvent(
            event_type="SIGNAL_PROCESSED",
            component="signal_pipeline",
            severity="INFO",
            message=f"Signal {signal.id} processed into trade {trade.id}",
            payload={
                "signal_id": signal.id,
                "trade_id": trade.id,
                "decision_reason": "PAPER_TRADE_CREATED",
                "symbol": signal.symbol,
                "side": signal.side,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "risk_distance": float(risk_result.risk_distance) if risk_result.risk_distance else None,
            }
        )
        db.add(system_event)

        await db.commit()
        await db.refresh(signal)
        await db.refresh(trade)

        r_targets_float = {k: float(v) for k, v in risk_result.r_targets.items()}

        return PipelineExecutionResult(
            signal_id=signal.id,
            trade_id=trade.id,
            decision_reason=DecisionReason.PAPER_TRADE_CREATED,
            symbol=signal.symbol,
            side=signal.side,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            provider_tp=float(signal.take_profit) if (signal.take_profit is not None and risk_result.tp_source.value == "PROVIDER") else None,
            calculated_tp=float(risk_result.effective_tp) if risk_result.effective_tp else None,
            tp_source=risk_result.tp_source.value,
            risk_distance=float(risk_result.risk_distance) if risk_result.risk_distance else None,
            risk_reward_ratio=float(risk_result.risk_reward_ratio) if risk_result.risk_reward_ratio else None,
            r_targets=r_targets_float,
            status=signal.status,
            parser_confidence=0.95,
            is_paper_trade_created=True
        )

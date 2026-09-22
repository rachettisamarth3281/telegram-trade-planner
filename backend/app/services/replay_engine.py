import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.signals.pipeline import SignalPipelineService
from app.signals.models import PipelineProcessRequest, PipelineExecutionResult
from app.parser.classifier import MessageClassifier, MessageClassification
from app.utils.logging import get_logger

logger = get_logger("replay_engine")

class TelegramExportReplayEngine:
    """
    Historical Telegram Export Replay Engine.
    
    Guarantees:
    - Strictly chronological replay (No lookahead bias).
    - Replays multi-message signal sequences (Entry -> SL -> Targets -> Risk Free -> Outcome).
    - Tracks both Provider-Claimed outcomes and Market-Calculated outcomes.
    """

    def __init__(self, pipeline_service: Optional[SignalPipelineService] = None):
        self.pipeline_service = pipeline_service or SignalPipelineService()

    async def replay_messages(
        self,
        db: AsyncSession,
        messages: List[Dict[str, Any]],
        chat_id: str = "SHUBHAM_VIP_REPLAY"
    ) -> Dict[str, Any]:
        """
        Replays a chronological list of exported messages through the pipeline.
        Each message dict should contain: 'id', 'text', 'date'.
        """
        # Sort chronologically by date/id if available
        sorted_msgs = sorted(messages, key=lambda m: m.get("id", 0))

        results: List[PipelineExecutionResult] = []
        stats = {
            "total_messages": len(sorted_msgs),
            "classified_types": {},
            "signals_created": 0,
            "trades_created": 0,
            "sl_updates_correlated": 0,
            "targets_configured": 0,
            "management_events": 0,
            "provider_outcomes": 0,
            "context_and_noise": 0,
            "sequences": []
        }

        current_sequence = []

        for msg in sorted_msgs:
            msg_id = msg.get("id")
            raw_text = msg.get("text", "")
            
            # Classify
            classification = MessageClassifier.classify(raw_text)
            c_type = classification.message_type.value
            stats["classified_types"][c_type] = stats["classified_types"].get(c_type, 0) + 1

            req = PipelineProcessRequest(
                raw_text=raw_text,
                telegram_message_id=msg_id,
                source_chat_id=chat_id,
                source_chat_title="Shubham Vip Club 👑 Replay",
                source="TELEGRAM_EXPORT_REPLAY"
            )

            res = await self.pipeline_service.process_message(db, req)
            results.append(res)

            if c_type == MessageClassification.SIGNAL_ENTRY.value:
                stats["signals_created"] += 1
                if res.is_paper_trade_created:
                    stats["trades_created"] += 1
                current_sequence = [{"id": msg_id, "type": c_type, "text": raw_text}]
            elif c_type == MessageClassification.SL_UPDATE.value:
                stats["sl_updates_correlated"] += 1
                if res.is_paper_trade_created:
                    stats["trades_created"] += 1
                current_sequence.append({"id": msg_id, "type": c_type, "text": raw_text})
            elif c_type == MessageClassification.TARGET_UPDATE.value:
                stats["targets_configured"] += 1
                current_sequence.append({"id": msg_id, "type": c_type, "text": raw_text})
            elif c_type == MessageClassification.TRADE_MANAGEMENT.value:
                stats["management_events"] += 1
                current_sequence.append({"id": msg_id, "type": c_type, "text": raw_text})
            elif c_type == MessageClassification.PROVIDER_OUTCOME.value:
                stats["provider_outcomes"] += 1
                current_sequence.append({"id": msg_id, "type": c_type, "text": raw_text})
                if "done" in raw_text.lower() or "hit" in raw_text.lower() or "reversed" in raw_text.lower() or "book all" in raw_text.lower():
                    stats["sequences"].append(list(current_sequence))
            else:
                stats["context_and_noise"] += 1

        stats["execution_results"] = [r.to_dict() for r in results]
        return stats


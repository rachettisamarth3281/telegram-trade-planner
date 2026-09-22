from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.signals.enums import DecisionReason

@dataclass
class PipelineProcessRequest:
    raw_text: str
    telegram_message_id: Optional[int] = None
    source_chat_id: Optional[str] = None
    source_chat_title: Optional[str] = None
    sender_id: Optional[str] = None
    sender_username: Optional[str] = None
    source: str = "TELEGRAM"
    target_r_multiple: Optional[float] = None

@dataclass
class PipelineExecutionResult:
    signal_id: str
    trade_id: Optional[str] = None
    decision_reason: DecisionReason = DecisionReason.VALID_SIGNAL
    symbol: Optional[str] = None
    side: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    provider_tp: Optional[float] = None
    calculated_tp: Optional[float] = None
    tp_source: str = "NONE"
    risk_distance: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    r_targets: Dict[str, float] = field(default_factory=dict)
    status: str = "RECEIVED"
    rejection_reasons: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)
    parser_confidence: float = 0.0
    is_paper_trade_created: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "trade_id": self.trade_id,
            "decision_reason": self.decision_reason.value if isinstance(self.decision_reason, DecisionReason) else str(self.decision_reason),
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "provider_tp": self.provider_tp,
            "calculated_tp": self.calculated_tp,
            "tp_source": self.tp_source,
            "risk_distance": self.risk_distance,
            "risk_reward_ratio": self.risk_reward_ratio,
            "r_targets": self.r_targets,
            "status": self.status,
            "rejection_reasons": self.rejection_reasons,
            "warning_flags": self.warning_flags,
            "parser_confidence": self.parser_confidence,
            "is_paper_trade_created": self.is_paper_trade_created,
        }

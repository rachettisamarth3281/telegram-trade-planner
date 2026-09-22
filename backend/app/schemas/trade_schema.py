from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TradeEventResponse(BaseModel):
    id: str
    event_type: str
    price: Optional[float]
    details: Optional[Dict[str, Any]]
    created_at: datetime

class TradeAuditProvenance(BaseModel):
    original_telegram_message: str = Field(description="Exact verbatim Telegram text that created this trade")
    telegram_message_id: Optional[int] = Field(default=None)
    source_chat_title: Optional[str] = Field(default=None)
    extracted_values: Dict[str, Any] = Field(description="Normalized tokens extracted by parser")
    sl_source: str = Field(description="PROVIDER, STRATEGY, or NONE")
    tp_source: str = Field(description="PROVIDER, CALCULATED, or NONE")
    tp_formula: str = Field(description="Explicit mathematical formula used to determine TP")
    initial_risk_distance: float = Field(description="Absolute difference |Entry - SL|")
    initial_risk_pips: float = Field(description="Risk converted to instrument pips")
    initial_risk_amount_usd: float = Field(description="Virtual dollar risk allocated")
    risk_reward_ratio: str = Field(description="Ratio e.g. 1:2.0")
    validation_status: str = Field(description="VALID, INVALID, or SKIPPED")
    decision_reason: str = Field(description="Why the signal was accepted or rejected")
    closing_price: Optional[float] = Field(default=None, description="Exact market price that triggered trade closure")
    closing_reason: Optional[str] = Field(default=None, description="Why the trade closed (TP_HIT, SL_HIT, MANUAL)")
    final_realized_r: Optional[float] = Field(default=None, description="Realized R multiplier outcome")

class PaperTradeResponse(BaseModel):
    id: str
    signal_id: str
    account_id: str
    symbol: str
    side: str
    status: str
    lot_size: float
    entry_price: float
    effective_sl: float
    active_tp: Optional[float]
    target_r_multiple: float
    opened_at: datetime
    closed_at: Optional[datetime]
    exit_price: Optional[float]
    exit_reason: Optional[str]
    realized_pnl_usd: float
    realized_pnl_pips: float
    realized_r_multiple: float
    max_favorable_r: float
    max_adverse_r: float
    events: Optional[List[TradeEventResponse]] = []
    provenance: Optional[TradeAuditProvenance] = None

class SimulateTickRequest(BaseModel):
    symbol: str
    bid: float
    ask: Optional[float] = None

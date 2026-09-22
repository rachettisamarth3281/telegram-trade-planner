from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SignalIngestRequest(BaseModel):
    raw_text: str = Field(..., description="Raw text of the Telegram signal")
    telegram_message_id: Optional[int] = None
    channel_id: Optional[str] = "VIP_CHANNEL"
    channel_title: Optional[str] = "VIP Forex Signals"
    sender_id: Optional[str] = None
    source: Optional[str] = "MANUAL_INGEST"
    target_r_multiple: Optional[float] = 2.0

class CalculatedMetricResponse(BaseModel):
    effective_sl: float
    sl_source: str
    risk_price_diff: float
    risk_pips: float
    r1_target: float
    r1_5_target: float
    r2_target: float
    r3_target: float
    r_targets: Dict[str, float]
    provider_tp_rrrs: Dict[str, float]
    suggested_lot_size: Optional[float]
    risk_amount_usd: Optional[float]

class SignalResponse(BaseModel):
    id: str
    raw_message_id: str
    raw_text: str
    symbol: Optional[str]
    side: Optional[str]
    order_type: str
    entry_price: Optional[float]
    provider_sl: Optional[float]
    provider_tps: List[float]
    parser_confidence: float
    validation_status: str
    rejection_reason: Optional[str]
    created_at: datetime
    metrics: Optional[CalculatedMetricResponse] = None
    paper_trade_id: Optional[str] = None

class SignalParsePreviewResponse(BaseModel):
    raw_text: str
    symbol: Optional[str]
    side: Optional[str]
    order_type: str
    entry_price: Optional[float]
    provider_sl: Optional[float]
    provider_tps: List[float]
    parser_confidence: float
    is_valid: bool
    validation_status: str
    rejection_reasons: List[str]
    warnings: List[str]
    metrics: Optional[CalculatedMetricResponse] = None


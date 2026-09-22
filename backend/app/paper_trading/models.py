from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.paper_trading.enums import TradeStatus, ExitReason, PositionSizingMode

@dataclass
class PositionSizingConfig:
    mode: PositionSizingMode = PositionSizingMode.FIXED_LOT
    fixed_lot: Decimal = Decimal("1.0")
    fixed_risk_amount: Decimal = Decimal("100.0")
    risk_percent: Decimal = Decimal("1.0")
    account_balance: Decimal = Decimal("10000.0")
    min_position_size: Decimal = Decimal("0.01")
    max_position_size: Decimal = Decimal("100.0")
    position_size_step: Decimal = Decimal("0.01")

@dataclass
class PositionSizeResult:
    position_size: Decimal
    risk_amount: Decimal
    monetary_risk_per_unit: Decimal
    contract_size: Decimal
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PaperTradeConfig:
    immediate_entry: bool = True
    default_target_r: Decimal = Decimal("2.0")
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)

@dataclass
class TradeTickEvaluationResult:
    trade_id: str
    symbol: str
    status: TradeStatus
    is_closed: bool
    exit_price: Optional[Decimal] = None
    exit_reason: Optional[ExitReason] = None
    realized_pnl: Optional[Decimal] = None
    realized_r: Optional[Decimal] = None
    highest_favorable_price: Optional[Decimal] = None
    lowest_favorable_price: Optional[Decimal] = None

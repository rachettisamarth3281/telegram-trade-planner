from decimal import Decimal
from typing import Optional, List, Dict, Union, Any
from dataclasses import dataclass, field
from app.risk.enums import Side, TPSource, SLSource, RiskValidationStatus

@dataclass
class RiskEngineConfig:
    min_rr: Decimal = Decimal("1.5")
    r_multiples: List[Decimal] = field(
        default_factory=lambda: [Decimal("1.0"), Decimal("1.5"), Decimal("2.0"), Decimal("3.0")]
    )
    default_tp_r: Optional[Decimal] = Decimal("2.0")
    tick_size: Optional[Decimal] = None
    decimal_places: Optional[int] = None
    allow_strategy_sl: bool = False
    rounding_mode: str = "HALF_UP"

@dataclass
class ProviderTPMetrics:
    tp_index: int
    tp_price: Decimal
    reward_distance: Decimal
    risk_reward_ratio: Decimal
    is_low_rr: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tp_index": self.tp_index,
            "tp_price": float(self.tp_price),
            "reward_distance": float(self.reward_distance),
            "risk_reward_ratio": float(self.risk_reward_ratio),
            "is_low_rr": self.is_low_rr
        }

@dataclass
class RiskCalculationInput:
    symbol: Optional[str] = None
    side: Optional[Union[str, Side]] = None
    entry_price: Optional[Union[Decimal, float, str, int]] = None
    stop_loss: Optional[Union[Decimal, float, str, int]] = None
    provider_take_profit: Optional[Union[Decimal, float, str, int]] = None
    provider_take_profits: Optional[List[Union[Decimal, float, str, int]]] = None
    strategy_stop_loss: Optional[Union[Decimal, float, str, int]] = None
    config: Optional[RiskEngineConfig] = None

@dataclass
class RiskCalculationResult:
    is_valid: bool = False
    status: RiskValidationStatus = RiskValidationStatus.INVALID
    rejection_reasons: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)
    
    symbol: Optional[str] = None
    side: Optional[str] = None
    entry_price: Optional[Decimal] = None
    effective_sl: Optional[Decimal] = None
    sl_source: SLSource = SLSource.NONE
    risk_distance: Optional[Decimal] = None
    
    effective_tp: Optional[Decimal] = None
    tp_source: TPSource = TPSource.NONE
    reward_distance: Optional[Decimal] = None
    risk_reward_ratio: Optional[Decimal] = None
    
    tp_1R: Optional[Decimal] = None
    tp_1_5R: Optional[Decimal] = None
    tp_2R: Optional[Decimal] = None
    tp_3R: Optional[Decimal] = None
    r_targets: Dict[str, Decimal] = field(default_factory=dict)
    
    provider_tps_metrics: List[ProviderTPMetrics] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status.value if isinstance(self.status, RiskValidationStatus) else str(self.status),
            "rejection_reasons": self.rejection_reasons,
            "warning_flags": self.warning_flags,
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": float(self.entry_price) if self.entry_price is not None else None,
            "effective_sl": float(self.effective_sl) if self.effective_sl is not None else None,
            "sl_source": self.sl_source.value if isinstance(self.sl_source, SLSource) else str(self.sl_source),
            "risk_distance": float(self.risk_distance) if self.risk_distance is not None else None,
            "effective_tp": float(self.effective_tp) if self.effective_tp is not None else None,
            "tp_source": self.tp_source.value if isinstance(self.tp_source, TPSource) else str(self.tp_source),
            "reward_distance": float(self.reward_distance) if self.reward_distance is not None else None,
            "risk_reward_ratio": float(self.risk_reward_ratio) if self.risk_reward_ratio is not None else None,
            "tp_1R": float(self.tp_1R) if self.tp_1R is not None else None,
            "tp_1_5R": float(self.tp_1_5R) if self.tp_1_5R is not None else None,
            "tp_2R": float(self.tp_2R) if self.tp_2R is not None else None,
            "tp_3R": float(self.tp_3R) if self.tp_3R is not None else None,
            "r_targets": {k: float(v) for k, v in self.r_targets.items()},
            "provider_tps_metrics": [m.to_dict() for m in self.provider_tps_metrics]
        }

from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Optional, Dict, Any, Callable
from app.paper_trading.enums import PositionSizingMode
from app.paper_trading.models import PositionSizingConfig, PositionSizeResult
from app.config.instruments import get_instrument_specification, InstrumentSpec
from app.config import settings

class PositionSizingService:
    """
    Position Sizing Service (V1 Trade Planning & Risk Safety).
    
    Guarantees:
    - Never increases position size beyond configured risk limit.
    - Always rounds volume DOWN (ROUND_DOWN / floor) to permitted volume step (0.01).
    - If calculated volume < minimum volume, sets lot size to 0.0 and flags:
      "Minimum tradable volume exceeds configured risk."
    - Supports currency conversion (INR account -> USD profit currency).
    - Zero live execution hooks.
    """

    def __init__(
        self,
        spec_provider: Optional[Callable[[str], InstrumentSpec]] = None,
        usd_inr_rate: Optional[Decimal] = None,
        custom_contract_sizes: Optional[Dict[str, Decimal]] = None
    ):
        self.spec_provider = spec_provider or get_instrument_specification
        self.usd_inr_rate = usd_inr_rate or Decimal(str(settings.MANUAL_USD_INR_RATE))
        self.custom_contract_sizes: Dict[str, Decimal] = custom_contract_sizes or {}

    def get_instrument_spec(self, symbol: str) -> InstrumentSpec:
        spec = self.spec_provider(symbol)
        clean_sym = symbol.upper().strip().replace("/", "").replace("-", "")
        if clean_sym in self.custom_contract_sizes:
            # Override contract size if specified
            return InstrumentSpec(
                symbol=spec.symbol,
                contract_size=self.custom_contract_sizes[clean_sym],
                tick_size=spec.tick_size,
                min_volume=spec.min_volume,
                volume_step=spec.volume_step,
                profit_currency=spec.profit_currency,
                description=spec.description
            )
        return spec

    def calculate_trade_plan_position_size(
        self,
        symbol: str,
        risk_distance: Decimal,
        account_balance_inr: Optional[Decimal] = None,
        risk_percent: Optional[Decimal] = None,
        usd_inr_rate: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Deterministic V1 Trade Plan Position Sizing.
        
        Formula:
        1. Target Risk INR = Current Balance INR * (Risk % / 100)
        2. Target Risk USD = Target Risk INR / USD_INR_Rate
        3. Risk per Lot USD = Risk Distance * Contract Size
        4. Raw Lots = Target Risk USD / Risk per Lot USD
        5. Floor Lots = (Raw Lots // Step) * Step
        6. Minimum volume check: if Floor Lots < Min Volume -> Lot Size = 0.0, Plan NOT_READY.
        """
        spec = self.get_instrument_spec(symbol)
        bal_inr = account_balance_inr or Decimal(str(settings.CURRENT_BALANCE))
        r_pct = risk_percent or Decimal(str(settings.RISK_PER_TRADE_PCT))
        conv_rate = usd_inr_rate or self.usd_inr_rate or Decimal("85.00")

        if risk_distance <= Decimal("0"):
            return {
                "lot_size": 0.0,
                "monetary_risk_inr": 0.0,
                "monetary_risk_usd": 0.0,
                "risk_distance": 0.0,
                "is_viable": False,
                "rejection_reason": "Zero or negative risk distance",
                "contract_size": float(spec.contract_size),
                "usd_inr_rate": float(conv_rate)
            }

        # 1. Target Risk in Account Currency (INR)
        target_risk_inr = (bal_inr * r_pct) / Decimal("100.0")

        # 2. Currency Conversion to Instrument Profit Currency (USD for Gold)
        if spec.profit_currency.upper() == "USD" and settings.ACCOUNT_CURRENCY.upper() == "INR":
            target_risk_usd = target_risk_inr / conv_rate
        else:
            target_risk_usd = target_risk_inr

        # 3. Monetary Risk per 1.0 Standard Lot
        monetary_risk_per_unit_usd = risk_distance * spec.contract_size

        if monetary_risk_per_unit_usd <= Decimal("0"):
            return {
                "lot_size": 0.0,
                "monetary_risk_inr": 0.0,
                "monetary_risk_usd": 0.0,
                "risk_distance": float(risk_distance),
                "is_viable": False,
                "rejection_reason": "Invalid contract or unit risk calculation",
                "contract_size": float(spec.contract_size),
                "usd_inr_rate": float(conv_rate)
            }

        # 4. Raw lot size calculation
        raw_lot_size = target_risk_usd / monetary_risk_per_unit_usd

        # 5. STRICT Floor Rounding (NEVER ROUND UP)
        step = spec.volume_step
        quantized_lot_size = (raw_lot_size / step).to_integral_value(rounding=ROUND_DOWN) * step

        # 6. Minimum Volume Guard
        if quantized_lot_size < spec.min_volume:
            return {
                "lot_size": 0.0,
                "raw_lot_size": float(raw_lot_size),
                "monetary_risk_inr": 0.0,
                "monetary_risk_usd": 0.0,
                "target_risk_inr": float(target_risk_inr),
                "risk_distance": float(risk_distance),
                "is_viable": False,
                "rejection_reason": "Minimum tradable volume exceeds configured risk.",
                "contract_size": float(spec.contract_size),
                "min_volume": float(spec.min_volume),
                "volume_step": float(spec.volume_step),
                "usd_inr_rate": float(conv_rate)
            }

        # 7. Actual monetary risk with floor-quantized lot size
        actual_risk_usd = quantized_lot_size * monetary_risk_per_unit_usd
        if spec.profit_currency.upper() == "USD" and settings.ACCOUNT_CURRENCY.upper() == "INR":
            actual_risk_inr = actual_risk_usd * conv_rate
        else:
            actual_risk_inr = actual_risk_usd

        return {
            "lot_size": float(quantized_lot_size),
            "raw_lot_size": float(raw_lot_size),
            "monetary_risk_inr": round(float(actual_risk_inr), 2),
            "monetary_risk_usd": round(float(actual_risk_usd), 2),
            "target_risk_inr": round(float(target_risk_inr), 2),
            "target_risk_usd": round(float(target_risk_usd), 2),
            "risk_distance": float(risk_distance),
            "is_viable": True,
            "rejection_reason": None,
            "contract_size": float(spec.contract_size),
            "min_volume": float(spec.min_volume),
            "volume_step": float(spec.volume_step),
            "usd_inr_rate": float(conv_rate)
        }

    def calculate_position_size(
        self,
        symbol: str,
        risk_distance: Decimal,
        config: Optional[PositionSizingConfig] = None
    ) -> PositionSizeResult:
        """Backwards-compatible legacy method for paper trading test suite."""
        cfg = config or PositionSizingConfig()
        spec = self.get_instrument_spec(symbol)
        contract_size = spec.contract_size

        if risk_distance <= Decimal("0"):
            return PositionSizeResult(
                position_size=Decimal("0.0"),
                risk_amount=Decimal("0.0"),
                monetary_risk_per_unit=Decimal("0.0"),
                contract_size=contract_size,
                details={"error": "Zero or negative risk distance"}
            )

        monetary_risk_per_unit = risk_distance * contract_size

        if cfg.mode == PositionSizingMode.FIXED_LOT:
            pos_size = cfg.fixed_lot
            risk_amount = (pos_size * monetary_risk_per_unit).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            return PositionSizeResult(
                position_size=pos_size,
                risk_amount=risk_amount,
                monetary_risk_per_unit=monetary_risk_per_unit,
                contract_size=contract_size,
                details={"mode": "FIXED_LOT"}
            )

        elif cfg.mode == PositionSizingMode.FIXED_RISK_AMOUNT:
            risk_amount = cfg.fixed_risk_amount
            raw_pos_size = risk_amount / monetary_risk_per_unit
            quant_pos_size = (raw_pos_size / cfg.position_size_step).to_integral_value(rounding=ROUND_DOWN) * cfg.position_size_step
            if quant_pos_size < cfg.min_position_size:
                quant_pos_size = Decimal("0.0")
            actual_risk = (quant_pos_size * monetary_risk_per_unit).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            return PositionSizeResult(
                position_size=quant_pos_size,
                risk_amount=actual_risk,
                monetary_risk_per_unit=monetary_risk_per_unit,
                contract_size=contract_size,
                details={"mode": "FIXED_RISK_AMOUNT", "target_risk": float(risk_amount)}
            )

        elif cfg.mode == PositionSizingMode.PERCENTAGE_RISK:
            target_risk_usd = (cfg.account_balance * cfg.risk_percent) / Decimal("100.0")
            raw_pos_size = target_risk_usd / monetary_risk_per_unit
            quant_pos_size = (raw_pos_size / cfg.position_size_step).to_integral_value(rounding=ROUND_DOWN) * cfg.position_size_step
            if quant_pos_size < cfg.min_position_size:
                quant_pos_size = Decimal("0.0")
            actual_risk = (quant_pos_size * monetary_risk_per_unit).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            return PositionSizeResult(
                position_size=quant_pos_size,
                risk_amount=actual_risk,
                monetary_risk_per_unit=monetary_risk_per_unit,
                contract_size=contract_size,
                details={"mode": "PERCENTAGE_RISK", "target_risk_usd": float(target_risk_usd)}
            )

        return PositionSizeResult(
            position_size=Decimal("0.01"),
            risk_amount=monetary_risk_per_unit * Decimal("0.01"),
            monetary_risk_per_unit=monetary_risk_per_unit,
            contract_size=contract_size,
            details={"mode": "DEFAULT"}
        )

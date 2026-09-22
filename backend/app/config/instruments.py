from decimal import Decimal
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class InstrumentSpec(BaseModel):
    symbol: str
    contract_size: Decimal = Field(default=Decimal("100.0"), description="Contract size per standard lot (e.g. 100 oz for Gold)")
    tick_size: Decimal = Field(default=Decimal("0.01"), description="Minimum price movement increment")
    min_volume: Decimal = Field(default=Decimal("0.01"), description="Minimum tradable lot size")
    volume_step: Decimal = Field(default=Decimal("0.01"), description="Allowed volume increment step")
    profit_currency: str = Field(default="USD", description="Currency in which PnL is quoted (e.g. USD)")
    description: str = Field(default="", description="Human-readable instrument description")

# In-memory registry with dynamic defaults (editable at runtime)
DEFAULT_INSTRUMENTS: Dict[str, InstrumentSpec] = {
    "XAUUSD": InstrumentSpec(
        symbol="XAUUSD",
        contract_size=Decimal("100.0"),
        tick_size=Decimal("0.01"),
        min_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        profit_currency="USD",
        description="Spot Gold / US Dollar (100 oz per lot)"
    ),
    "GOLD": InstrumentSpec(
        symbol="GOLD",
        contract_size=Decimal("100.0"),
        tick_size=Decimal("0.01"),
        min_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        profit_currency="USD",
        description="Spot Gold / US Dollar (100 oz per lot)"
    ),
    "EURUSD": InstrumentSpec(
        symbol="EURUSD",
        contract_size=Decimal("100000.0"),
        tick_size=Decimal("0.00001"),
        min_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        profit_currency="USD",
        description="Euro / US Dollar (100,000 EUR per lot)"
    ),
    "BTCUSD": InstrumentSpec(
        symbol="BTCUSD",
        contract_size=Decimal("1.0"),
        tick_size=Decimal("0.01"),
        min_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        profit_currency="USD",
        description="Bitcoin / US Dollar (1 BTC per lot)"
    ),
}

_active_instruments: Dict[str, InstrumentSpec] = dict(DEFAULT_INSTRUMENTS)

def get_instrument_specification(symbol: str) -> InstrumentSpec:
    """Resolve instrument spec by symbol with normalization."""
    clean_sym = symbol.upper().strip().replace("/", "").replace("-", "")
    if clean_sym in _active_instruments:
        return _active_instruments[clean_sym]
    if "XAU" in clean_sym or "GOLD" in clean_sym:
        return _active_instruments["XAUUSD"]
    # Fallback to standard 100-contract spec
    return InstrumentSpec(
        symbol=clean_sym,
        contract_size=Decimal("100.0"),
        tick_size=Decimal("0.01"),
        min_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        profit_currency="USD",
        description=f"Standard Spec for {clean_sym}"
    )

def update_instrument_specification(symbol: str, spec: InstrumentSpec) -> InstrumentSpec:
    """Update active instrument specification at runtime."""
    clean_sym = symbol.upper().strip().replace("/", "").replace("-", "")
    _active_instruments[clean_sym] = spec
    return spec

def list_instrument_specifications() -> Dict[str, InstrumentSpec]:
    return dict(_active_instruments)


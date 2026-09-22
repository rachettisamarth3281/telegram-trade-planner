from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from app.parser.diagnostics import ParserDiagnostics
from app.parser.states import ParsingState

@dataclass
class ParsedSignal:
    """
    Normalized signal object output by the SignalParserEngine.
    Preserves original text, metadata, parsed levels, and diagnostics.
    """
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: str = "MARKET"
    entry_price: Optional[float] = None
    entry_price_upper: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profits: List[float] = field(default_factory=list)
    message_id: Optional[int] = None
    original_message: str = ""
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    diagnostics: Optional[ParserDiagnostics] = None

    @property
    def is_valid(self) -> bool:
        return self.diagnostics is not None and self.diagnostics.state == ParsingState.VALID

    @property
    def is_partial(self) -> bool:
        return self.diagnostics is not None and self.diagnostics.state == ParsingState.PARTIAL

from typing import Optional, List, Dict
from dataclasses import dataclass, field
from app.parser.states import ParsingState

@dataclass
class ParserDiagnostics:
    """
    Detailed diagnostics produced by the Signal Parser.
    Note: parser_confidence measures purely syntactic parsing confidence and
    must NOT represent any probability of trade success.
    """
    state: ParsingState
    detected_symbol: Optional[str] = None
    detected_side: Optional[str] = None
    detected_entry: Optional[float] = None
    detected_entry_upper: Optional[float] = None
    detected_sl: Optional[float] = None
    detected_tp: Optional[float] = None
    detected_tps: List[float] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    parser_confidence: float = 0.0
    parse_errors: List[str] = field(default_factory=list)
    token_matches: Dict[str, str] = field(default_factory=dict)

    @property
    def confidence(self) -> float:
        return self.parser_confidence

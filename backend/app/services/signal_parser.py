import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from app.utils.instrument_specs import ALIAS_MAP, normalize_symbol_name

@dataclass
class ParsedSignalResult:
    raw_text: str
    symbol: Optional[str] = None
    side: Optional[str] = None           # BUY, SELL
    order_type: str = "MARKET"          # MARKET, LIMIT, STOP
    entry_price: Optional[float] = None # Reference entry price (e.g. 4351.50)
    entry_price_upper: Optional[float] = None  # for range entries: 2300-2305
    entry_zone_low: Optional[float] = None     # 4350.0
    entry_zone_high: Optional[float] = None    # 4353.0
    provider_sl: Optional[float] = None
    provider_tps: List[float] = field(default_factory=list)
    confidence: float = 0.0
    matched_patterns: Dict[str, str] = field(default_factory=dict)
    parse_errors: List[str] = field(default_factory=list)


class SignalParser:
    """
    High-resilience tokenizer and multi-pattern parser for Telegram trading signals.
    Extracts Symbol, Side (BUY/SELL), Order Type, Entry Price, SL, and multiple TP levels.
    """

    # Side patterns
    SIDE_PATTERNS = [
        (r'\b(BUY\s+LIMIT)\b', "BUY", "LIMIT"),
        (r'\b(BUY\s+STOP)\b', "BUY", "STOP"),
        (r'\b(SELL\s+LIMIT)\b', "SELL", "LIMIT"),
        (r'\b(SELL\s+STOP)\b', "SELL", "STOP"),
        (r'\b(BUY\s+NOW|BUY\s+CMP|STRONG\s+BUY|BUY)\b', "BUY", "MARKET"),
        (r'\b(LONG|GO\s+LONG)\b', "BUY", "MARKET"),
        (r'\b(SELL\s+NOW|SELL\s+CMP|STRONG\s+SELL|SELL)\b', "SELL", "MARKET"),
        (r'\b(SHORT|GO\s+SHORT)\b', "SELL", "MARKET"),
    ]

    # Entry patterns
    ENTRY_PATTERNS = [
        r'(?:ENTRY|ENTRADA|PRICE|CMP|AT|@)\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)',
        r'@\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)',
        r'\b(?:NOW|CMP)\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)',
    ]

    # Stop Loss patterns
    SL_PATTERNS = [
        r'\b(?:SL|STOP\s*LOSS|STOP)\s*[:=-]?\s*@?\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)',
        r'\b(?:SL)\s*@?\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)',
    ]

    @classmethod
    def parse(cls, text: str) -> ParsedSignalResult:
        if not text or not text.strip():
            return ParsedSignalResult(raw_text="", confidence=0.0, parse_errors=["Empty text"])

        clean_text = cls._preprocess_text(text)
        result = ParsedSignalResult(raw_text=text)

        # 1. Extract Symbol
        symbol, sym_match = cls._extract_symbol(clean_text)
        if symbol:
            result.symbol = symbol
            result.matched_patterns["symbol"] = sym_match

        # 2. Extract Side and Order Type
        side, order_type, side_match = cls._extract_side(clean_text)
        if side:
            result.side = side
            result.order_type = order_type
            result.matched_patterns["side"] = side_match

        # 3. Extract Stop Loss (SL)
        sl_val, sl_match = cls._extract_sl(clean_text, side=side)
        if sl_val is not None:
            result.provider_sl = sl_val
            result.matched_patterns["sl"] = sl_match

        # 4. Extract Take Profits (TPs)
        tps, tp_matches = cls._extract_tps(clean_text)
        result.provider_tps = tps
        if tp_matches:
            result.matched_patterns["tp"] = ", ".join(tp_matches)

        # 5. Extract Entry Price & Zone
        entry_val, entry_upper, zone_low, zone_high, entry_match = cls._extract_entry(
            clean_text,
            side=side,
            sl=result.provider_sl,
            tps=result.provider_tps
        )
        if entry_val is not None:
            result.entry_price = entry_val
            result.entry_price_upper = entry_upper
            result.entry_zone_low = zone_low
            result.entry_zone_high = zone_high
            result.matched_patterns["entry"] = entry_match

        # 6. Calculate Parser Confidence
        result.confidence = cls._calculate_confidence(result)

        return result

    @classmethod
    def _preprocess_text(cls, text: str) -> str:
        # Standardize whitespace and remove disruptive decorative characters
        cleaned = text.replace("’", "'").replace("–", "-").replace("—", "-")
        # Keep letters, numbers, basic punctuation (@ : . , / -)
        return cleaned

    @classmethod
    def _extract_symbol(cls, text: str) -> tuple[Optional[str], str]:
        upper_text = text.upper()
        # Sort candidate aliases by descending length to match "XAUUSD" before "XAU"
        sorted_aliases = sorted(ALIAS_MAP.keys(), key=len, reverse=True)

        for alias in sorted_aliases:
            # Match word boundary or slash format e.g. "EUR/USD" or "GOLD"
            pattern = rf'(?:\b|(?<=/)){re.escape(alias)}(?:\b|(?=/))'
            match = re.search(pattern, upper_text)
            if match:
                canonical = ALIAS_MAP[alias]
                return canonical, match.group(0)

        return None, ""

    @classmethod
    def _extract_side(cls, text: str) -> tuple[Optional[str], str, str]:
        upper_text = text.upper()
        for pattern, side, order_type in cls.SIDE_PATTERNS:
            match = re.search(pattern, upper_text)
            if match:
                return side, order_type, match.group(0)
        return None, "MARKET", ""

    @classmethod
    def _extract_sl(cls, text: str, side: Optional[str] = None) -> tuple[Optional[float], str]:
        from app.parser.zone_parser import EntryZoneParser
        upper_text = text.upper()
        for pattern in cls.SL_PATTERNS:
            match = re.search(pattern, upper_text)
            if match:
                try:
                    raw_sl = match.group(1)
                    val = EntryZoneParser.parse_sl_value(raw_sl, side=side)
                    if val > 0:
                        return val, match.group(0)
                except (ValueError, IndexError):
                    continue
        return None, ""

    @classmethod
    def _extract_tps(cls, text: str) -> tuple[List[float], List[str]]:
        upper_text = text.upper()
        tps: List[float] = []
        matches: List[str] = []

        # 1. Numbered TPs first: TP1: 4180, TP2 4190, TARGET 1 4180
        numbered_pattern = r'\b(?:TP\s*([1-5])(?!\d)|TARGET\s*([1-5])(?!\d))\s*[:=-]?\s*@?\s*([0-9]+(?:\.[0-9]+)?)\b'
        numbered_matches = list(re.finditer(numbered_pattern, upper_text))
        if numbered_matches:
            for m in numbered_matches:
                try:
                    price = float(m.group(3))
                    if price not in tps:
                        tps.append(price)
                        matches.append(m.group(0))
                except (ValueError, IndexError):
                    pass
            if tps:
                return tps, matches

        # 2. Multi-target list: "Target 4180 4190 4200" or "Targets: 4180, 4190, 4200"
        multi_target_match = re.search(r'\b(?:TARGETS?|TAKE\s*PROFITS?)\s*🎯?\s*[:=-]?\s*(\d{3,6}(?:\.\d+)?(?:\s+\d{3,6}(?:\.\d+)?)+)', upper_text)
        if multi_target_match:
            nums = re.findall(r'\b\d{3,6}(?:\.\d+)?\b', multi_target_match.group(1))
            for n in nums:
                try:
                    price = float(n)
                    if price not in tps:
                        tps.append(price)
                except ValueError:
                    pass
            if tps:
                return tps, [multi_target_match.group(0)]

        # 3. Generic TP / TARGET (single price)
        generic_pattern = r'\b(?:TP|TARGET|TAKE\s*PROFIT)\s*[:=-]?\s*@?\s*([0-9]+(?:\.[0-9]+)?)\b'
        for m in re.finditer(generic_pattern, upper_text):
            try:
                price = float(m.group(1))
                if price not in tps:
                    tps.append(price)
                    matches.append(m.group(0))
            except (ValueError, IndexError):
                pass

        return tps, matches

    @classmethod
    def _extract_entry(
        cls,
        text: str,
        side: Optional[str],
        sl: Optional[float],
        tps: List[float]
    ) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], str]:
        from app.parser.zone_parser import EntryZoneParser
        upper_text = text.upper()

        # 1. Explicit ENTRY / CMP / @ keyword
        for pattern in cls.ENTRY_PATTERNS:
            match = re.search(pattern, upper_text)
            if match:
                try:
                    raw_str = match.group(1)
                    low, high, ref, prices = EntryZoneParser.parse_zone(raw_str, side=side)
                    if ref > 0:
                        upper = high if high != low else None
                        return ref, upper, low, high, match.group(0)
                except (ValueError, IndexError):
                    continue

        # 2. Fallback: Positional number/range immediately following Side / Symbol (e.g. "BUY 1.0850", "Sell gold 4350_53")
        fallback_pattern = r'\b(?:BUY|SELL|LONG|SHORT)\s+(?:[A-Z0-9/_-]+\s+)?([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)'
        fallback_match = re.search(fallback_pattern, upper_text)
        if fallback_match:
            try:
                raw_str = fallback_match.group(1)
                low, high, ref, prices = EntryZoneParser.parse_zone(raw_str, side=side)
                if ref > 0:
                    # Check that this number is not already identified as SL or TP
                    if (sl is None or abs(ref - sl) > 1e-5) and not any(abs(ref - tp) < 1e-5 for tp in tps):
                        upper = high if high != low else None
                        return ref, upper, low, high, fallback_match.group(0)
            except (ValueError, IndexError):
                pass

        return None, None, None, None, ""

    @classmethod
    def _calculate_confidence(cls, result: ParsedSignalResult) -> float:
        score = 0.0
        if result.symbol:
            score += 0.35
        if result.side:
            score += 0.30
        if result.entry_price is not None:
            score += 0.15
        if result.provider_sl is not None:
            score += 0.15
        if result.provider_tps:
            score += 0.05
        return min(round(score, 2), 1.0)


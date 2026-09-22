import re
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone

from app.parser.states import ParsingState
from app.parser.diagnostics import ParserDiagnostics
from app.parser.result import ParsedSignal
from app.parser.patterns import (
    SYMBOL_ALIASES,
    SIDE_PATTERNS,
    SL_PATTERNS,
    TP_NUMBERED_PATTERN,
    TP_GENERIC_PATTERNS,
    ENTRY_EXPLICIT_PATTERNS,
    preprocess_text
)

class SignalParserEngine:
    """
    Robust, deterministic parser for Telegram trading signals.
    Extracts Symbol, Side (BUY/SELL), Order Type, Entry Price, Stop Loss, and Take Profits.
    Produces explicit lifecycle states (VALID, PARTIAL, INVALID, UNKNOWN) and comprehensive diagnostics.
    """

    @classmethod
    def parse(
        cls,
        text: str,
        message_id: Optional[int] = None,
        received_at: Optional[datetime] = None
    ) -> ParsedSignal:
        if not text or not text.strip():
            diag = ParserDiagnostics(
                state=ParsingState.UNKNOWN,
                parse_errors=["Empty or whitespace text"],
                missing_fields=["symbol", "side", "entry_price", "stop_loss"],
                parser_confidence=0.0
            )
            return ParsedSignal(
                original_message=text or "",
                message_id=message_id,
                received_at=received_at or datetime.now(timezone.utc),
                diagnostics=diag
            )

        clean_text = preprocess_text(text)
        token_matches: Dict[str, str] = {}
        parse_errors: List[str] = []

        # 1. Extract Symbol
        detected_symbol, sym_match = cls._extract_symbol(clean_text)
        if detected_symbol:
            token_matches["symbol"] = sym_match

        # 2. Extract Side and Order Type
        detected_side, order_type, side_match = cls._extract_side(clean_text)
        if detected_side:
            token_matches["side"] = side_match

        # 3. Extract Stop Loss
        detected_sl, sl_match = cls._extract_sl(clean_text, side=detected_side)
        if detected_sl is not None:
            token_matches["sl"] = sl_match

        # 4. Extract Take Profits (handles TP before SL or SL before TP)
        detected_tps, tp_matches = cls._extract_tps(clean_text)
        detected_tp = detected_tps[0] if detected_tps else None
        if tp_matches:
            token_matches["tp"] = ", ".join(tp_matches)

        # 5. Extract Entry Price (ignoring SL and TP numbers)
        excluded_prices = [p for p in ([detected_sl] + detected_tps) if p is not None]
        detected_entry, entry_upper, zone_low, zone_high, entry_match = cls._extract_entry(
            clean_text,
            excluded_prices,
            side=detected_side
        )
        if detected_entry is not None:
            token_matches["entry"] = entry_match

        # 6. Determine Missing Fields
        missing_fields: List[str] = []
        if not detected_symbol:
            missing_fields.append("symbol")
        if not detected_side:
            missing_fields.append("side")
        if detected_entry is None:
            missing_fields.append("entry_price")
        if detected_sl is None:
            missing_fields.append("stop_loss")
        if detected_tp is None:
            missing_fields.append("take_profit")

        # 7. Calculate State and Confidence
        state, confidence = cls._evaluate_state(
            detected_symbol=detected_symbol,
            detected_side=detected_side,
            detected_entry=detected_entry,
            detected_sl=detected_sl,
            detected_tps=detected_tps,
            parse_errors=parse_errors,
            text=text
        )

        diagnostics = ParserDiagnostics(
            state=state,
            detected_symbol=detected_symbol,
            detected_side=detected_side,
            detected_entry=detected_entry,
            detected_entry_upper=entry_upper,
            detected_sl=detected_sl,
            detected_tp=detected_tp,
            detected_tps=detected_tps,
            missing_fields=missing_fields,
            parser_confidence=confidence,
            parse_errors=parse_errors,
            token_matches=token_matches
        )

        return ParsedSignal(
            symbol=detected_symbol,
            side=detected_side,
            order_type=order_type,
            entry_price=detected_entry,
            entry_price_upper=entry_upper,
            stop_loss=detected_sl,
            take_profit=detected_tp,
            take_profits=detected_tps,
            message_id=message_id,
            original_message=text,
            received_at=received_at or datetime.now(timezone.utc),
            diagnostics=diagnostics
        )

    @classmethod
    def _extract_symbol(cls, text: str) -> Tuple[Optional[str], str]:
        upper_text = text.upper()
        sorted_keys = sorted(SYMBOL_ALIASES.keys(), key=len, reverse=True)

        for alias in sorted_keys:
            pattern = rf'(?:\b|(?<=/)|(?<=-)){re.escape(alias)}(?:\b|(?=/)|(?=-))'
            match = re.search(pattern, upper_text)
            if match:
                canonical = SYMBOL_ALIASES[alias]
                return canonical, match.group(0)

        return None, ""

    @classmethod
    def _extract_side(cls, text: str) -> Tuple[Optional[str], str, str]:
        upper_text = text.upper()
        for pattern, side, order_type in SIDE_PATTERNS:
            match = re.search(pattern, upper_text)
            if match:
                return side, order_type, match.group(0)
        return None, "MARKET", ""

    @classmethod
    def _extract_sl(cls, text: str, side: Optional[str] = None) -> Tuple[Optional[float], str]:
        from app.parser.zone_parser import EntryZoneParser
        upper_text = text.upper()
        for pattern in SL_PATTERNS:
            match = re.search(pattern, upper_text)
            if match:
                try:
                    val_str = match.group("sl_price")
                    val = EntryZoneParser.parse_sl_value(val_str, side=side)
                    if val > 0:
                        return val, match.group(0)
                except (ValueError, IndexError):
                    continue
        return None, ""

    @classmethod
    def _extract_tps(cls, text: str) -> Tuple[List[float], List[str]]:
        upper_text = text.upper()
        tps: List[float] = []
        matches: List[str] = []

        # 1. Numbered TP patterns (TP1, TP2, TARGET 1, etc.)
        numbered = list(re.finditer(TP_NUMBERED_PATTERN, upper_text))
        if numbered:
            for m in numbered:
                try:
                    price_str = m.group("tp_price")
                    price = float(price_str)
                    if price not in tps:
                        tps.append(price)
                        matches.append(m.group(0))
                except (ValueError, IndexError):
                    pass
            if tps:
                return tps, matches

        # 2. Multi-target list (e.g. Target 4180 4190 4200)
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

        # 3. Generic TP patterns
        for pat in TP_GENERIC_PATTERNS:
            for m in re.finditer(pat, upper_text):
                try:
                    price_str = m.group("tp_price")
                    price = float(price_str)
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
        excluded_prices: List[float],
        side: Optional[str] = None
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], str]:
        from app.parser.zone_parser import EntryZoneParser
        upper_text = text.upper()

        # 1. Explicit keyword entries (ENTRY @ 4350_53, CMP 4350, @ 4350.53, 4350-4352)
        for pattern in ENTRY_EXPLICIT_PATTERNS:
            match = re.search(pattern, upper_text)
            if match:
                try:
                    raw_str = match.group(1)
                    low, high, ref, prices = EntryZoneParser.parse_zone(raw_str, side=side)
                    if ref > 0 and not any(abs(ref - ex) < 1e-5 for ex in excluded_prices):
                        upper = high if high != low else None
                        return ref, upper, low, high, match.group(0)
                except (ValueError, IndexError):
                    continue

        # 2. Positional entry immediately following side or symbol (e.g. "BUY GOLD 4350_53", "SELL XAUUSD 4350.53")
        positional_pattern = r'\b(?:BUY|SELL|LONG|SHORT)\s+(?:[A-Z0-9/_-]+\s+)?([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)\b'
        match = re.search(positional_pattern, upper_text)
        if match:
            try:
                raw_str = match.group(1)
                low, high, ref, prices = EntryZoneParser.parse_zone(raw_str, side=side)
                if ref > 0 and not any(abs(ref - ex) < 1e-5 for ex in excluded_prices):
                    upper = high if high != low else None
                    return ref, upper, low, high, match.group(0)
            except (ValueError, IndexError):
                pass

        # 3. Positional symbol followed by number (e.g. "GOLD 4350_53 BUY")
        sym_pos_pattern = r'\b(?:GOLD|XAUUSD|XAU|EURUSD|GBPUSD|USDJPY|US30|BTCUSD)\s+([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)\b'
        match = re.search(sym_pos_pattern, upper_text)
        if match:
            try:
                raw_str = match.group(1)
                low, high, ref, prices = EntryZoneParser.parse_zone(raw_str, side=side)
                if ref > 0 and not any(abs(ref - ex) < 1e-5 for ex in excluded_prices):
                    upper = high if high != low else None
                    return ref, upper, low, high, match.group(0)
            except (ValueError, IndexError):
                pass

        return None, None, None, None, ""

    @classmethod
    def _evaluate_state(
        cls,
        detected_symbol: Optional[str],
        detected_side: Optional[str],
        detected_entry: Optional[float],
        detected_sl: Optional[float],
        detected_tps: List[float],
        parse_errors: List[str],
        text: str
    ) -> Tuple[ParsingState, float]:
        # Syntactic confidence scoring (0.0 to 1.0)
        score = 0.0
        if detected_symbol:
            score += 0.35
        if detected_side:
            score += 0.30
        if detected_entry is not None:
            score += 0.15
        if detected_sl is not None:
            score += 0.15
        if detected_tps:
            score += 0.05

        confidence = min(round(score, 2), 1.0)

        # UNKNOWN: Completely unrelated message
        if not detected_symbol and not detected_side:
            return ParsingState.UNKNOWN, 0.0

        # VALID: Symbol + Side + Entry + Stop Loss all present
        if detected_symbol and detected_side and (detected_entry is not None) and (detected_sl is not None):
            return ParsingState.VALID, confidence

        # PARTIAL: Symbol + Side + Entry present, but missing SL (or missing Entry but SL present)
        if (detected_symbol and detected_side) and (detected_entry is not None or detected_sl is not None):
            return ParsingState.PARTIAL, confidence

        # INVALID: Ambiguous or fragmentary trade terms
        if parse_errors or (detected_symbol and not detected_side) or (detected_side and not detected_symbol):
            return ParsingState.INVALID, confidence

        return ParsingState.UNKNOWN, 0.0

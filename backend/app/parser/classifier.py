import re
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

class MessageClassification(str, Enum):
    SIGNAL_ENTRY = "SIGNAL_ENTRY"
    SL_UPDATE = "SL_UPDATE"
    TARGET_UPDATE = "TARGET_UPDATE"
    TRADE_MANAGEMENT = "TRADE_MANAGEMENT"
    PROVIDER_OUTCOME = "PROVIDER_OUTCOME"
    PLANNING = "PLANNING"
    ADD_ENTRY = "ADD_ENTRY"
    COMMENTARY = "COMMENTARY"
    PROMOTIONAL = "PROMOTIONAL"
    NOISE = "NOISE"
    MEDIA_ONLY = "MEDIA_ONLY"

class ManagementAction(str, Enum):
    RISK_FREE = "RISK_FREE"
    MOVE_SL_TO_ENTRY = "MOVE_SL_TO_ENTRY"
    MOVE_SL = "MOVE_SL"
    BOOK_PROFIT = "BOOK_PROFIT"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    EXIT = "EXIT"
    TRAIL_SL = "TRAIL_SL"

@dataclass
class ClassificationResult:
    message_type: MessageClassification
    confidence: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Optional parsed metadata if recognized
    pips_claimed: Optional[float] = None
    management_action: Optional[ManagementAction] = None
    raw_text: str = ""

class MessageClassifier:
    """
    Deterministic rule-based Telegram message classifier trained on real 'Shubham Vip Club 👑' patterns.
    """

    # 1. Promotional / Links / External Channels
    RE_PROMOTIONAL = re.compile(
        r"(youtube\.com/live|youtu\.be|whatsapp\.com/channel|manus\.space|Join\s+(?:LiveStream|Live|New\s+Profiitable|Everyone)|Giveaway|Invite\s+karo|Watching\s+\d+|Likes\s+\d+|Share\s+(?:Everyone\s+)?Profit\s+Screenshot|Kisne\s+Kitna\s+Chapa|Share\s+Profits|Dosto\s+website\s+open|Challenge\s+Group)",
        re.IGNORECASE
    )

    # 2. Planning messages
    RE_PLANNING = re.compile(
        r"^(?:Now\s+)?planning\s+(?:for|Selling|a\s+sell\s+Trade|for\s+sell\s+in\s+gold|for\s+buy\s+trade|for\s+sell\s+trade)?\s*(?:buy|sell|buying|selling|side)?.*$|"
        r"^Ready\s*(?:for\s+.*|karege|sab)?$|"
        r"^(?:Plan\s+change|Finding\s+(?:level|perfect\s+level).*|Waiting\s+for\s+(?:perfect\s+level|setup|more\s+down|closing|level).*|Analysing\s+market|Ready\s*)$|"
        r"^(?:Selling\s+plan\s+kar\s+raha\s+tha|Me\s+selling\s+plan|Shifting\s+a\s+view\s+to\s+buy|Before\s+giving\s+trade|Market\s+current\s+view|Your\s+view|Your\s+Opinion|Apan\s+apna\s+view)",
        re.IGNORECASE
    )

    # 3. Trade Management (Risk Free, C2C, Book profit, Exit)
    RE_RISK_FREE = re.compile(r"\b(?:Risk\s*free|karo\s+risk\s+free|Risky\s*free)\b", re.IGNORECASE)
    RE_MOVE_SL_COST = re.compile(r"\b(?:Trail\s+SL\s+to\s+cost|C2c|c\s*2\s*c|SL\s+c2c|move\s+sl\s+c2c)\b", re.IGNORECASE)
    RE_EXIT_MANAGEMENT = re.compile(r"^(?:Exit|Exit\s+all\s+C2C|Book\s+all|Book\s+full|Full\s+booked\s*✅?|Closing\s+this\s+trade\s+in\s+risk\s+Free|Don't\s+hold\s+this\s+trade\s+now|Exit\s+from\s+this\s+trade\s+immediately)$", re.IGNORECASE)
    RE_BOOK_PROFIT = re.compile(r"\b(?:(?:profit\s+)?Booking\s+karte\s+(?:chalna|jana|start|chalo)|book\s+\d+%\s*|Apne\s+apne\s+hisab\s+se\s+booking|Booking\s+And\s+Trailing)\b", re.IGNORECASE)

    # 4. Provider Outcome Claims (Pips, TP hits, SL hits, Price reversed)
    RE_PIPS = re.compile(r"(?:(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:pips|pipes)\s*(?:done|Running|ka|hai|Done)?|Poore\s+(\d+)\s+pips|Crazy\s+(\d+)\s+pips|It's\s+(\d+)\s+pips|Again\s+(\d+)\s+pips|Literally\s+Blast\s+Ho\s+Gaya\s+(\d+)\s+Pips)", re.IGNORECASE)
    RE_TP_HIT = re.compile(r"(?:TP\s*[123]\s*HIT|Target\s*(?:🎯)?\s*(?:1|2nd|3rd|All)?\s*(?:done|hit|✅)|All\s+target\s*(?:🎯)?\s*✅|All\s+targets\s+hit|All\s+TP\s+done|2nd\s+target\s*🎯✅|Loos\s+recovered\s*✅)", re.IGNORECASE)
    RE_SL_HIT = re.compile(r"^(?:SL\s*hit|Exit\s+SL\s+hit|sl\s+hit|SL\s+Hit)$", re.IGNORECASE)
    RE_PRICE_REVERSED = re.compile(r"\b(?:Price\s*reversed|price\s*reversed|Ok\s+price\s*reversed|Sudden\s+Price\s*reversed|Price\s+reverse)\b", re.IGNORECASE)

    # 5. Stop Loss Update
    RE_SL_UPDATE = re.compile(r"^(?:SL|Sl|sl)\s*[:=]?\s*(\d{4,5}(?:[_\-\.]\d{1,5}(?:\.\d+)?)?|\d{4,5})\s*(?:only)?$", re.IGNORECASE)
    RE_SHIFT_SL = re.compile(r"^Shift\s+SL\s+to\s+(\d{4,5})$", re.IGNORECASE)

    # 6. Target Update
    RE_TARGET_UPDATE = re.compile(r"^(?:Target|Targets)\s*🎯?\s*[:\n]?", re.IGNORECASE)

    # 7. Additional Entry / Averaging
    RE_ADD_ENTRY = re.compile(r"(?:Personally\s+adding\s+few\s+qty|I\s+will\s+(?:personally\s+)?add\s+\d+\s+lot|Added\s+\d+\s+lot|Also\s+buy\s+at\s+\d+|\d+\s+more\s+lots\s+add\s+on|Holding\s+\d+\s+lots|I\s+am\s+placing\s+1\s+more\s+sell\s+order|Take\s+entry\s+as\s+down\s+as|Take\s+down\s+if\s+you\s+get|Buy\s+down\s+if\s+you\s+got)", re.IGNORECASE)

    # 8. Signal Entry pattern
    RE_SIGNAL_ENTRY = re.compile(r"\b(?:Buy|Sell|BUY|SELL|LONG|SHORT)\s+([A-Za-z0-9_\/\-]+)?\s*(?:@|at)?\s*(?:https://t\.me/)?(?:@)?\s*(\d{1,6}(?:[_\-]\d{1,6})*(?:\.\d+)?|\d{1,6})", re.IGNORECASE)

    # 9. Simple Noise / Greetings
    RE_NOISE = re.compile(r"^(?:Hello|hello|Good\s+Morning\s+Traders\s*🫶?|Ok|ok|Wait|wait|Still\s+waiting|One\s+last\s+trade|Last\s+trade|A\s+another\s+trade\s+I\s+will\s+give|A\s+another\s+trade\s+will\s+come|Ek\s+trade\s+or\s+karte\s+hai|Ab\s+kal\s+trade\s+karenge|Next\s+trade\s+\d+\s*(?:Pm|pm|am)\.?|Today|1st\s+Trade|Second\s+Trade|🤫|🚀|🚀🚀|🔥🔥|V|✅✅✅)$", re.IGNORECASE)

    @classmethod
    def classify(cls, text: str) -> ClassificationResult:
        clean = (text or "").strip()
        if not clean:
            return ClassificationResult(message_type=MessageClassification.MEDIA_ONLY, raw_text=clean)

        # A. Promotional & Social Links
        if cls.RE_PROMOTIONAL.search(clean):
            return ClassificationResult(message_type=MessageClassification.PROMOTIONAL, raw_text=clean)

        # B. Noise
        if cls.RE_NOISE.match(clean) or clean in ("Hello", "hello", "🚀", "🤫", "🔥", "👍", "❤", "⚡"):
            return ClassificationResult(message_type=MessageClassification.NOISE, raw_text=clean)

        # C. SL Update
        sl_match = cls.RE_SL_UPDATE.match(clean)
        if sl_match:
            return ClassificationResult(
                message_type=MessageClassification.SL_UPDATE,
                details={"raw_sl": sl_match.group(1)},
                raw_text=clean
            )
        shift_sl_match = cls.RE_SHIFT_SL.match(clean)
        if shift_sl_match:
            return ClassificationResult(
                message_type=MessageClassification.SL_UPDATE,
                details={"raw_sl": shift_sl_match.group(1), "is_shift": True},
                raw_text=clean
            )

        # D. Outcome Claims (Pips, TP hits, SL hits, Price reversed)
        pips_match = cls.RE_PIPS.search(clean)
        if pips_match:
            pips_val = None
            for g in pips_match.groups():
                if g:
                    pips_val = float(g)
                    break
            return ClassificationResult(
                message_type=MessageClassification.PROVIDER_OUTCOME,
                pips_claimed=pips_val,
                details={"pips": pips_val},
                raw_text=clean
            )
        if cls.RE_TP_HIT.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.PROVIDER_OUTCOME,
                details={"outcome": "TP_HIT"},
                raw_text=clean
            )
        if cls.RE_SL_HIT.match(clean):
            return ClassificationResult(
                message_type=MessageClassification.PROVIDER_OUTCOME,
                details={"outcome": "SL_HIT"},
                raw_text=clean
            )
        if cls.RE_PRICE_REVERSED.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.PROVIDER_OUTCOME,
                details={"outcome": "PRICE_REVERSED"},
                raw_text=clean
            )

        # E. Target Update (Multiple Targets list)
        if cls.RE_TARGET_UPDATE.search(clean) and any(char.isdigit() for char in clean):
            if not re.search(r"\b(buy|sell)\s+gold\b", clean, re.IGNORECASE):
                nums = re.findall(r"\b(\d{4,5}(?:\.\d+)?)\b", clean)
                return ClassificationResult(
                    message_type=MessageClassification.TARGET_UPDATE,
                    details={"targets": [float(n) for n in nums]},
                    raw_text=clean
                )

        # F. Trade Management Actions
        if cls.RE_EXIT_MANAGEMENT.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.TRADE_MANAGEMENT,
                management_action=ManagementAction.EXIT,
                raw_text=clean
            )
        if cls.RE_MOVE_SL_COST.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.TRADE_MANAGEMENT,
                management_action=ManagementAction.MOVE_SL_TO_ENTRY,
                raw_text=clean
            )
        if cls.RE_RISK_FREE.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.TRADE_MANAGEMENT,
                management_action=ManagementAction.RISK_FREE,
                raw_text=clean
            )
        if cls.RE_BOOK_PROFIT.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.TRADE_MANAGEMENT,
                management_action=ManagementAction.BOOK_PROFIT,
                raw_text=clean
            )

        # G. Additional Entry / Averaging
        if cls.RE_ADD_ENTRY.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.ADD_ENTRY,
                details={"averaging": True},
                raw_text=clean
            )

        # H. Signal Entry
        # (Must contain Buy/Sell + entry price or zone)
        sig_match = cls.RE_SIGNAL_ENTRY.search(clean)
        if sig_match:
            raw_sym = sig_match.group(1) if sig_match.group(1) else ""
            raw_ent = sig_match.group(2) if (sig_match.lastindex and sig_match.lastindex >= 2 and sig_match.group(2)) else sig_match.group(1)
            return ClassificationResult(
                message_type=MessageClassification.SIGNAL_ENTRY,
                details={"raw_symbol": raw_sym, "raw_entry": raw_ent},
                raw_text=clean
            )

        # I. Planning Messages
        if cls.RE_PLANNING.search(clean):
            return ClassificationResult(
                message_type=MessageClassification.PLANNING,
                raw_text=clean
            )

        # J. General Commentary
        return ClassificationResult(
            message_type=MessageClassification.COMMENTARY,
            raw_text=clean
        )

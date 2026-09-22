import re
from typing import Dict, List, Tuple

# Canonical symbol mapping
SYMBOL_ALIASES: Dict[str, str] = {
    # Gold variants (all normalize to XAUUSD)
    "GOLD": "XAUUSD",
    "XAUUSD": "XAUUSD",
    "XAU/USD": "XAUUSD",
    "XAU": "XAUUSD",
    "GOLDUSD": "XAUUSD",
    "SPOTGOLD": "XAUUSD",
    "XAU-USD": "XAUUSD",

    # Silver variants
    "SILVER": "XAGUSD",
    "XAGUSD": "XAGUSD",
    "XAG/USD": "XAGUSD",
    "XAG": "XAGUSD",
    "XAG-USD": "XAGUSD",

    # Major & Cross Forex
    "EURUSD": "EURUSD",
    "EUR/USD": "EURUSD",
    "EUR-USD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "GBP/USD": "GBPUSD",
    "GBP-USD": "GBPUSD",
    "USDJPY": "USDJPY",
    "USD/JPY": "USDJPY",
    "USD-JPY": "USDJPY",
    "GBPJPY": "GBPJPY",
    "GBP/JPY": "GBPJPY",
    "EURJPY": "EURJPY",
    "EUR/JPY": "EURJPY",
    "AUDUSD": "AUDUSD",
    "AUD/USD": "AUDUSD",
    "USDCAD": "USDCAD",
    "USD/CAD": "USDCAD",
    "USDCHF": "USDCHF",
    "USD/CHF": "USDCHF",
    "NZDUSD": "NZDUSD",
    "NZD/USD": "NZDUSD",
    "EURGBP": "EURGBP",
    "EUR/GBP": "EURGBP",

    # Indices
    "US30": "US30",
    "DJ30": "US30",
    "DJI": "US30",
    "DOW": "US30",
    "WALLSTREET30": "US30",
    "NAS100": "NAS100",
    "US100": "NAS100",
    "NDX": "NAS100",
    "NASDAQ": "NAS100",
    "SPX500": "SPX500",
    "SP500": "SPX500",
    "SPX": "SPX500",
    "GER40": "GER40",
    "GER30": "GER40",
    "DAX": "GER40",
    "DAX40": "GER40",

    # Crypto
    "BTCUSD": "BTCUSD",
    "BTC/USD": "BTCUSD",
    "BTC": "BTCUSD",
    "BITCOIN": "BTCUSD",
    "BTCUSDT": "BTCUSD",
    "ETHUSD": "ETHUSD",
    "ETH/USD": "ETHUSD",
    "ETH": "ETHUSD",
    "ETHEREUM": "ETHUSD"
}

# Side patterns (Pattern, Canonical Side, Order Type)
SIDE_PATTERNS: List[Tuple[str, str, str]] = [
    (r'\bBUY\s+LIMIT\b', "BUY", "LIMIT"),
    (r'\bBUY\s+STOP\b', "BUY", "STOP"),
    (r'\bSELL\s+LIMIT\b', "SELL", "LIMIT"),
    (r'\bSELL\s+STOP\b', "SELL", "STOP"),
    (r'\b(?:BUY\s+NOW|BUY\s+CMP|STRONG\s+BUY|BUY)\b', "BUY", "MARKET"),
    (r'\b(?:LONG\s+NOW|GO\s+LONG|LONG)\b', "BUY", "MARKET"),
    (r'\b(?:SELL\s+NOW|SELL\s+CMP|STRONG\s+SELL|SELL)\b', "SELL", "MARKET"),
    (r'\b(?:SHORT\s+NOW|GO\s+SHORT|SHORT)\b', "SELL", "MARKET"),
]

# Stop Loss Extraction Patterns (Named capture group: sl_price)
SL_PATTERNS: List[str] = [
    r'\b(?:STOP\s*LOSS|STOPLOSS|SL)\s*[:=-]?\s*@?\s*(?P<sl_price>[0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)\b',
    r'\b(?:STOP)\s*[:=-]\s*(?P<sl_price>[0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)\b',
    r'\bSL\s+(?P<sl_price>[0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)\b'
]

# Take Profit Extraction Patterns
# Note: (?!\\d) ensures "TP 4360" is not parsed as TP4 with price 360
TP_NUMBERED_PATTERN = r'\b(?:TP\s*[1-5](?!\d)|TARGET\s*[1-5](?!\d)|TAKE\s*PROFIT\s*[1-5](?!\d))\s*[:=-]?\s*@?\s*(?P<tp_price>[0-9]+(?:\.[0-9]+)?)\b'
TP_GENERIC_PATTERNS: List[str] = [
    r'\b(?:TAKE\s*PROFIT|TAKEPROFIT|TARGET|TP)\s*[:=-]?\s*@?\s*(?P<tp_price>[0-9]+(?:\.[0-9]+)?)\b',
    r'\bTP\s+(?P<tp_price>[0-9]+(?:\.[0-9]+)?)\b'
]

# Entry Extraction Patterns
ENTRY_EXPLICIT_PATTERNS: List[str] = [
    r'(?:ENTRY|ENTRADA|PRICE|CMP|OPEN\s*AT)\s*[:=-]?\s*@?\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)',
    r'@\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)',
    r'\b(?:CMP|NOW)\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?(?:[_\-][0-9]+(?:\.[0-9]+)?)*)\b',
]

def preprocess_text(text: str) -> str:
    """Standardizes dashes, quotes, and whitespace while preserving textual content."""
    if not text:
        return ""
    cleaned = text.replace("’", "'").replace("“", '"').replace("”", '"')
    cleaned = cleaned.replace("–", "-").replace("—", "-").replace("−", "-")
    cleaned = re.sub(r'\b([0-2]?[0-9]):([0-5][0-9])\b', r'\1_TIME_\2', cleaned)
    cleaned = re.sub(r'([0-9]+(?:\.[0-9]+)?)\s*%', r'\1_PCT', cleaned)
    return cleaned

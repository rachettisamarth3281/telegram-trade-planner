from typing import Dict, Any, Optional

# Instrument specifications for calculating pips, contract sizes, and price increments
INSTRUMENT_SPECS: Dict[str, Dict[str, Any]] = {
    # Metals
    "XAUUSD": {
        "name": "Gold / US Dollar",
        "category": "METALS",
        "pip_size": 0.10,          # 1 pip = 0.10 price movement (10 points)
        "point_size": 0.01,
        "contract_size": 100,      # 100 oz per standard lot
        "digits": 2,
        "aliases": ["GOLD", "XAU", "XAU/USD", "GOLDUSD", "SPOTGOLD"]
    },
    "XAGUSD": {
        "name": "Silver / US Dollar",
        "category": "METALS",
        "pip_size": 0.01,
        "point_size": 0.001,
        "contract_size": 5000,
        "digits": 3,
        "aliases": ["SILVER", "XAG", "XAG/USD"]
    },

    # Major Forex Pairs (0.0001 pip)
    "EURUSD": {
        "name": "Euro / US Dollar",
        "category": "FOREX",
        "pip_size": 0.0001,
        "point_size": 0.00001,
        "contract_size": 100000,
        "digits": 5,
        "aliases": ["EUR/USD", "EUR-USD"]
    },
    "GBPUSD": {
        "name": "British Pound / US Dollar",
        "category": "FOREX",
        "pip_size": 0.0001,
        "point_size": 0.00001,
        "contract_size": 100000,
        "digits": 5,
        "aliases": ["GBP/USD", "CABLE"]
    },
    "AUDUSD": {
        "name": "Australian Dollar / US Dollar",
        "category": "FOREX",
        "pip_size": 0.0001,
        "point_size": 0.00001,
        "contract_size": 100000,
        "digits": 5,
        "aliases": ["AUD/USD", "AUSSIE"]
    },
    "NZDUSD": {
        "name": "New Zealand Dollar / US Dollar",
        "category": "FOREX",
        "pip_size": 0.0001,
        "point_size": 0.00001,
        "contract_size": 100000,
        "digits": 5,
        "aliases": ["NZD/USD", "KIWI"]
    },
    "USDCAD": {
        "name": "US Dollar / Canadian Dollar",
        "category": "FOREX",
        "pip_size": 0.0001,
        "point_size": 0.00001,
        "contract_size": 100000,
        "digits": 5,
        "aliases": ["USD/CAD", "LOONIE"]
    },
    "USDCHF": {
        "name": "US Dollar / Swiss Franc",
        "category": "FOREX",
        "pip_size": 0.0001,
        "point_size": 0.00001,
        "contract_size": 100000,
        "digits": 5,
        "aliases": ["USD/CHF", "SWISSY"]
    },

    # JPY Pairs (0.01 pip)
    "USDJPY": {
        "name": "US Dollar / Japanese Yen",
        "category": "FOREX",
        "pip_size": 0.01,
        "point_size": 0.001,
        "contract_size": 100000,
        "digits": 3,
        "aliases": ["USD/JPY", "GJ", "UJ"]
    },
    "GBPJPY": {
        "name": "British Pound / Japanese Yen",
        "category": "FOREX",
        "pip_size": 0.01,
        "point_size": 0.001,
        "contract_size": 100000,
        "digits": 3,
        "aliases": ["GBP/JPY", "GU"]
    },
    "EURJPY": {
        "name": "Euro / Japanese Yen",
        "category": "FOREX",
        "pip_size": 0.01,
        "point_size": 0.001,
        "contract_size": 100000,
        "digits": 3,
        "aliases": ["EUR/JPY", "EJ"]
    },
    "AUDJPY": {
        "name": "Australian Dollar / Japanese Yen",
        "category": "FOREX",
        "pip_size": 0.01,
        "point_size": 0.001,
        "contract_size": 100000,
        "digits": 3,
        "aliases": ["AUD/JPY"]
    },
    "CADJPY": {
        "name": "Canadian Dollar / Japanese Yen",
        "category": "FOREX",
        "pip_size": 0.01,
        "point_size": 0.001,
        "contract_size": 100000,
        "digits": 3,
        "aliases": ["CAD/JPY"]
    },
    "CHFJPY": {
        "name": "Swiss Franc / Japanese Yen",
        "category": "FOREX",
        "pip_size": 0.01,
        "point_size": 0.001,
        "contract_size": 100000,
        "digits": 3,
        "aliases": ["CHF/JPY"]
    },
    "EURGBP": {
        "name": "Euro / British Pound",
        "category": "FOREX",
        "pip_size": 0.0001,
        "point_size": 0.00001,
        "contract_size": 100000,
        "digits": 5,
        "aliases": ["EUR/GBP"]
    },

    # Indices
    "US30": {
        "name": "Dow Jones Industrial Average",
        "category": "INDICES",
        "pip_size": 1.0,
        "point_size": 1.0,
        "contract_size": 1,
        "digits": 2,
        "aliases": ["DJ30", "DJI", "DOW", "US30USD", "WALLSTREET30", "WS30"]
    },
    "NAS100": {
        "name": "Nasdaq 100",
        "category": "INDICES",
        "pip_size": 1.0,
        "point_size": 0.1,
        "contract_size": 1,
        "digits": 2,
        "aliases": ["US100", "NDX", "USTECH100", "NASDAQ", "NAS100USD"]
    },
    "SPX500": {
        "name": "S&P 500",
        "category": "INDICES",
        "pip_size": 0.1,
        "point_size": 0.01,
        "contract_size": 1,
        "digits": 2,
        "aliases": ["US500", "SP500", "SPX", "USA500"]
    },
    "GER40": {
        "name": "German DAX 40",
        "category": "INDICES",
        "pip_size": 1.0,
        "point_size": 0.1,
        "contract_size": 1,
        "digits": 2,
        "aliases": ["GER30", "DAX", "DAX40", "DAX30", "DE40", "DE30"]
    },

    # Crypto
    "BTCUSD": {
        "name": "Bitcoin / US Dollar",
        "category": "CRYPTO",
        "pip_size": 1.0,
        "point_size": 0.01,
        "contract_size": 1,
        "digits": 2,
        "aliases": ["BTC", "BTC/USD", "BITCOIN", "BTCUSDT"]
    },
    "ETHUSD": {
        "name": "Ethereum / US Dollar",
        "category": "CRYPTO",
        "pip_size": 0.1,
        "point_size": 0.01,
        "contract_size": 1,
        "digits": 2,
        "aliases": ["ETH", "ETH/USD", "ETHEREUM", "ETHUSDT"]
    }
}

# Alias lookup mapping for fast normalization
ALIAS_MAP: Dict[str, str] = {}
for canonical_sym, spec in INSTRUMENT_SPECS.items():
    ALIAS_MAP[canonical_sym.upper()] = canonical_sym
    for alias in spec.get("aliases", []):
        clean_alias = alias.upper().replace("/", "").replace("-", "").replace(" ", "")
        ALIAS_MAP[clean_alias] = canonical_sym
        ALIAS_MAP[alias.upper()] = canonical_sym

def get_instrument_spec(symbol: str) -> Optional[Dict[str, Any]]:
    """Returns instrument specs for a normalized or raw symbol name."""
    clean = symbol.upper().strip().replace("/", "").replace("-", "").replace(" ", "")
    canonical = ALIAS_MAP.get(clean) or ALIAS_MAP.get(symbol.upper().strip())
    if canonical and canonical in INSTRUMENT_SPECS:
        return INSTRUMENT_SPECS[canonical]
    return None

def normalize_symbol_name(symbol: str) -> Optional[str]:
    """Resolves an alias to the canonical symbol name."""
    clean = symbol.upper().strip().replace("/", "").replace("-", "").replace(" ", "")
    return ALIAS_MAP.get(clean) or ALIAS_MAP.get(symbol.upper().strip())


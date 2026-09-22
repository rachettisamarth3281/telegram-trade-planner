import re
from enum import Enum
from typing import Optional, Tuple, List
from decimal import Decimal, ROUND_HALF_UP

class EntryReferencePolicy(str, Enum):
    ZONE_MIDPOINT = "ZONE_MIDPOINT"
    ZONE_FIRST_PRICE = "ZONE_FIRST_PRICE"
    ZONE_SECOND_PRICE = "ZONE_SECOND_PRICE"
    FIRST_TOUCH = "FIRST_TOUCH"
    MANUAL = "MANUAL"

class EntryZoneParser:
    """
    Parses complex trading price ranges, underscore notation, and abbreviated shorthands.
    
    Examples:
    - "4350_53"     -> low=4350.0, high=4353.0
    - "4350_47"     -> low=4347.0, high=4350.0 (47 takes prefix 43 -> 4347)
    - "4025_30"     -> low=4025.0, high=4030.0 (30 takes prefix 40 -> 4030)
    - "4401_4398"   -> low=4398.0, high=4401.0
    - "4597_01"     -> low=4597.0, high=4601.0 (century crossover from 4597 to 4601)
    - "4023_24_25"  -> low=4023.0, high=4025.0
    - "4725-24"     -> low=4724.0, high=4725.0
    - "4564"        -> low=4564.0, high=4564.0
    """

    @classmethod
    def expand_abbreviation(cls, base_num_str: str, abbrev_str: str) -> float:
        """
        Intelligently expands an abbreviated number (e.g. base='4350', abbrev='47' -> 4347).
        Handles century crossovers (e.g. base='4597', abbrev='01' -> 4601).
        """
        clean_base = base_num_str.strip()
        clean_abbrev = abbrev_str.strip()
        base_int_part = clean_base.split(".")[0]
        abbrev_int_part = clean_abbrev.split(".")[0]
        if len(abbrev_int_part) >= len(base_int_part):
            return float(clean_abbrev.replace(",", "."))

        base_val = float(clean_base)
        prefix_len = len(base_int_part) - len(abbrev_int_part)
        
        if prefix_len <= 0:
            return float(clean_abbrev)

        prefix = base_int_part[:prefix_len]
        candidate_str = f"{prefix}{clean_abbrev}"
        candidate_val = float(candidate_str)

        # Century crossover check (e.g. 4597 and 01 -> candidate 4501, but diff is -96. 4601 diff is +4!)
        diff = candidate_val - base_val
        if diff < -50:
            # Try incrementing prefix by 1
            try:
                inc_prefix = str(int(prefix) + 1)
                alt_candidate = float(f"{inc_prefix}{clean_abbrev}")
                if abs(alt_candidate - base_val) < abs(candidate_val - base_val):
                    return alt_candidate
            except ValueError:
                pass
        elif diff > 50:
            # Try decrementing prefix by 1 (e.g. 4602 and 98 -> 4598)
            try:
                dec_prefix = str(int(prefix) - 1)
                alt_candidate = float(f"{dec_prefix}{clean_abbrev}")
                if abs(alt_candidate - base_val) < abs(candidate_val - base_val):
                    return alt_candidate
            except ValueError:
                pass

        return candidate_val

    @classmethod
    def parse_zone(
        cls,
        raw_price_str: str,
        side: Optional[str] = None,
        policy: EntryReferencePolicy = EntryReferencePolicy.ZONE_MIDPOINT
    ) -> Tuple[float, float, float, List[float]]:
        """
        Parses a raw price string into (zone_low, zone_high, reference_price, all_prices).
        """
        clean = (raw_price_str or "").strip()
        if not clean:
            return 0.0, 0.0, 0.0, []

        # Remove url links like https://t.me/4350_47 or @4350_47
        clean = re.sub(r"https?://\S+", "", clean)
        clean = clean.replace("@", "").strip()

        # Split by underscore, hyphen, or space
        parts = [p.strip() for p in re.split(r"[_ \-]+", clean) if p.strip()]

        if not parts:
            return 0.0, 0.0, 0.0, []

        first_str = parts[0]
        try:
            first_price = float(first_str.replace(",", "."))
        except ValueError:
            return 0.0, 0.0, 0.0, []

        parsed_prices: List[float] = [first_price]

        for p_str in parts[1:]:
            try:
                first_int_len = len(first_str.split(".")[0])
                p_int_len = len(p_str.split(".")[0])
                if p_int_len < first_int_len:
                    expanded = cls.expand_abbreviation(first_str, p_str)
                    parsed_prices.append(expanded)
                else:
                    parsed_prices.append(float(p_str.replace(",", ".")))
            except ValueError:
                continue

        zone_low = min(parsed_prices)
        zone_high = max(parsed_prices)

        # Calculate reference price based on policy
        ref_price = cls.calculate_reference_price(
            zone_low=zone_low,
            zone_high=zone_high,
            first_price=parsed_prices[0],
            second_price=parsed_prices[1] if len(parsed_prices) > 1 else parsed_prices[0],
            side=side,
            policy=policy
        )

        return zone_low, zone_high, ref_price, parsed_prices

    @classmethod
    def calculate_reference_price(
        cls,
        zone_low: float,
        zone_high: float,
        first_price: float,
        second_price: float,
        side: Optional[str] = None,
        policy: EntryReferencePolicy = EntryReferencePolicy.ZONE_MIDPOINT
    ) -> float:
        if zone_low == zone_high or len([p for p in (first_price, second_price) if p > 0]) <= 1:
            return first_price

        if policy == EntryReferencePolicy.ZONE_MIDPOINT:
            return round((zone_low + zone_high) / 2.0, 5)
        elif policy == EntryReferencePolicy.ZONE_FIRST_PRICE:
            return first_price
        elif policy == EntryReferencePolicy.ZONE_SECOND_PRICE:
            return second_price
        elif policy == EntryReferencePolicy.FIRST_TOUCH:
            # For BUY, entering from above touches zone_high first
            # For SELL, entering from below touches zone_low first
            if (side or "").upper() in ("BUY", "LONG"):
                return zone_high
            else:
                return zone_low
        return round((zone_low + zone_high) / 2.0, 5)

    @classmethod
    def parse_sl_value(cls, raw_sl_str: str, side: Optional[str] = None) -> float:
        """
        Parses Stop Loss string which might be a single number (e.g. '4358') or a range (e.g. '4328_27', '4468_69.5').
        For BUY trades, returns conservative lower SL. For SELL trades, returns conservative higher SL.
        """
        low, high, _, prices = cls.parse_zone(raw_sl_str)
        if not prices:
            return 0.0
        if len(prices) == 1:
            return prices[0]

        side_u = (side or "").upper()
        if side_u in ("BUY", "LONG"):
            # Lower SL gives wider, safer stop for BUY
            return low
        else:
            # Higher SL gives wider, safer stop for SELL
            return high

import pytest
from app.parser.zone_parser import EntryZoneParser, EntryReferencePolicy

def test_entry_zone_standard_ranges():
    # 4350_53 -> [4350, 4353]
    low, high, ref, prices = EntryZoneParser.parse_zone("4350_53")
    assert low == 4350.0
    assert high == 4353.0
    assert ref == 4351.5
    assert prices == [4350.0, 4353.0]

def test_entry_zone_abbreviated_second_number_lower():
    # 4350_47 -> [4347, 4350]
    low, high, ref, prices = EntryZoneParser.parse_zone("4350_47")
    assert low == 4347.0
    assert high == 4350.0
    assert ref == 4348.5
    assert prices == [4350.0, 4347.0]

def test_entry_zone_abbreviated_second_number_higher():
    # 4025_30 -> [4025, 4030]
    low, high, ref, prices = EntryZoneParser.parse_zone("4025_30")
    assert low == 4025.0
    assert high == 4030.0
    assert prices == [4025.0, 4030.0]

def test_entry_zone_century_crossover():
    # 4597_01 -> [4597, 4601]
    low, high, ref, prices = EntryZoneParser.parse_zone("4597_01")
    assert low == 4597.0
    assert high == 4601.0
    assert prices == [4597.0, 4601.0]

def test_entry_zone_triple_shorthand():
    # 4023_24_25 -> [4023, 4025]
    low, high, ref, prices = EntryZoneParser.parse_zone("4023_24_25")
    assert low == 4023.0
    assert high == 4025.0
    assert prices == [4023.0, 4024.0, 4025.0]

def test_entry_zone_hyphenated():
    # 4725-24 -> [4724, 4725]
    low, high, ref, prices = EntryZoneParser.parse_zone("4725-24")
    assert low == 4724.0
    assert high == 4725.0

def test_entry_reference_policies():
    low = 4350.0
    high = 4354.0
    first = 4350.0
    second = 4354.0
    
    # Midpoint
    ref_mid = EntryZoneParser.calculate_reference_price(low, high, first, second, policy=EntryReferencePolicy.ZONE_MIDPOINT)
    assert ref_mid == 4352.0

    # First price
    ref_first = EntryZoneParser.calculate_reference_price(low, high, first, second, policy=EntryReferencePolicy.ZONE_FIRST_PRICE)
    assert ref_first == 4350.0

    # First touch BUY
    ref_buy = EntryZoneParser.calculate_reference_price(low, high, first, second, side="BUY", policy=EntryReferencePolicy.FIRST_TOUCH)
    assert ref_buy == 4354.0

    # First touch SELL
    ref_sell = EntryZoneParser.calculate_reference_price(low, high, first, second, side="SELL", policy=EntryReferencePolicy.FIRST_TOUCH)
    assert ref_sell == 4350.0

def test_parse_sl_values():
    # Single number
    assert EntryZoneParser.parse_sl_value("4358") == 4358.0
    
    # Range for BUY (conservative is lower)
    assert EntryZoneParser.parse_sl_value("4328_27", side="BUY") == 4327.0
    
    # Range for SELL (conservative is higher)
    assert EntryZoneParser.parse_sl_value("4328_27", side="SELL") == 4328.0

    # Decimals in SL
    assert EntryZoneParser.parse_sl_value("4468_69.5", side="SELL") == 4469.5


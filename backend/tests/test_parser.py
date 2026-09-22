import pytest
from app.services.signal_parser import SignalParser
from app.services.signal_normalizer import SignalNormalizer
from app.services.signal_validator import SignalValidator

def test_prompt_example_sell_gold():
    text = "Sell gold @ 4350.53\nSL 4358"
    parsed = SignalParser.parse(text)
    assert parsed.symbol == "XAUUSD"
    assert parsed.side == "SELL"
    assert parsed.entry_price == 4350.53
    assert parsed.provider_sl == 4358.00
    assert parsed.provider_tps == []

    norm = SignalNormalizer.normalize(parsed)
    assert norm.symbol == "XAUUSD"
    assert norm.side == "SELL"
    assert norm.entry_price == 4350.53
    assert norm.provider_sl == 4358.00

    val = SignalValidator.validate(norm)
    assert val.is_valid is True
    assert val.status == "VALID"
    assert val.effective_sl == 4358.00

def test_forex_signal_with_multiple_tps():
    text = """
    🔥 VIP EUR/USD SIGNAL 🔥
    BUY EURUSD @ 1.08500
    SL: 1.08000
    TP1: 1.09000
    TP2: 1.09500
    TP3: 1.10000
    """
    parsed = SignalParser.parse(text)
    assert parsed.symbol == "EURUSD"
    assert parsed.side == "BUY"
    assert parsed.entry_price == 1.08500
    assert parsed.provider_sl == 1.08000
    assert parsed.provider_tps == [1.09000, 1.09500, 1.10000]

    norm = SignalNormalizer.normalize(parsed)
    val = SignalValidator.validate(norm)
    assert val.is_valid is True
    assert val.status == "VALID"

def test_crypto_signal():
    text = "BTC/USD LONG @ 65000 SL 63500 TP 68000"
    parsed = SignalParser.parse(text)
    assert parsed.symbol == "BTCUSD"
    assert parsed.side == "BUY"
    assert parsed.entry_price == 65000.0
    assert parsed.provider_sl == 63500.0
    assert parsed.provider_tps == [68000.0]

def test_indices_signal():
    text = "US30 SHORT 38500 SL 38650 TP1 38200 TP2 38000"
    parsed = SignalParser.parse(text)
    assert parsed.symbol == "US30"
    assert parsed.side == "SELL"
    assert parsed.entry_price == 38500.0
    assert parsed.provider_sl == 38650.0
    assert len(parsed.provider_tps) == 2

def test_missing_sl_rejection():
    # Never invent an SL: strict rejection
    text = "BUY GOLD @ 2350.00 TP 2380.00"
    parsed = SignalParser.parse(text)
    norm = SignalNormalizer.normalize(parsed)
    val = SignalValidator.validate(norm)
    assert val.is_valid is False
    assert val.status == "SKIPPED_NO_SL"
    assert any("NO_VALID_STOP_LOSS" in r for r in val.rejection_reasons)

def test_directional_invalidity_buy_sl_above_entry():
    text = "BUY EURUSD @ 1.0850 SL 1.0900"
    parsed = SignalParser.parse(text)
    norm = SignalNormalizer.normalize(parsed)
    val = SignalValidator.validate(norm)
    assert val.is_valid is False
    assert val.status == "INVALID"
    assert any("Stop Loss" in r and "must be lower" in r for r in val.rejection_reasons)

def test_directional_invalidity_sell_sl_below_entry():
    text = "SELL XAUUSD @ 2350.00 SL 2340.00"
    parsed = SignalParser.parse(text)
    norm = SignalNormalizer.normalize(parsed)
    val = SignalValidator.validate(norm)
    assert val.is_valid is False
    assert val.status == "INVALID"
    assert any("Stop Loss" in r and "must be higher" in r for r in val.rejection_reasons)

def test_non_signal_text():
    text = "Good morning traders! Let's get ready for NFP today."
    parsed = SignalParser.parse(text)
    assert parsed.confidence < 0.4
    norm = SignalNormalizer.normalize(parsed)
    val = SignalValidator.validate(norm)
    assert val.is_valid is False


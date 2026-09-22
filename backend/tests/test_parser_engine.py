import pytest
from app.parser.engine import SignalParserEngine
from app.parser.states import ParsingState

# 1. Normal SELL
def test_normal_sell():
    text = "Sell gold @ 4350.53\nSL 4358"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "SELL"
    assert res.entry_price == 4350.53
    assert res.stop_loss == 4358.00
    assert res.take_profit is None
    assert res.diagnostics.state == ParsingState.VALID
    assert res.is_valid is True

# 2. Normal BUY
def test_normal_buy():
    text = "BUY EURUSD @ 1.08500\nSL 1.08000\nTP 1.09500"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "EURUSD"
    assert res.side == "BUY"
    assert res.entry_price == 1.08500
    assert res.stop_loss == 1.08000
    assert res.take_profit == 1.09500
    assert res.diagnostics.state == ParsingState.VALID

# 3. GOLD alias normalizes to XAUUSD
def test_gold_alias():
    text = "BUY GOLD 4350\nSL 4342\nTP 4360"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.0
    assert res.stop_loss == 4342.0
    assert res.take_profit == 4360.0
    assert res.diagnostics.state == ParsingState.VALID

# 4. XAUUSD canonical
def test_xauusd_canonical():
    text = "SELL XAUUSD 4350.53\nSL: 4358\nTP: 4335"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "SELL"
    assert res.entry_price == 4350.53
    assert res.stop_loss == 4358.0
    assert res.take_profit == 4335.0
    assert res.diagnostics.state == ParsingState.VALID

# 5. Missing TP
def test_missing_tp():
    text = "XAUUSD SELL @ 4350.53 SL 4358"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "SELL"
    assert res.entry_price == 4350.53
    assert res.stop_loss == 4358.0
    assert res.take_profit is None
    assert "take_profit" in res.diagnostics.missing_fields
    assert res.diagnostics.state == ParsingState.VALID

# 6. Missing SL (State must be PARTIAL, never fabricate SL)
def test_missing_sl():
    text = "LONG XAUUSD @ 4350"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.0
    assert res.stop_loss is None
    assert "stop_loss" in res.diagnostics.missing_fields
    assert res.diagnostics.state == ParsingState.PARTIAL
    assert res.is_partial is True
    assert res.is_valid is False

# 7. Missing Entry (State must be PARTIAL)
def test_missing_entry():
    text = "BUY GOLD\nSL 4340\nTP 4360"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price is None
    assert res.stop_loss == 4340.0
    assert "entry_price" in res.diagnostics.missing_fields
    assert res.diagnostics.state == ParsingState.PARTIAL

# 8. Extra emojis
def test_extra_emojis():
    text = "🔥🚀 VIP GOLD BUY NOW @ 4350.00 💰💰 SL 4340.00 🎯 TP 4370.00 🚀"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.0
    assert res.stop_loss == 4340.0
    assert res.take_profit == 4370.0
    assert res.diagnostics.state == ParsingState.VALID

# 9. Different spacing
def test_different_spacing():
    text = "BUY   GOLD    @    4350.50     SL    4340.00     TP    4360.00"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.50
    assert res.stop_loss == 4340.00
    assert res.take_profit == 4360.00
    assert res.diagnostics.state == ParsingState.VALID

# 10. Different capitalization (all lowercase)
def test_different_capitalization():
    text = "sell gold @ 4350.53 sl 4358 tp 4330"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "SELL"
    assert res.entry_price == 4350.53
    assert res.stop_loss == 4358.0
    assert res.take_profit == 4330.0
    assert res.diagnostics.state == ParsingState.VALID

# 11. Multiple numbers and percentage in message
def test_multiple_numbers():
    text = "Risk 1% of account: BUY EURUSD @ 1.0850 SL 1.0800 TP 1.0900"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "EURUSD"
    assert res.side == "BUY"
    assert res.entry_price == 1.0850
    assert res.stop_loss == 1.0800
    assert res.take_profit == 1.0900
    assert res.diagnostics.state == ParsingState.VALID

# 12. TP before SL
def test_tp_before_sl():
    text = "BUY GOLD @ 4350\nTP: 4370\nSL: 4340"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.0
    assert res.take_profit == 4370.0
    assert res.stop_loss == 4340.0
    assert res.diagnostics.state == ParsingState.VALID

# 13. SL before TP
def test_sl_before_tp():
    text = "BUY GOLD @ 4350\nSL: 4340\nTP: 4370"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.0
    assert res.stop_loss == 4340.0
    assert res.take_profit == 4370.0
    assert res.diagnostics.state == ParsingState.VALID

# 14. Unrelated Telegram messages
def test_unrelated_message():
    text = "Good morning everyone! Let's have a great trading day."
    res = SignalParserEngine.parse(text)
    assert res.symbol is None
    assert res.side is None
    assert res.diagnostics.state == ParsingState.UNKNOWN
    assert res.diagnostics.parser_confidence == 0.0

# 15. Malformed messages
def test_malformed_message():
    text = "BUY SOMETHING SL ABC"
    res = SignalParserEngine.parse(text)
    assert res.side == "BUY"
    assert res.symbol is None
    assert res.stop_loss is None
    assert res.diagnostics.state in [ParsingState.INVALID, ParsingState.UNKNOWN]

# 16. Decimal prices (high precision Forex)
def test_decimal_prices():
    text = "BUY EURUSD @ 1.08523 SL 1.08115 TP 1.09450"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "EURUSD"
    assert res.side == "BUY"
    assert res.entry_price == 1.08523
    assert res.stop_loss == 1.08115
    assert res.take_profit == 1.09450
    assert res.diagnostics.state == ParsingState.VALID

# 17. Messages containing timestamps
def test_message_with_timestamp():
    text = "At 14:30 EST: BUY GOLD @ 4350.00 SL 4340.00 TP 4365.00"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.00
    assert res.stop_loss == 4340.00
    assert res.take_profit == 4365.00
    assert res.diagnostics.state == ParsingState.VALID

# 18. Messages containing percentages
def test_message_with_percentages():
    text = "Target gain +50%: BUY XAUUSD @ 4350 SL 4340 TP 4360"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.0
    assert res.stop_loss == 4340.0
    assert res.take_profit == 4360.0
    assert res.diagnostics.state == ParsingState.VALID

# 19. Messages containing multiple targets
def test_multiple_targets():
    text = "BUY GOLD 4350 SL 4340 TP1 4360 TP2 4370 TP3 4385"
    res = SignalParserEngine.parse(text)
    assert res.symbol == "XAUUSD"
    assert res.side == "BUY"
    assert res.entry_price == 4350.0
    assert res.stop_loss == 4340.0
    assert res.take_profit == 4360.0
    assert res.take_profits == [4360.0, 4370.0, 4385.0]
    assert len(res.diagnostics.detected_tps) == 3
    assert res.diagnostics.state == ParsingState.VALID

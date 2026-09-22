import pytest
from app.parser.classifier import MessageClassifier, MessageClassification, ManagementAction

def test_classify_signal_entries():
    samples = [
        ("Buy gold @ 4335_32", MessageClassification.SIGNAL_ENTRY),
        ("Sell Gold @4042_47", MessageClassification.SIGNAL_ENTRY),
        ("Buy Gold @4455_50", MessageClassification.SIGNAL_ENTRY),
        ("Buy gold @ 4766_65", MessageClassification.SIGNAL_ENTRY),
        ("Buy gold @ 4401_4398", MessageClassification.SIGNAL_ENTRY),
        ("Sell gold @ 4350_53", MessageClassification.SIGNAL_ENTRY),
        ("Sell gold @ 4391_94", MessageClassification.SIGNAL_ENTRY),
        ("Buy gold @ 4581_78", MessageClassification.SIGNAL_ENTRY),
        ("Buy gold @ 4014_15", MessageClassification.SIGNAL_ENTRY),
        ("Sell gold @ 3989_90", MessageClassification.SIGNAL_ENTRY),
        ("Sell Gold @4055_60", MessageClassification.SIGNAL_ENTRY),
    ]
    for text, expected in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == expected, f"Failed for '{text}': got {res.message_type}, expected {expected}"

def test_classify_sl_updates():
    samples = [
        ("SL 4358", MessageClassification.SL_UPDATE),
        ("Sl 4328_27", MessageClassification.SL_UPDATE),
        ("SL : 4165", MessageClassification.SL_UPDATE),
        ("SL 4468_69.5", MessageClassification.SL_UPDATE),
        ("SL 4501_92", MessageClassification.SL_UPDATE),
        ("SL 4393", MessageClassification.SL_UPDATE),
        ("SL 4410", MessageClassification.SL_UPDATE),
        ("SL 4500", MessageClassification.SL_UPDATE),
        ("SL 4725", MessageClassification.SL_UPDATE),
        ("Shift SL to 4116", MessageClassification.SL_UPDATE),
    ]
    for text, expected in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == expected, f"Failed for '{text}': got {res.message_type}"

def test_classify_target_updates():
    samples = [
        ("Target 🎯 \n\n4180\n\n4190\n\n4200", MessageClassification.TARGET_UPDATE),
        ("Target 🎯 \n\n4584 ✅\n\n4589\n\n4594", MessageClassification.TARGET_UPDATE),
        ("Target 🎯 \n\n4495\n\n4490\n\n4480", MessageClassification.TARGET_UPDATE),
        ("Target 🎯 \n\n4613\n\n4618\n\n4622", MessageClassification.TARGET_UPDATE),
        ("Target 🎯 \n\n4048\n\n4040\n\n4030", MessageClassification.TARGET_UPDATE),
    ]
    for text, expected in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == expected, f"Failed for '{text}'"

def test_classify_trade_management():
    samples = [
        ("Risk free", ManagementAction.RISK_FREE),
        ("Risk Free", ManagementAction.RISK_FREE),
        ("karo risk free", ManagementAction.RISK_FREE),
        ("Trail SL to cost", ManagementAction.MOVE_SL_TO_ENTRY),
        ("C2c", ManagementAction.MOVE_SL_TO_ENTRY),
        ("SL c2c", ManagementAction.MOVE_SL_TO_ENTRY),
        ("Exit", ManagementAction.EXIT),
        ("Book all", ManagementAction.EXIT),
        ("Book full", ManagementAction.EXIT),
        ("Full booked ✅", ManagementAction.EXIT),
        ("profit Booking karte chalna", ManagementAction.BOOK_PROFIT),
        ("Booking karte chalna dosto", ManagementAction.BOOK_PROFIT),
    ]
    for text, expected_action in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == MessageClassification.TRADE_MANAGEMENT, f"Failed for '{text}'"
        assert res.management_action == expected_action

def test_classify_provider_outcomes():
    samples = [
        ("30 pips ✅", 30.0),
        ("40 pips ✅🔥🔥", 40.0),
        ("50 pips ✅🔥🔥", 50.0),
        ("70 pips ✅🔥🔥", 70.0),
        ("80 pips ✅🔥🔥", 80.0),
        ("100 pips ✅🔥", 100.0),
        ("120 pips done ✅🔥🔥", 120.0),
        ("150 pips ✅🔥🔥🚀", 150.0),
        ("180 pips ✅ Booked 👍", 180.0),
        ("200 pips ✅🔥🔥", 200.0),
        ("Poore 200 pips ✅🔥🔥", 200.0),
        ("Crazy 100 pips ✅🔥🔥", 100.0),
    ]
    for text, expected_pips in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == MessageClassification.PROVIDER_OUTCOME
        assert res.pips_claimed == expected_pips

def test_classify_outcome_states():
    samples = [
        ("SL hit", "SL_HIT"),
        ("Exit SL hit", "SL_HIT"),
        ("Price reversed", "PRICE_REVERSED"),
        ("Ok price reversed", "PRICE_REVERSED"),
        ("Target 🎯 1 ✅", "TP_HIT"),
        ("2nd target 🎯✅", "TP_HIT"),
        ("All target 🎯✅", "TP_HIT"),
        ("TP 1 HIT 🎯", "TP_HIT"),
    ]
    for text, _ in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == MessageClassification.PROVIDER_OUTCOME

def test_classify_planning():
    samples = [
        "Planning for sell",
        "Planning for buy",
        "Plan change",
        "Now planning for buy",
        "Ready for buying",
        "Ready for sell",
        "Finding level for perfect entry",
        "Waiting for perfect level",
        "Analysing market",
        "Ready for quick scalp",
    ]
    for text in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == MessageClassification.PLANNING

def test_classify_add_entry():
    samples = [
        "Personally adding few qty.",
        "If it comes down to 4398 I will personally add 1 lot",
        "Added 1 lot near 43",
        "Also buy at 4451",
        "2 more lots add on",
        "Holding 2 lots",
    ]
    for text in samples:
        res = MessageClassifier.classify(text)
        assert res.message_type == MessageClassification.ADD_ENTRY

def test_classify_promotional_and_noise():
    promos = [
        "https://www.youtube.com/live/LS8mMctzFZ4?si=PqrU3BQ7d5OHH74e",
        "Join LiveStream 👑💵💵",
        "Join Live 💰💰",
        "Share Profit Screenshot @teamshubham03",
        "Kisne Kitna Chapa",
        "https://whatsapp.com/channel/0029Vam6Rh5545v0nUoUEU2e",
    ]
    for text in promos:
        res = MessageClassifier.classify(text)
        assert res.message_type == MessageClassification.PROMOTIONAL

    noise = [
        "Hello",
        "Good Morning Traders 🫶",
        "🚀",
        "🤫",
        "🔥🔥",
    ]
    for text in noise:
        res = MessageClassifier.classify(text)
        assert res.message_type == MessageClassification.NOISE


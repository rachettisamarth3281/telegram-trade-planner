"""
Real-world Telegram message dataset extracted from 'Shubham Vip Club 👑' export.
Contains authentic message sequences across multiple months covering:
- Standalone and multi-message signal entries
- Separate SL messages
- Multiple target updates
- Trade management events (Risk free, SL c2c, Book all, Partial exit)
- Provider outcome claims (30 pips, 50 pips, 80 pips, 150 pips, 200 pips, SL hit, Price reversed)
- Planning messages ("Planning for sell", "Plan change", "Now planning for buy")
- Additional entry & Averaging ("Personally adding few qty.", "Also buy at 4451", "Buy down if you got")
- Noise, commentary, and promotional broadcasts
"""

REAL_TELEGRAM_MESSAGES = [
    # --- Sequence 1: September 16, 2026 (Morning Trade 1) ---
    {"id": 7109, "date": "16.09.2026 13:14:49 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 7110, "date": "16.09.2026 13:15:03 UTC+05:30", "text": "Planning for buy", "type": "PLANNING"},
    {"id": 7111, "date": "16.09.2026 13:15:24 UTC+05:30", "text": "Thoda risky trade hai", "type": "COMMENTARY"},
    {"id": 7112, "date": "16.09.2026 13:16:25 UTC+05:30", "text": "Buy gold @ 4335_32", "type": "SIGNAL_ENTRY", "side": "BUY", "symbol": "XAUUSD", "low": 4332.0, "high": 4335.0},
    {"id": 7113, "date": "16.09.2026 13:17:27 UTC+05:30", "text": "Sl 4328_27", "type": "SL_UPDATE", "sl": 4327.0},
    {"id": 7114, "date": "16.09.2026 13:30:56 UTC+05:30", "text": "Ok price reversed", "type": "PROVIDER_OUTCOME", "outcome": "PRICE_REVERSED"},
    {"id": 7115, "date": "16.09.2026 13:31:20 UTC+05:30", "text": "We will take another trade after some time", "type": "COMMENTARY"},

    # --- Sequence 2: September 16, 2026 (Trade 2 - Massive Winner) ---
    {"id": 7116, "date": "16.09.2026 14:41:52 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 7117, "date": "16.09.2026 14:41:56 UTC+05:30", "text": "Planning for buy", "type": "PLANNING"},
    {"id": 7118, "date": "16.09.2026 14:42:56 UTC+05:30", "text": "Buy gold @ 4332_29", "type": "SIGNAL_ENTRY", "side": "BUY", "symbol": "XAUUSD", "low": 4329.0, "high": 4332.0},
    {"id": 7120, "date": "16.09.2026 14:43:42 UTC+05:30", "text": "Sl 4323_22", "type": "SL_UPDATE", "sl": 4322.0},
    {"id": 7123, "date": "16.09.2026 15:01:30 UTC+05:30", "text": "Momentum bahut tej hai", "type": "COMMENTARY"},
    {"id": 7125, "date": "16.09.2026 15:02:50 UTC+05:30", "text": "30 pips ✅", "type": "PROVIDER_OUTCOME", "pips": 30},
    {"id": 7126, "date": "16.09.2026 15:03:37 UTC+05:30", "text": "40 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 40},
    {"id": 7128, "date": "16.09.2026 15:03:52 UTC+05:30", "text": "Risk free", "type": "TRADE_MANAGEMENT", "action": "RISK_FREE"},
    {"id": 7131, "date": "16.09.2026 15:11:47 UTC+05:30", "text": "Market fluctuat kar raha hai booking karte chalna dosto", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},
    {"id": 7132, "date": "16.09.2026 15:13:59 UTC+05:30", "text": "50 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 50},
    {"id": 7135, "date": "16.09.2026 15:15:19 UTC+05:30", "text": "60 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 60},
    {"id": 7139, "date": "16.09.2026 15:29:02 UTC+05:30", "text": "70 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 70},
    {"id": 7142, "date": "16.09.2026 15:35:33 UTC+05:30", "text": "100 pips ✅🔥", "type": "PROVIDER_OUTCOME", "pips": 100},
    {"id": 7144, "date": "16.09.2026 15:37:25 UTC+05:30", "text": "Booking karte chalna dosto", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},
    {"id": 7146, "date": "16.09.2026 15:41:54 UTC+05:30", "text": "150 pips ✅🔥🔥🚀", "type": "PROVIDER_OUTCOME", "pips": 150},
    {"id": 7148, "date": "16.09.2026 15:59:10 UTC+05:30", "text": "160 Pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 160},
    {"id": 7150, "date": "16.09.2026 17:10:47 UTC+05:30", "text": "200 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 200},

    # --- Sequence 3: September 17, 2026 (Sell Gold) ---
    {"id": 7171, "date": "17.09.2026 13:42:49 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 7172, "date": "17.09.2026 13:43:01 UTC+05:30", "text": "Planning for sell", "type": "PLANNING"},
    {"id": 7173, "date": "17.09.2026 13:45:33 UTC+05:30", "text": "Sell gold @ 4319_22", "type": "SIGNAL_ENTRY", "side": "SELL", "symbol": "XAUUSD", "low": 4319.0, "high": 4322.0},
    {"id": 7174, "date": "17.09.2026 13:46:59 UTC+05:30", "text": "SL 4328", "type": "SL_UPDATE", "sl": 4328.0},
    {"id": 7177, "date": "17.09.2026 13:49:46 UTC+05:30", "text": "50 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 50},
    {"id": 7178, "date": "17.09.2026 13:49:47 UTC+05:30", "text": "Risk free", "type": "TRADE_MANAGEMENT", "action": "RISK_FREE"},
    {"id": 7181, "date": "17.09.2026 13:53:00 UTC+05:30", "text": "60 pips ✅🔥", "type": "PROVIDER_OUTCOME", "pips": 60},
    {"id": 7183, "date": "17.09.2026 13:54:32 UTC+05:30", "text": "70 pips ✅🔥", "type": "PROVIDER_OUTCOME", "pips": 70},
    {"id": 7184, "date": "17.09.2026 14:04:22 UTC+05:30", "text": "90 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 90},
    {"id": 7185, "date": "17.09.2026 14:04:40 UTC+05:30", "text": "Booking karte chalna dosto", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},
    {"id": 7187, "date": "17.09.2026 14:17:00 UTC+05:30", "text": "110 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 110},

    # --- Sequence 4: September 17, 2026 (Night Averaging Sequence) ---
    {"id": 7189, "date": "17.09.2026 21:40:01 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 7190, "date": "17.09.2026 21:40:43 UTC+05:30", "text": "Planning for buy", "type": "PLANNING"},
    {"id": 7191, "date": "17.09.2026 21:41:34 UTC+05:30", "text": "Buy gold @4368_65", "type": "SIGNAL_ENTRY", "side": "BUY", "symbol": "XAUUSD", "low": 4365.0, "high": 4368.0},
    {"id": 7192, "date": "17.09.2026 21:42:29 UTC+05:30", "text": "SL 4359", "type": "SL_UPDATE", "sl": 4359.0},
    {"id": 7194, "date": "17.09.2026 21:56:45 UTC+05:30", "text": "Personally adding few qty.", "type": "ADD_ENTRY"},
    {"id": 7195, "date": "17.09.2026 21:57:00 UTC+05:30", "text": "Aap log add mat karna", "type": "COMMENTARY"},
    {"id": 7196, "date": "17.09.2026 22:04:17 UTC+05:30", "text": "Price reversed", "type": "PROVIDER_OUTCOME", "outcome": "PRICE_REVERSED"},

    # --- Sequence 5: September 21, 2026 (Plan Change -> Buy Gold) ---
    {"id": 7251, "date": "21.09.2026 12:33:07 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 7252, "date": "21.09.2026 12:33:28 UTC+05:30", "text": "Planning for sell", "type": "PLANNING"},
    {"id": 7253, "date": "21.09.2026 12:37:05 UTC+05:30", "text": "Plan change", "type": "PLANNING"},
    {"id": 7254, "date": "21.09.2026 12:37:05 UTC+05:30", "text": "Now planning for buy", "type": "PLANNING"},
    {"id": 7255, "date": "21.09.2026 12:39:31 UTC+05:30", "text": "Buy gold @4350_47", "type": "SIGNAL_ENTRY", "side": "BUY", "symbol": "XAUUSD", "low": 4347.0, "high": 4350.0},
    {"id": 7256, "date": "21.09.2026 12:41:44 UTC+05:30", "text": "SL 4342", "type": "SL_UPDATE", "sl": 4342.0},
    {"id": 7258, "date": "21.09.2026 12:44:31 UTC+05:30", "text": "30 pips ✅🔥", "type": "PROVIDER_OUTCOME", "pips": 30},
    {"id": 7260, "date": "21.09.2026 12:45:22 UTC+05:30", "text": "60 pips ✅🔥", "type": "PROVIDER_OUTCOME", "pips": 60},
    {"id": 7261, "date": "21.09.2026 12:45:26 UTC+05:30", "text": "Risk free", "type": "TRADE_MANAGEMENT", "action": "RISK_FREE"},
    {"id": 7262, "date": "21.09.2026 12:46:38 UTC+05:30", "text": "70 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 70},
    {"id": 7265, "date": "21.09.2026 12:47:42 UTC+05:30", "text": "90 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 90},
    {"id": 7267, "date": "21.09.2026 12:50:47 UTC+05:30", "text": "Booking karte chalna dosto", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},

    # --- Sequence 6: September 21, 2026 (Classic Sell Gold @ 4350_53) ---
    {"id": 7268, "date": "21.09.2026 16:15:48 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 7269, "date": "21.09.2026 16:16:24 UTC+05:30", "text": "Planning for sell", "type": "PLANNING"},
    {"id": 7270, "date": "21.09.2026 16:16:58 UTC+05:30", "text": "Sell gold @ 4350_53", "type": "SIGNAL_ENTRY", "side": "SELL", "symbol": "XAUUSD", "low": 4350.0, "high": 4353.0},
    {"id": 7271, "date": "21.09.2026 16:17:58 UTC+05:30", "text": "SL 4358", "type": "SL_UPDATE", "sl": 4358.0},
    {"id": 7274, "date": "21.09.2026 16:23:23 UTC+05:30", "text": "30 pips ✅🔥", "type": "PROVIDER_OUTCOME", "pips": 30},
    {"id": 7276, "date": "21.09.2026 16:28:51 UTC+05:30", "text": "50 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 50},
    {"id": 7277, "date": "21.09.2026 16:28:57 UTC+05:30", "text": "Risk Free", "type": "TRADE_MANAGEMENT", "action": "RISK_FREE"},
    {"id": 7279, "date": "21.09.2026 16:31:24 UTC+05:30", "text": "80 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 80},
    {"id": 7281, "date": "21.09.2026 16:32:42 UTC+05:30", "text": "Apne apne hisab se booking karte jana dosto", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},

    # --- Sequence 7: August 21, 2026 (Multiple Explicit Targets) ---
    {"id": 6267, "date": "21.08.2026 13:45:05 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 6270, "date": "21.08.2026 14:01:44 UTC+05:30", "text": "Ready for buy", "type": "PLANNING"},
    {"id": 6271, "date": "21.08.2026 14:07:26 UTC+05:30", "text": "Buy gold @ 4581_78", "type": "SIGNAL_ENTRY", "side": "BUY", "symbol": "XAUUSD", "low": 4578.0, "high": 4581.0},
    {"id": 6272, "date": "21.08.2026 14:08:14 UTC+05:30", "text": "SL 4573", "type": "SL_UPDATE", "sl": 4573.0},
    {"id": 6275, "date": "21.08.2026 14:12:27 UTC+05:30", "text": "30 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 30},
    {"id": 6277, "date": "21.08.2026 14:14:42 UTC+05:30", "text": "40 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 40},
    {"id": 6278, "date": "21.08.2026 14:14:44 UTC+05:30", "text": "Risk free", "type": "TRADE_MANAGEMENT", "action": "RISK_FREE"},
    {"id": 6279, "date": "21.08.2026 14:22:13 UTC+05:30", "text": "Target 🎯 \n\n4584 ✅\n\n4589\n\n4594", "type": "TARGET_UPDATE", "targets": [4584.0, 4589.0, 4594.0]},
    {"id": 6281, "date": "21.08.2026 14:30:27 UTC+05:30", "text": "50 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 50},
    {"id": 6283, "date": "21.08.2026 14:37:05 UTC+05:30", "text": "90 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 90},
    {"id": 6284, "date": "21.08.2026 14:37:25 UTC+05:30", "text": "2nd target 🎯✅", "type": "PROVIDER_OUTCOME", "outcome": "TP2_HIT"},
    {"id": 6286, "date": "21.08.2026 14:38:52 UTC+05:30", "text": "120 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 120},
    {"id": 6290, "date": "21.08.2026 14:42:27 UTC+05:30", "text": "170 pips ✅🔥🔥🚀", "type": "PROVIDER_OUTCOME", "pips": 170},
    {"id": 6293, "date": "21.08.2026 14:44:10 UTC+05:30", "text": "200 pips ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 200},
    {"id": 6294, "date": "21.08.2026 14:45:34 UTC+05:30", "text": "Book all", "type": "TRADE_MANAGEMENT", "action": "EXIT"},

    # --- Sequence 8: June 1, 2026 (Trail SL to Cost / C2C) ---
    {"id": 4065, "date": "01.06.2026 13:30:36 UTC+05:30", "text": "hello", "type": "NOISE"},
    {"id": 4066, "date": "01.06.2026 13:31:43 UTC+05:30", "text": "planning for sell side", "type": "PLANNING"},
    {"id": 4068, "date": "01.06.2026 14:13:15 UTC+05:30", "text": "Sell gold @ 4500_01", "type": "SIGNAL_ENTRY", "side": "SELL", "symbol": "XAUUSD", "low": 4500.0, "high": 4501.0},
    {"id": 4069, "date": "01.06.2026 14:13:48 UTC+05:30", "text": "SL 4507_08", "type": "SL_UPDATE", "sl": 4508.0},
    {"id": 4070, "date": "01.06.2026 14:17:25 UTC+05:30", "text": "40 Pips Done ✅", "type": "PROVIDER_OUTCOME", "pips": 40},
    {"id": 4072, "date": "01.06.2026 14:21:24 UTC+05:30", "text": "Target 🎯 \n\n4495\n\n4490\n\n4480", "type": "TARGET_UPDATE", "targets": [4495.0, 4490.0, 4480.0]},
    {"id": 4074, "date": "01.06.2026 14:24:02 UTC+05:30", "text": "Risk free", "type": "TRADE_MANAGEMENT", "action": "RISK_FREE"},
    {"id": 4076, "date": "01.06.2026 14:28:42 UTC+05:30", "text": "Target 🎯 1 ✅", "type": "PROVIDER_OUTCOME", "outcome": "TP1_HIT"},
    {"id": 4077, "date": "01.06.2026 14:28:57 UTC+05:30", "text": "60 pips done ✅👍", "type": "PROVIDER_OUTCOME", "pips": 60},
    {"id": 4080, "date": "01.06.2026 15:02:35 UTC+05:30", "text": "80 pips done ✅", "type": "PROVIDER_OUTCOME", "pips": 80},
    {"id": 4082, "date": "01.06.2026 15:03:43 UTC+05:30", "text": "120 pips done ✅🔥🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 120},
    {"id": 4083, "date": "01.06.2026 15:04:02 UTC+05:30", "text": "Target 🎯 2nd ✅", "type": "PROVIDER_OUTCOME", "outcome": "TP2_HIT"},
    {"id": 4084, "date": "01.06.2026 15:04:31 UTC+05:30", "text": "Book karte chalna dosto", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},

    # --- Sequence 9: June 1, 2026 (Night Trade - C2C) ---
    {"id": 4088, "date": "01.06.2026 23:01:11 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 4091, "date": "01.06.2026 23:11:53 UTC+05:30", "text": "Buy gold @ 4483_82", "type": "SIGNAL_ENTRY", "side": "BUY", "symbol": "XAUUSD", "low": 4482.0, "high": 4483.0},
    {"id": 4092, "date": "01.06.2026 23:14:10 UTC+05:30", "text": "Risk free", "type": "TRADE_MANAGEMENT", "action": "RISK_FREE"},
    {"id": 4095, "date": "01.06.2026 23:15:17 UTC+05:30", "text": "Trail SL to cost", "type": "TRADE_MANAGEMENT", "action": "MOVE_SL_TO_ENTRY"},
    {"id": 4096, "date": "01.06.2026 23:15:18 UTC+05:30", "text": "C2c", "type": "TRADE_MANAGEMENT", "action": "MOVE_SL_TO_ENTRY"},
    {"id": 4097, "date": "01.06.2026 23:15:18 UTC+05:30", "text": "70 pips done ✅🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 70},
    {"id": 4100, "date": "01.06.2026 23:16:16 UTC+05:30", "text": "120 pips done ✅🔥🔥🔥", "type": "PROVIDER_OUTCOME", "pips": 120},
    {"id": 4101, "date": "01.06.2026 23:18:22 UTC+05:30", "text": "Booking karte chalna dosto", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},

    # --- Sequence 10: July 3, 2026 (Complete Single-Message Broadcast with All Fields) ---
    {"id": 4821, "date": "03.07.2026 13:03:28 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 4822, "date": "03.07.2026 13:04:17 UTC+05:30", "text": "Buy Gold @4175_72\n\nSL : 4165\n\nTarget 🎯 \n\n4180\n\n4190\n\n4200", "type": "SIGNAL_ENTRY", "side": "BUY", "symbol": "XAUUSD", "low": 4172.0, "high": 4175.0, "sl": 4165.0, "targets": [4180.0, 4190.0, 4200.0]},
    {"id": 4823, "date": "03.07.2026 13:25:52 UTC+05:30", "text": "60 Pips ✅👑", "type": "PROVIDER_OUTCOME", "pips": 60},
    {"id": 4824, "date": "03.07.2026 13:26:08 UTC+05:30", "text": "profit Booking karte chalna", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},
    {"id": 4827, "date": "03.07.2026 13:37:34 UTC+05:30", "text": "80 Pips ✅👑", "type": "PROVIDER_OUTCOME", "pips": 80},

    # --- Sequence 11: July 13, 2026 (Fast Big Lot Modifier) ---
    {"id": 5041, "date": "13.07.2026 19:19:01 UTC+05:30", "text": "Hello", "type": "NOISE"},
    {"id": 5042, "date": "13.07.2026 19:19:09 UTC+05:30", "text": "Sell Gold", "type": "PLANNING"},
    {"id": 5043, "date": "13.07.2026 19:19:15 UTC+05:30", "text": "Fast Big Lot", "type": "COMMENTARY"},
    {"id": 5044, "date": "13.07.2026 19:19:35 UTC+05:30", "text": "Sell Gold @4055_60", "type": "SIGNAL_ENTRY", "side": "SELL", "symbol": "XAUUSD", "low": 4055.0, "high": 4060.0, "execution_style": "FAST"},
    {"id": 5046, "date": "13.07.2026 19:20:31 UTC+05:30", "text": "50 Pips ✅👑", "type": "PROVIDER_OUTCOME", "pips": 50},
    {"id": 5047, "date": "13.07.2026 19:21:15 UTC+05:30", "text": "Target 🎯 \n\n4048\n\n4040\n\n4030", "type": "TARGET_UPDATE", "targets": [4048.0, 4040.0, 4030.0]},
    {"id": 5048, "date": "13.07.2026 19:21:32 UTC+05:30", "text": "SL : 4065", "type": "SL_UPDATE", "sl": 4065.0},
    {"id": 5049, "date": "13.07.2026 19:21:54 UTC+05:30", "text": "4046 ✅👑", "type": "PROVIDER_OUTCOME", "outcome": "TP1_HIT"},
    {"id": 5053, "date": "13.07.2026 19:22:13 UTC+05:30", "text": "4042 done ✅👑🫡", "type": "PROVIDER_OUTCOME", "outcome": "TP2_HIT"},
    {"id": 5054, "date": "13.07.2026 19:22:54 UTC+05:30", "text": "Booking karte chalna", "type": "TRADE_MANAGEMENT", "action": "BOOK_PROFIT"},

    # --- Promotional & Noise Samples ---
    {"id": 7107, "date": "16.09.2026 09:56:28 UTC+05:30", "text": "https://www.youtube.com/live/LS8mMctzFZ4?si=PqrU3BQ7d5OHH74e", "type": "PROMOTIONAL"},
    {"id": 7108, "date": "16.09.2026 09:56:29 UTC+05:30", "text": "Join LiveStream 👑💵💵", "type": "PROMOTIONAL"},
    {"id": 7248, "date": "21.09.2026 10:07:05 UTC+05:30", "text": "https://www.youtube.com/live/QexaB3PizXY?si=x2hkreqtcX2McJxU", "type": "PROMOTIONAL"},
    {"id": 7250, "date": "21.09.2026 11:18:39 UTC+05:30", "text": "Dosto Jitne Log Vip me hai Bo sirf Vip me rahege Challenge Group me nhi milega access So don't dm about challenge I will share that trade in Vip Group Only", "type": "COMMENTARY"},
    {"id": 6990, "date": "13.09.2026 13:26:50 UTC+05:30", "text": "https://shubhamuni-br9dl2as.manus.space", "type": "PROMOTIONAL"},
    {"id": 6991, "date": "13.09.2026 13:27:43 UTC+05:30", "text": "Dosto website open karke indicator bale section me jao Baha SHUBHAM03 daalke code ko copy karna hai Tradingview me paste kardo", "type": "COMMENTARY"},
    {"id": 4518, "date": "16.06.2026 14:22:47 UTC+05:30", "text": "🚨 Important Update for All Members To stay connected with us without interruption, we recommend joining our WhatsApp Channel as a backup.", "type": "PROMOTIONAL"}
]


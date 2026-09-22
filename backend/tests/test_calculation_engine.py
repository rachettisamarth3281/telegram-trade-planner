import pytest
from app.services.signal_parser import SignalParser
from app.services.signal_normalizer import SignalNormalizer
from app.services.calculation_engine import CalculationEngine

def test_prompt_exact_example_risk_and_r_multiples():
    text = "Sell gold @ 4350.53\nSL 4358"
    parsed = SignalParser.parse(text)
    norm = SignalNormalizer.normalize(parsed)

    metrics = CalculationEngine.calculate(
        signal=norm,
        effective_sl=norm.provider_sl,
        account_balance=10000.0,
        risk_percent=1.0
    )

    # Risk = 4358.00 - 4350.53 = 7.47
    assert metrics.risk_price_diff == 7.47

    # 1R = 4343.06
    assert metrics.r1_target == 4343.06

    # 1.5R = 4339.32 (or 4339.33 depending on rounding: 4350.53 - 11.205 = 4339.325)
    assert metrics.r1_5_target in [4339.32, 4339.33]

    # 2R = 4335.59
    assert metrics.r2_target == 4335.59

    # 3R = 4328.12
    assert metrics.r3_target == 4328.12

def test_buy_risk_and_r_multiples():
    text = "BUY EURUSD @ 1.08500 SL 1.08000 TP1 1.09500"
    parsed = SignalParser.parse(text)
    norm = SignalNormalizer.normalize(parsed)

    metrics = CalculationEngine.calculate(
        signal=norm,
        effective_sl=norm.provider_sl,
        account_balance=10000.0,
        risk_percent=1.0
    )

    # Risk = 1.08500 - 1.08000 = 0.00500 (50 pips)
    assert metrics.risk_price_diff == 0.00500
    assert metrics.risk_pips == 50.0

    # 1R = 1.08500 + 0.00500 = 1.09000
    assert metrics.r1_target == 1.09000
    # 2R = 1.08500 + 0.01000 = 1.09500
    assert metrics.r2_target == 1.09500
    # 3R = 1.08500 + 0.01500 = 1.10000
    assert metrics.r3_target == 1.10000

    # TP1 RRR = (1.09500 - 1.08500) / 0.00500 = 2.0R
    assert metrics.provider_tp_rrrs.get("TP1") == 2.0


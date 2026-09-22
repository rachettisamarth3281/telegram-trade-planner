import pytest
from decimal import Decimal
from app.risk import (
    RiskEngine,
    RiskEngineConfig,
    RiskCalculationInput,
    RiskCalculationResult,
    Side,
    TPSource,
    SLSource,
    RiskValidationStatus,
    RejectionReason,
)

def test_prompt_benchmark_sell_gold_exact():
    """
    Test exact prompt benchmark scenario:
    SELL
    Entry = 4350.53
    SL = 4358
    Expected:
    risk = 7.47
    1R = 4343.06
    1.5R = 4339.325
    2R = 4335.59
    3R = 4328.12
    """
    config = RiskEngineConfig(
        r_multiples=[Decimal("1.0"), Decimal("1.5"), Decimal("2.0"), Decimal("3.0")],
        default_tp_r=Decimal("2.0"),
        tick_size=None,
        decimal_places=None,  # exact mode
    )

    result = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="SELL",
        entry_price="4350.53",
        stop_loss="4358",
        config=config,
    )

    assert result.is_valid is True
    assert result.status == RiskValidationStatus.VALID
    assert result.side == "SELL"
    assert result.entry_price == Decimal("4350.53")
    assert result.effective_sl == Decimal("4358")
    assert result.sl_source == SLSource.PROVIDER

    # Exact Risk calculation: 4358 - 4350.53 = 7.47
    assert result.risk_distance == Decimal("7.47")

    # Exact R-multiple targets
    assert result.tp_1R == Decimal("4343.06")
    assert result.tp_1_5R == Decimal("4339.325")
    assert result.tp_2R == Decimal("4335.59")
    assert result.tp_3R == Decimal("4328.12")
    assert result.r_targets["1R"] == Decimal("4343.06")
    assert result.r_targets["1.5R"] == Decimal("4339.325")
    assert result.r_targets["2R"] == Decimal("4335.59")
    assert result.r_targets["3R"] == Decimal("4328.12")

    # TP priority fallback: Calculated 2R
    assert result.tp_source == TPSource.CALCULATED
    assert result.effective_tp == Decimal("4335.59")
    assert result.reward_distance == Decimal("14.94")
    assert result.risk_reward_ratio == Decimal("2.00")

def test_prompt_benchmark_sell_gold_with_2_decimal_rounding():
    """
    Verify rounding behavior when 2 decimal places are configured.
    4339.325 rounds to 4339.33 under ROUND_HALF_UP.
    """
    config = RiskEngineConfig(
        r_multiples=[Decimal("1.0"), Decimal("1.5"), Decimal("2.0"), Decimal("3.0")],
        decimal_places=2,
    )

    result = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="SELL",
        entry_price="4350.53",
        stop_loss="4358",
        config=config,
    )

    assert result.risk_distance == Decimal("7.47")
    assert result.tp_1R == Decimal("4343.06")
    assert result.tp_1_5R == Decimal("4339.33")
    assert result.tp_2R == Decimal("4335.59")
    assert result.tp_3R == Decimal("4328.12")

def test_buy_calculation_with_provider_tp():
    """
    Test BUY calculation with provider TP and RRR calculation.
    BUY: Entry = 1.08500, SL = 1.08000, TP = 1.09500
    Risk = 0.00500
    Reward = 0.01000
    RRR = 2.00
    """
    config = RiskEngineConfig(
        min_rr=Decimal("1.5"),
        default_tp_r=Decimal("2.0"),
    )

    result = RiskEngine.calculate_from_values(
        symbol="EURUSD",
        side="BUY",
        entry_price=1.08500,
        stop_loss=1.08000,
        provider_take_profit=1.09500,
        config=config,
    )

    assert result.is_valid is True
    assert result.status == RiskValidationStatus.VALID
    assert result.side == "BUY"
    assert result.risk_distance == Decimal("0.00500")
    assert result.tp_source == TPSource.PROVIDER
    assert result.effective_tp == Decimal("1.09500")
    assert result.reward_distance == Decimal("0.01000")
    assert result.risk_reward_ratio == Decimal("2.00")
    assert result.tp_1R == Decimal("1.09000")
    assert result.tp_1_5R == Decimal("1.09250")
    assert result.tp_2R == Decimal("1.09500")
    assert result.tp_3R == Decimal("1.10000")

def test_buy_invalid_sl_geometry():
    """
    BUY where SL >= entry:
    Must mark INVALID and report rejection reasons.
    """
    # SL > Entry
    res1 = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4355.00",
    )
    assert res1.is_valid is False
    assert res1.status == RiskValidationStatus.INVALID
    assert RejectionReason.SL_ABOVE_BUY_ENTRY.value in res1.rejection_reasons

    # SL == Entry (zero risk)
    res2 = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4350.00",
    )
    assert res2.is_valid is False
    assert res2.status == RiskValidationStatus.INVALID
    assert RejectionReason.ZERO_OR_NEGATIVE_RISK.value in res2.rejection_reasons

def test_sell_invalid_sl_geometry():
    """
    SELL where SL <= entry:
    Must mark INVALID and report rejection reasons.
    """
    # SL < Entry
    res1 = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="SELL",
        entry_price="4350.00",
        stop_loss="4345.00",
    )
    assert res1.is_valid is False
    assert res1.status == RiskValidationStatus.INVALID
    assert RejectionReason.SL_BELOW_SELL_ENTRY.value in res1.rejection_reasons

    # SL == Entry
    res2 = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="SELL",
        entry_price="4350.00",
        stop_loss="4350.00",
    )
    assert res2.is_valid is False
    assert res2.status == RiskValidationStatus.INVALID
    assert RejectionReason.ZERO_OR_NEGATIVE_RISK.value in res2.rejection_reasons

def test_invalid_prices_and_sides():
    """
    Test zero or negative prices and invalid side strings.
    """
    # Zero entry price
    res_zero = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="0",
        stop_loss="4300",
    )
    assert res_zero.is_valid is False
    assert RejectionReason.MISSING_ENTRY_PRICE.value in res_zero.rejection_reasons

    # Negative SL
    res_neg_sl = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350",
        stop_loss="-10",
    )
    assert res_neg_sl.is_valid is False

    # Invalid side
    res_side = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="HOLD",
        entry_price="4350",
        stop_loss="4340",
    )
    assert res_side.is_valid is False
    assert RejectionReason.INVALID_SIDE.value in res_side.rejection_reasons

def test_zero_assumption_missing_sl():
    """
    If SL is missing:
    - Never invent or fabricate an SL.
    - Status must be PARTIAL.
    - sl_source must be NONE.
    """
    result = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss=None,
    )

    assert result.is_valid is False
    assert result.status == RiskValidationStatus.PARTIAL
    assert result.effective_sl is None
    assert result.sl_source == SLSource.NONE
    assert result.risk_distance is None
    assert RejectionReason.MISSING_STOP_LOSS.value in result.rejection_reasons

def test_sl_priority_provider_over_strategy():
    """
    SL Priority:
    1. Provider SL takes precedence even when strategy SL is provided.
    2. Strategy SL is used ONLY when provider SL is missing AND allow_strategy_sl is True.
    """
    config_enabled = RiskEngineConfig(allow_strategy_sl=True)

    # Provider SL present -> uses PROVIDER
    res1 = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4340.00",
        strategy_stop_loss="4330.00",
        config=config_enabled,
    )
    assert res1.effective_sl == Decimal("4340.00")
    assert res1.sl_source == SLSource.PROVIDER

    # Provider SL missing -> uses STRATEGY
    res2 = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss=None,
        strategy_stop_loss="4330.00",
        config=config_enabled,
    )
    assert res2.effective_sl == Decimal("4330.00")
    assert res2.sl_source == SLSource.STRATEGY

    # Strategy SL provided but allow_strategy_sl is False -> PARTIAL / NONE
    config_disabled = RiskEngineConfig(allow_strategy_sl=False)
    res3 = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss=None,
        strategy_stop_loss="4330.00",
        config=config_disabled,
    )
    assert res3.effective_sl is None
    assert res3.sl_source == SLSource.NONE
    assert res3.status == RiskValidationStatus.PARTIAL

def test_tp_priority():
    """
    TP Priority:
    1. Provider TP
    2. Configured R-multiple TP
    3. No TP
    """
    # 1. Provider TP present
    res_provider = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4340.00",
        provider_take_profit="4370.00",
        config=RiskEngineConfig(default_tp_r=Decimal("2.0")),
    )
    assert res_provider.tp_source == TPSource.PROVIDER
    assert res_provider.effective_tp == Decimal("4370.00")

    # 2. Configured R-multiple fallback
    res_calc = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4340.00",
        provider_take_profit=None,
        config=RiskEngineConfig(default_tp_r=Decimal("3.0")),
    )
    assert res_calc.tp_source == TPSource.CALCULATED
    assert res_calc.effective_tp == Decimal("4380.00")  # 4350 + (10 * 3)

    # 3. No TP
    res_none = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4340.00",
        provider_take_profit=None,
        config=RiskEngineConfig(default_tp_r=None),
    )
    assert res_none.tp_source == TPSource.NONE
    assert res_none.effective_tp is None

def test_low_rr_flagging_preserves_signal():
    """
    If provider TP produces RR < MIN_RR:
    - Mark status LOW_RR
    - Append warning flag
    - Keep is_valid = True (Preserve signal for analytics)
    """
    config = RiskEngineConfig(min_rr=Decimal("1.5"))

    # Risk = 10 (4350 - 4340). TP = 4360 (Reward = 10). RRR = 1.0 < 1.5
    result = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4340.00",
        provider_take_profit="4360.00",
        config=config,
    )

    assert result.is_valid is True
    assert result.status == RiskValidationStatus.LOW_RR
    assert result.risk_reward_ratio == Decimal("1.00")
    assert any("LOW_RR" in flag for flag in result.warning_flags)

def test_tp_wrong_side_of_entry():
    """
    Test rejection when TP is on wrong side of entry:
    - BUY with TP <= entry
    - SELL with TP >= entry
    """
    # BUY with TP below entry
    res_buy = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="4350.00",
        stop_loss="4340.00",
        provider_take_profit="4330.00",
    )
    assert any(RejectionReason.TP_BELOW_BUY_ENTRY.value in r for r in res_buy.rejection_reasons)

    # SELL with TP above entry
    res_sell = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="SELL",
        entry_price="4350.00",
        stop_loss="4360.00",
        provider_take_profit="4370.00",
    )
    assert any(RejectionReason.TP_ABOVE_SELL_ENTRY.value in r for r in res_sell.rejection_reasons)

def test_multiple_provider_tps_metrics():
    """
    Test extraction of multiple provider TPs with individual RRR and LOW_RR checks.
    """
    config = RiskEngineConfig(min_rr=Decimal("1.5"))
    # SELL @ 4350, SL 4360 (Risk = 10)
    # TP1 = 4345 (Reward 5, RRR 0.5 -> LOW_RR)
    # TP2 = 4335 (Reward 15, RRR 1.5 -> Valid)
    # TP3 = 4320 (Reward 30, RRR 3.0 -> Valid)
    result = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="SELL",
        entry_price="4350.00",
        stop_loss="4360.00",
        provider_take_profits=["4345.00", "4335.00", "4320.00"],
        config=config,
    )

    assert len(result.provider_tps_metrics) == 3
    tp1 = result.provider_tps_metrics[0]
    assert tp1.tp_price == Decimal("4345.00")
    assert tp1.reward_distance == Decimal("5.00")
    assert tp1.risk_reward_ratio == Decimal("0.50")
    assert tp1.is_low_rr is True

    tp2 = result.provider_tps_metrics[1]
    assert tp2.tp_price == Decimal("4335.00")
    assert tp2.reward_distance == Decimal("15.00")
    assert tp2.risk_reward_ratio == Decimal("1.50")
    assert tp2.is_low_rr is False

    tp3 = result.provider_tps_metrics[2]
    assert tp3.tp_price == Decimal("4320.00")
    assert tp3.reward_distance == Decimal("30.00")
    assert tp3.risk_reward_ratio == Decimal("3.00")
    assert tp3.is_low_rr is False

def test_tick_size_rounding():
    """
    Test tick_size quantization behavior.
    """
def test_forex_5_digit_precision():
    """
    Test Forex pair with 5 decimal places precision and multiple R targets.
    BUY EURUSD @ 1.08250, SL 1.08050 (Risk = 0.00200 = 20 pips)
    1R = 1.08450
    1.5R = 1.08550
    2R = 1.08650
    3R = 1.08850
    """
    config = RiskEngineConfig(decimal_places=5)
    result = RiskEngine.calculate_from_values(
        symbol="EURUSD",
        side="BUY",
        entry_price="1.08250",
        stop_loss="1.08050",
        config=config,
    )

    assert result.is_valid is True
    assert result.risk_distance == Decimal("0.00200")
    assert result.tp_1R == Decimal("1.08450")
    assert result.tp_1_5R == Decimal("1.08550")
    assert result.tp_2R == Decimal("1.08650")
    assert result.tp_3R == Decimal("1.08850")

def test_result_to_dict_serialization():
    """
    Ensure to_dict returns clean JSON-serializable float and string values.
    """
    result = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="SELL",
        entry_price="4350.53",
        stop_loss="4358.00",
        provider_take_profit="4335.59",
    )
    d = result.to_dict()
    assert d["is_valid"] is True
    assert d["status"] == "VALID"
    assert d["entry_price"] == 4350.53
    assert d["effective_sl"] == 4358.0
    assert d["risk_distance"] == 7.47
    assert d["effective_tp"] == 4335.59
    assert d["tp_source"] == "PROVIDER"
    assert d["risk_reward_ratio"] == 2.0
    assert isinstance(d["r_targets"], dict)
    assert d["r_targets"]["1R"] == 4343.06
    assert d["r_targets"]["2R"] == 4335.59

def test_non_numeric_and_null_inputs():
    """
    Ensure non-numeric strings or None values do not crash and are rejected cleanly.
    """
    result = RiskEngine.calculate_from_values(
        symbol="XAUUSD",
        side="BUY",
        entry_price="invalid_price",
        stop_loss="4300",
    )
    assert result.is_valid is False
    assert result.status == RiskValidationStatus.INVALID
    assert RejectionReason.MISSING_ENTRY_PRICE.value in result.rejection_reasons


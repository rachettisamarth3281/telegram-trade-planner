import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.database.models import Signal, TradePlan, ValueProvenance, TradePlanStatus
from app.trade_plan.service import TradePlanService
from app.paper_trading.position_sizing import PositionSizingService
from app.risk.guards import RiskGuardsService
from app.signals.correlator import SignalCorrelator
from app.signals.models import PipelineProcessRequest
from app.config import settings

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_telegram_sl_and_tp_preserved_with_telegram_provenance(db_session: AsyncSession):
    """RULE 1 & RULE 2: Preserves Telegram SL and TP with TELEGRAM provenance."""
    orig_bal = settings.CURRENT_BALANCE
    orig_dbal = settings.DAILY_STARTING_BALANCE
    settings.CURRENT_BALANCE = 500000.0  # ₹5,00,000 -> ₹5,000 risk (~$58.8 USD) -> 0.05 lot on 10 pt risk
    settings.DAILY_STARTING_BALANCE = 500000.0
    try:
        signal = Signal(
            raw_message="BUY XAUUSD @ 4350.00 SL 4340.00 TP 4370.00",
            symbol="XAUUSD",
            side="BUY",
            entry_price=4350.00,
            stop_loss=4340.00,
            take_profit=4370.00,
            message_type="SIGNAL_ENTRY",
            status="VALID"
        )
        db_session.add(signal)
        await db_session.commit()

        service = TradePlanService()
        plan = await service.generate_or_update_plan(db_session, signal)

        assert plan.plan_status == TradePlanStatus.READY.value
        assert plan.entry_price == 4350.00
        assert plan.entry_provenance == ValueProvenance.TELEGRAM.value
        assert plan.stop_loss == 4340.00
        assert plan.sl_provenance == ValueProvenance.TELEGRAM.value
        assert plan.tp1 == 4370.00
        assert plan.tp1_provenance == ValueProvenance.TELEGRAM.value
        assert plan.risk_distance_points == 10.0
        assert plan.calculated_lot_size == 0.05
    finally:
        settings.CURRENT_BALANCE = orig_bal
        settings.DAILY_STARTING_BALANCE = orig_dbal

@pytest.mark.asyncio
async def test_missing_tp_calculates_1r_2r_3r_with_system_calculated_provenance(db_session: AsyncSession):
    """RULE 3: Missing TP generates TP1 (1R), TP2 (2R), TP3 (3R) labelled SYSTEM_CALCULATED."""
    orig_bal = settings.CURRENT_BALANCE
    orig_dbal = settings.DAILY_STARTING_BALANCE
    settings.CURRENT_BALANCE = 500000.0
    settings.DAILY_STARTING_BALANCE = 500000.0
    try:
        # Sell Gold Entry 4350, SL 4358 -> Risk = 8 points
        signal = Signal(
            raw_message="Sell gold @ 4350 SL 4358",
            symbol="XAUUSD",
            side="SELL",
            entry_price=4350.00,
            stop_loss=4358.00,
            take_profit=None,
            message_type="SIGNAL_ENTRY",
            status="VALID"
        )
        db_session.add(signal)
        await db_session.commit()

        service = TradePlanService()
        plan = await service.generate_or_update_plan(db_session, signal)

        assert plan.plan_status == TradePlanStatus.READY.value
        assert plan.entry_price == 4350.00
        assert plan.stop_loss == 4358.00
        assert plan.risk_distance_points == 8.0

        # SELL: TP = Entry - (Risk * R)
        # 1R = 4350 - 8 = 4342
        # 2R = 4350 - 16 = 4334
        # 3R = 4350 - 24 = 4326
        assert plan.tp1 == 4342.00
        assert plan.tp1_provenance == ValueProvenance.SYSTEM_CALCULATED.value
        assert plan.tp2 == 4334.00
        assert plan.tp2_provenance == ValueProvenance.SYSTEM_CALCULATED.value
        assert plan.tp3 == 4326.00
        assert plan.tp3_provenance == ValueProvenance.SYSTEM_CALCULATED.value
    finally:
        settings.CURRENT_BALANCE = orig_bal
        settings.DAILY_STARTING_BALANCE = orig_dbal

@pytest.mark.asyncio
async def test_missing_sl_sets_waiting_for_sl_and_zero_volume(db_session: AsyncSession):
    """RULE 4: Missing SL results in WAITING_FOR_SL; never invents SL."""
    signal = Signal(
        raw_message="Buy Gold @ 4350_53 (SL soon)",
        symbol="XAUUSD",
        side="BUY",
        entry_price=4351.50,
        entry_zone_low=4350.00,
        entry_zone_high=4353.00,
        stop_loss=None,
        take_profit=4380.00,
        message_type="SIGNAL_ENTRY",
        status="WAITING_FOR_DETAILS"
    )
    db_session.add(signal)
    await db_session.commit()

    service = TradePlanService()
    plan = await service.generate_or_update_plan(db_session, signal)

    assert plan.plan_status == TradePlanStatus.WAITING_FOR_SL.value
    assert plan.calculated_lot_size == 0.0
    assert plan.stop_loss is None
    assert "Awaiting correlated Telegram Stop Loss" in (plan.guard_rejection_reason or "")

@pytest.mark.asyncio
async def test_missing_sl_and_tp_sets_incomplete(db_session: AsyncSession):
    """RULE 5: Missing both SL and TP results in INCOMPLETE."""
    signal = Signal(
        raw_message="Buy Gold 4350",
        symbol="XAUUSD",
        side="BUY",
        entry_price=4350.00,
        stop_loss=None,
        take_profit=None,
        message_type="SIGNAL_ENTRY",
        status="WAITING_FOR_DETAILS"
    )
    db_session.add(signal)
    await db_session.commit()

    service = TradePlanService()
    plan = await service.generate_or_update_plan(db_session, signal)

    assert plan.plan_status == TradePlanStatus.INCOMPLETE.value
    assert plan.calculated_lot_size == 0.0

def test_position_sizing_floor_rounding_and_risk_limit():
    """Position sizing must strictly floor-quantize (ROUND_DOWN) and never exceed max risk."""
    sizer = PositionSizingService()

    # Balance = 50,000 INR, Risk = 1% -> Max Risk = 500 INR
    # USD_INR = 85.00 -> Max Risk USD = 500 / 85 = 5.88235 USD
    # Risk distance = 8.0 points on XAUUSD (Contract size = 100)
    # Unit risk = 8 * 100 = 800 USD per 1.0 lot
    # Raw lots = 5.88235 / 800 = 0.0073529 lots
    # Floor lots to step 0.01 -> 0.00 lots (Below min volume 0.01)
    res = sizer.calculate_trade_plan_position_size(
        symbol="XAUUSD",
        risk_distance=Decimal("8.0"),
        account_balance_inr=Decimal("50000.0"),
        risk_percent=Decimal("1.0"),
        usd_inr_rate=Decimal("85.00")
    )
    assert res["lot_size"] == 0.0
    assert res["is_viable"] is False
    assert res["rejection_reason"] == "Minimum tradable volume exceeds configured risk."

    # Test with larger balance where lots >= 0.01
    # Balance = 1,000,000 INR, 1% = 10,000 INR -> 10,000 / 85 = 117.647 USD
    # Raw lots = 117.647 / 800 = 0.14705 lots
    # Floor lots = 0.14 lots (never 0.15!)
    res_large = sizer.calculate_trade_plan_position_size(
        symbol="XAUUSD",
        risk_distance=Decimal("8.0"),
        account_balance_inr=Decimal("1000000.0"),
        risk_percent=Decimal("1.0"),
        usd_inr_rate=Decimal("85.00")
    )
    assert res_large["lot_size"] == 0.14
    assert res_large["is_viable"] is True
    # Actual risk INR = 0.14 * 800 * 85 = 9,520 INR <= 10,000 INR target
    assert res_large["monetary_risk_inr"] <= 10000.00
    assert res_large["monetary_risk_inr"] == 9520.00

def test_dynamic_balance_updates_max_risk():
    """Recalculates maximum risk whenever Current Balance changes."""
    sizer = PositionSizingService()

    # Dynamic balance = ₹75,000 -> Max Risk = ₹750
    res = sizer.calculate_trade_plan_position_size(
        symbol="XAUUSD",
        risk_distance=Decimal("2.0"),
        account_balance_inr=Decimal("75000.0"),
        risk_percent=Decimal("1.0"),
        usd_inr_rate=Decimal("85.00")
    )
    assert res["target_risk_inr"] == 750.00

@pytest.mark.asyncio
async def test_manual_override_provenance_preservation(db_session: AsyncSession):
    """User modification sets USER_MODIFIED provenance while leaving original Telegram values untouched."""
    orig_bal = settings.CURRENT_BALANCE
    settings.CURRENT_BALANCE = 500000.0
    try:
        signal = Signal(
            raw_message="BUY XAUUSD @ 4350.00 SL 4342.00 TP 4366.00",
            symbol="XAUUSD",
            side="BUY",
            entry_price=4350.00,
            stop_loss=4342.00,
            take_profit=4366.00,
            message_type="SIGNAL_ENTRY",
            status="VALID"
        )
        db_session.add(signal)
        await db_session.commit()

        service = TradePlanService()
        # 1. Initial Plan from Telegram
        plan = await service.generate_or_update_plan(db_session, signal)
        assert plan.sl_provenance == ValueProvenance.TELEGRAM.value
        assert plan.stop_loss == 4342.00

        # 2. User overrides Stop Loss to 4344.00 and TP2 to 4375.00
        overrides = {
            "stop_loss": 4344.00,
            "tp2": 4375.00
        }
        updated_plan = await service.generate_or_update_plan(db_session, signal, user_overrides=overrides)

        assert updated_plan.stop_loss == 4344.00
        assert updated_plan.sl_provenance == ValueProvenance.USER_MODIFIED.value
        assert updated_plan.tp2 == 4375.00
        assert updated_plan.tp2_provenance == ValueProvenance.USER_MODIFIED.value
        # Entry remains TELEGRAM
        assert updated_plan.entry_provenance == ValueProvenance.TELEGRAM.value

        # Original Telegram values snapshot remains completely unchanged
        assert updated_plan.original_telegram_values["stop_loss"] == 4342.00
        assert updated_plan.original_telegram_values["raw_message"] == "BUY XAUUSD @ 4350.00 SL 4342.00 TP 4366.00"
    finally:
        settings.CURRENT_BALANCE = orig_bal

@pytest.mark.asyncio
async def test_daily_risk_and_open_trades_guards(db_session: AsyncSession):
    """Guards flag NOT_READY when daily risk is exhausted or max open trades reached."""
    # Create 3 already-executed trade plans with small risk (₹100 each -> ₹300 used < ₹1,500 limit)
    for i in range(3):
        sig = Signal(raw_message=f"BUY XAUUSD @ 4350 SL 4340", symbol="XAUUSD", side="BUY", status="VALID")
        db_session.add(sig)
        await db_session.flush()

        tp = TradePlan(
            signal_id=sig.id,
            symbol="XAUUSD",
            side="BUY",
            entry_price=4350.0,
            stop_loss=4340.0,
            calculated_lot_size=0.05,
            monetary_risk_inr=100.0,
            plan_status=TradePlanStatus.MARKED_EXECUTED.value,
            is_manually_executed=True
        )
        db_session.add(tp)
    await db_session.commit()

    # 4th trade plan: Open trade limit (3) should be triggered!
    is_ready, guard_reason, details = await RiskGuardsService.evaluate_guards(
        db=db_session,
        plan_risk_inr=100.0,
        calculated_lot_size=0.05
    )
    assert is_ready is False
    assert "MAX_OPEN_TRADES_REACHED" in guard_reason
    assert details["open_trades_count"] == 3

@pytest.mark.asyncio
async def test_multi_message_correlation_assembles_trade_plan(db_session: AsyncSession):
    """Multi-message correlation assembles entry + separate SL into a complete TradePlan."""
    orig_bal = settings.CURRENT_BALANCE
    orig_dbal = settings.DAILY_STARTING_BALANCE
    settings.CURRENT_BALANCE = 500000.0
    settings.DAILY_STARTING_BALANCE = 500000.0
    try:
        correlator = SignalCorrelator()

        # Message 1: Entry without SL -> WAITING_FOR_SL
        req1 = PipelineProcessRequest(
            raw_text="Sell gold @ 4350_53",
            source_chat_id="VIP_TEST",
            telegram_message_id=101
        )
        res1 = await correlator.correlate_and_process(db_session, req1)
        assert res1.decision_reason.value == "WAITING_FOR_SL"

        # Verify TradePlan in initial INCOMPLETE/WAITING_FOR_SL state
        stmt1 = select(TradePlan).where(TradePlan.signal_id == res1.signal_id)
        plan1 = await db_session.scalar(stmt1)
        assert plan1 is not None
        assert plan1.plan_status in (TradePlanStatus.WAITING_FOR_SL.value, TradePlanStatus.INCOMPLETE.value)
        assert plan1.entry_price == 4351.50
        assert plan1.stop_loss is None

        # Message 2: Separate SL message -> Correlates and updates TradePlan
        req2 = PipelineProcessRequest(
            raw_text="SL 4358",
            source_chat_id="VIP_TEST",
            telegram_message_id=102
        )
        res2 = await correlator.correlate_and_process(db_session, req2)
        assert res2.decision_reason.value == "PAPER_TRADE_CREATED"

        stmt2 = select(TradePlan).where(TradePlan.signal_id == res1.signal_id)
        plan2 = await db_session.scalar(stmt2)
        assert plan2 is not None
        assert plan2.stop_loss == 4358.00
        assert plan2.sl_provenance == ValueProvenance.TELEGRAM.value
        # TP calculated 1R, 2R, 3R
        assert plan2.tp1_provenance == ValueProvenance.SYSTEM_CALCULATED.value
        assert plan2.tp2_provenance == ValueProvenance.SYSTEM_CALCULATED.value
        assert plan2.plan_status == TradePlanStatus.READY.value
    finally:
        settings.CURRENT_BALANCE = orig_bal
        settings.DAILY_STARTING_BALANCE = orig_dbal

def test_entry_zone_shorthand_regression_cases():
    """Regression test for exact entry zone shorthand cases."""
    from app.parser.zone_parser import EntryZoneParser

    # 1. 4350_53 -> 4350.00–4353.00 (ref 4351.50)
    low, high, ref, _ = EntryZoneParser.parse_zone("4350_53")
    assert low == 4350.00
    assert high == 4353.00
    assert ref == 4351.50

    # 2. 4175_72 -> 4172.00–4175.00 (ref 4173.50)
    low, high, ref, _ = EntryZoneParser.parse_zone("4175_72")
    assert low == 4172.00
    assert high == 4175.00
    assert ref == 4173.50

    # 3. 4025_30 -> 4025.00–4030.00 (ref 4027.50)
    low, high, ref, _ = EntryZoneParser.parse_zone("4025_30")
    assert low == 4025.00
    assert high == 4030.00
    assert ref == 4027.50

    # 4. 4401_4398 -> 4398.00–4401.00 (ref 4399.50)
    low, high, ref, _ = EntryZoneParser.parse_zone("4401_4398")
    assert low == 4398.00
    assert high == 4401.00
    assert ref == 4399.50

    # 5. 4597_01 -> 4597.00–4601.00 (ref 4599.00)
    low, high, ref, _ = EntryZoneParser.parse_zone("4597_01")
    assert low == 4597.00
    assert high == 4601.00
    assert ref == 4599.00

@pytest.mark.asyncio
async def test_real_export_example_a_sell_gold(db_session: AsyncSession):
    """
    Example A:
    Sell gold @ 4350_53
    SL 4358

    Expected:
    Entry Zone: 4350–4353
    Reference: 4351.50
    SL: 4358 (Risk distance: 6.50)
    TP1: 4345.00 (SYSTEM CALCULATED)
    TP2: 4338.50 (SYSTEM CALCULATED)
    TP3: 4332.00 (SYSTEM CALCULATED)
    """
    orig_bal = settings.CURRENT_BALANCE
    settings.CURRENT_BALANCE = 500000.0
    try:
        from app.services.signal_parser import SignalParser
        from app.services.signal_normalizer import SignalNormalizer
        parsed = SignalParser.parse("Sell gold @ 4350_53 SL 4358")
        norm = SignalNormalizer.normalize(parsed)

        sig = Signal(
            raw_message="Sell gold @ 4350_53 SL 4358",
            symbol=norm.symbol,
            side=norm.side,
            entry_price=norm.entry_price,
            entry_zone_low=norm.entry_zone_low,
            entry_zone_high=norm.entry_zone_high,
            entry_reference_price=norm.entry_price,
            stop_loss=norm.provider_sl
        )
        db_session.add(sig)
        await db_session.flush()

        svc = TradePlanService()
        plan = await svc.generate_or_update_plan(db_session, sig)

        assert plan.entry_zone_low == 4350.00
        assert plan.entry_zone_high == 4353.00
        assert plan.entry_price == 4351.50
        assert plan.stop_loss == 4358.00
        assert plan.sl_provenance == ValueProvenance.TELEGRAM.value
        assert plan.risk_distance_points == 6.50
        assert plan.tp1 == 4345.00
        assert plan.tp1_provenance == ValueProvenance.SYSTEM_CALCULATED.value
        assert plan.tp2 == 4338.50
        assert plan.tp2_provenance == ValueProvenance.SYSTEM_CALCULATED.value
        assert plan.tp3 == 4332.00
        assert plan.tp3_provenance == ValueProvenance.SYSTEM_CALCULATED.value
    finally:
        settings.CURRENT_BALANCE = orig_bal

@pytest.mark.asyncio
async def test_real_export_example_b_buy_gold(db_session: AsyncSession):
    """
    Example B:
    Buy gold @ 4401_4398
    SL 4393

    Expected zone: 4398–4401, ref 4399.50, SL 4393 (Risk distance: 6.50)
    TP1: 4406.00, TP2: 4412.50, TP3: 4419.00
    """
    from app.services.signal_parser import SignalParser
    from app.services.signal_normalizer import SignalNormalizer
    parsed = SignalParser.parse("Buy gold @ 4401_4398 SL 4393")
    norm = SignalNormalizer.normalize(parsed)

    sig = Signal(
        raw_message="Buy gold @ 4401_4398 SL 4393",
        symbol=norm.symbol,
        side=norm.side,
        entry_price=norm.entry_price,
        entry_zone_low=norm.entry_zone_low,
        entry_zone_high=norm.entry_zone_high,
        entry_reference_price=norm.entry_price,
        stop_loss=norm.provider_sl
    )
    db_session.add(sig)
    await db_session.flush()

    svc = TradePlanService()
    plan = await svc.generate_or_update_plan(db_session, sig)

    assert plan.entry_zone_low == 4398.00
    assert plan.entry_zone_high == 4401.00
    assert plan.entry_price == 4399.50
    assert plan.stop_loss == 4393.00
    assert plan.risk_distance_points == 6.50
    assert plan.tp1 == 4406.00
    assert plan.tp2 == 4412.50
    assert plan.tp3 == 4419.00

@pytest.mark.asyncio
async def test_real_export_example_c_telegram_targets(db_session: AsyncSession):
    """
    Example C:
    Buy Gold @4175_72
    SL 4165
    Target 4180 4190 4200

    Expected:
    Entry: 4172–4175 (Ref 4173.50)
    SL: 4165 (TELEGRAM)
    TP1: 4180 (TELEGRAM)
    TP2: 4190 (TELEGRAM)
    TP3: 4200 (TELEGRAM)
    """
    from app.services.signal_parser import SignalParser
    from app.services.signal_normalizer import SignalNormalizer
    import json

    parsed = SignalParser.parse("Buy Gold @4175_72 SL 4165 Target 4180 4190 4200")
    norm = SignalNormalizer.normalize(parsed)
    targets_json = json.dumps([{"price": p} for p in norm.provider_tps])

    sig = Signal(
        raw_message="Buy Gold @4175_72 SL 4165 Target 4180 4190 4200",
        symbol=norm.symbol,
        side=norm.side,
        entry_price=norm.entry_price,
        entry_zone_low=norm.entry_zone_low,
        entry_zone_high=norm.entry_zone_high,
        entry_reference_price=norm.entry_price,
        stop_loss=norm.provider_sl,
        targets_json=targets_json
    )
    db_session.add(sig)
    await db_session.flush()

    svc = TradePlanService()
    plan = await svc.generate_or_update_plan(db_session, sig)

    assert plan.entry_zone_low == 4172.00
    assert plan.entry_zone_high == 4175.00
    assert plan.entry_price == 4173.50
    assert plan.stop_loss == 4165.00
    assert plan.sl_provenance == ValueProvenance.TELEGRAM.value
    assert plan.tp1 == 4180.00
    assert plan.tp1_provenance == ValueProvenance.TELEGRAM.value
    assert plan.tp2 == 4190.00
    assert plan.tp2_provenance == ValueProvenance.TELEGRAM.value
    assert plan.tp3 == 4200.00
    assert plan.tp3_provenance == ValueProvenance.TELEGRAM.value

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Float, DateTime, Text, BigInteger, JSON, Boolean, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, utc_now

class ValueProvenance(str, Enum):
    TELEGRAM = "TELEGRAM"
    SYSTEM_CALCULATED = "SYSTEM_CALCULATED"
    USER_MODIFIED = "USER_MODIFIED"

class TradePlanStatus(str, Enum):
    RECEIVED = "RECEIVED"
    ANALYZING = "ANALYZING"
    SIGNAL_DETECTED = "SIGNAL_DETECTED"
    WAITING_FOR_SL = "WAITING_FOR_SL"
    READY = "READY"
    INCOMPLETE = "INCOMPLETE"
    NOT_READY = "NOT_READY"
    REJECTED = "REJECTED"
    MARKED_EXECUTED = "MARKED_EXECUTED"

class TradePlan(Base, TimestampMixin):
    """
    TradePlan Model (V1 Primary Product Artifact).
    Represents an analyzed, calculated, risk-guarded trade plan ready for manual execution.
    Preserves value provenance (TELEGRAM, SYSTEM_CALCULATED, USER_MODIFIED) and original Telegram values.
    """
    __tablename__ = "trade_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id: Mapped[str] = mapped_column(String(36), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, index=True)

    # Instrument & Direction
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # BUY, SELL
    order_type: Mapped[str] = mapped_column(String(20), default="MARKET")      # MARKET, LIMIT, ZONE

    # Entry & Zone with Provenance
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_zone_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_provenance: Mapped[str] = mapped_column(String(30), default=ValueProvenance.TELEGRAM.value)

    # Stop Loss with Provenance
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    sl_provenance: Mapped[str] = mapped_column(String(30), default=ValueProvenance.TELEGRAM.value)

    # Multi-Target Take Profits with Provenance
    tp1: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp1_provenance: Mapped[str] = mapped_column(String(30), default=ValueProvenance.SYSTEM_CALCULATED.value)
    tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp2_provenance: Mapped[str] = mapped_column(String(30), default=ValueProvenance.SYSTEM_CALCULATED.value)
    tp3: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3_provenance: Mapped[str] = mapped_column(String(30), default=ValueProvenance.SYSTEM_CALCULATED.value)

    # Position Sizing & Monetary Risk
    calculated_lot_size: Mapped[float] = mapped_column(Float, default=0.0)
    monetary_risk_inr: Mapped[float] = mapped_column(Float, default=0.0)
    monetary_risk_usd: Mapped[float] = mapped_column(Float, default=0.0)
    risk_distance_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward_risk_ratio_tp1: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward_risk_ratio_tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward_risk_ratio_tp3: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status & Guard Flags
    plan_status: Mapped[str] = mapped_column(String(30), default=TradePlanStatus.RECEIVED.value, index=True)
    guard_rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Manual Execution Tracking (No automated order execution)
    is_manually_executed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit & Provenance Snapshots (JSON)
    calculation_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    original_telegram_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    signal: Mapped["Signal"] = relationship("Signal", back_populates="trade_plans")

    __table_args__ = (
        Index("ix_trade_plans_symbol_status", "symbol", "plan_status"),
        Index("ix_trade_plans_created", "created_at"),
    )


import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Text, BigInteger, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, utc_now

class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Telegram metadata & preserved original message
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    source_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    source_chat_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sender_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="MANUAL_INGEST")  # TELEGRAM_USERBOT, MOCK_DEVELOPMENT, MANUAL_INGEST, TEST

    # Original unaltered Telegram message
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)

    # Parsed & normalized signal fields (Populated in Phase 3/4)
    symbol: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)      # e.g., XAUUSD, EURUSD
    side: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)        # BUY, SELL
    order_type: Mapped[str] = mapped_column(String(20), default="MARKET")                 # MARKET, LIMIT, STOP
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_price_upper: Mapped[float | None] = mapped_column(Float, nullable=True)         # for range entries e.g. 4350-4352
    entry_zone_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_reference_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_style: Mapped[str] = mapped_column(String(32), default="STANDARD")          # FAST, IMMEDIATE, ZONE, STANDARD
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profits: Mapped[dict | None] = mapped_column(JSON, nullable=True)                # e.g. {"tp1": 4343.06, "tp2": 4335.59}
    targets_json: Mapped[str | None] = mapped_column(Text, nullable=True)                 # Serialized list of targets
    provider_outcomes_json: Mapped[str | None] = mapped_column(Text, nullable=True)       # Serialized list of provider outcomes
    management_events_json: Mapped[str | None] = mapped_column(Text, nullable=True)       # Serialized list of management events

    # Signal status & validation details
    message_type: Mapped[str] = mapped_column(String(64), default="SIGNAL_ENTRY", index=True)
    parent_signal_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="RECEIVED", index=True)       # RECEIVED, WAITING_FOR_DETAILS, VALID, INVALID, SKIPPED_NO_SL
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Exact timestamps
    telegram_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )

    # Relationships
    paper_trades: Mapped[list["PaperTrade"]] = relationship("PaperTrade", back_populates="signal", cascade="all, delete-orphan")
    trade_plans: Mapped[list["TradePlan"]] = relationship("TradePlan", back_populates="signal", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_signals_source_chat_msg", "source_chat_id", "telegram_message_id"),
        Index("ix_signals_symbol_status", "symbol", "status"),
        Index("ix_signals_received_created", "received_at", "created_at"),
    )

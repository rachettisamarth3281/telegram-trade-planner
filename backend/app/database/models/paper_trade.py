import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, utc_now

class PaperTrade(Base, TimestampMixin):
    __tablename__ = "paper_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id: Mapped[str] = mapped_column(String(36), ForeignKey("signals.id"), index=True, nullable=False)

    symbol: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(20), index=True, nullable=False)          # BUY, SELL
    order_type: Mapped[str] = mapped_column(String(20), default="MARKET")              # MARKET, LIMIT, STOP
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)        # PENDING, OPEN, TP_HIT, SL_HIT, CANCELLED, INVALID, MANUAL_CLOSED

    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    entry_zone_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    trailing_sl: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_size: Mapped[float] = mapped_column(Float, default=1.0)
    risk_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_r_multiple: Mapped[float] = mapped_column(Float, default=2.0)
    is_risk_free_moved: Mapped[bool] = mapped_column(default=False)

    # Execution timestamps
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=True, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Outcome & Financial Results (Market Calculated)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)         # STOP_LOSS, TAKE_PROFIT, MANUAL, CANCELLED, INVALID
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pips: Mapped[float] = mapped_column(Float, default=0.0)
    realized_r: Mapped[float] = mapped_column(Float, default=0.0)

    # Provider Reported Outcome (Stream A)
    provider_claimed_pips: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_claimed_status: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Excursion metrics (MFE / MAE)
    highest_favorable_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    lowest_favorable_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_favorable_r: Mapped[float] = mapped_column(Float, default=0.0)
    max_adverse_r: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    signal: Mapped["Signal"] = relationship("Signal", back_populates="paper_trades")
    events: Mapped[list["TradeEvent"]] = relationship("TradeEvent", back_populates="paper_trade", cascade="all, delete-orphan")

    @property
    def lot_size(self) -> float:
        return self.position_size

    @lot_size.setter
    def lot_size(self, val: float) -> None:
        self.position_size = val

    @property
    def realized_R(self) -> float:
        return self.realized_r

    __table_args__ = (
        Index("ix_paper_trades_symbol_status", "symbol", "status"),
        Index("ix_paper_trades_opened_closed", "opened_at", "closed_at"),
    )

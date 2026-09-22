import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, utc_now

class TradeEvent(Base, TimestampMixin):
    __tablename__ = "trade_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paper_trade_id: Mapped[str] = mapped_column(String(36), ForeignKey("paper_trades.id"), index=True, nullable=False)

    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # ORDER_CREATED, ORDER_OPENED, SL_HIT, TP_HIT, MANUAL_CLOSE, TICK_CHECK
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    paper_trade: Mapped["PaperTrade"] = relationship("PaperTrade", back_populates="events")

    __table_args__ = (
        Index("ix_trade_events_trade_type", "paper_trade_id", "event_type"),
    )

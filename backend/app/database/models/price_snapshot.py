import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, TimestampMixin, utc_now

class PriceSnapshot(Base, TimestampMixin):
    __tablename__ = "price_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    bid_price: Mapped[float] = mapped_column(Float, nullable=False)
    ask_price: Mapped[float] = mapped_column(Float, nullable=False)
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="simulated")

    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )

    __table_args__ = (
        Index("ix_price_snapshots_symbol_time", "symbol", "snapshot_time"),
    )

import uuid
from datetime import datetime
from sqlalchemy import String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, TimestampMixin, utc_now

class SystemEvent(Base, TimestampMixin):
    __tablename__ = "system_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    component: Mapped[str] = mapped_column(String(50), index=True, nullable=False)    # telegram, parser, signals, risk, paper_trading, market_data
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)   # STARTUP, SHUTDOWN, INGESTION_ERROR, VALIDATION_ERROR, EXECUTION_ERROR
    severity: Mapped[str] = mapped_column(String(20), default="INFO", index=True)     # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_system_events_comp_sev", "component", "severity"),
    )

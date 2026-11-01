"""SupplyChain IQ - System-Wide Immutable Audit Event Ledger."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import (
    Base,
    PrimaryKeyMixin,
    utc_now,
)


class AuditEvent(Base, PrimaryKeyMixin):
    """Immutable audit trail logging every state modification across the supply chain platform."""
    __tablename__ = "audit_events"

    entity_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # CREATE, UPDATE, DELETE, APPROVE, REJECT
    performed_by: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    before_state_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_state_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_audit_entity_lookup", "entity_name", "entity_id", "created_at"),
    )


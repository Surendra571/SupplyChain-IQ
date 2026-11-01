"""SupplyChain IQ - Inventory & Inventory Transaction Models."""

from datetime import datetime
from typing import List, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import (
    Base,
    GUID,
    PrimaryKeyMixin,
    TimestampMixin,
    utc_now,
)
from backend.app.models.enums import InventoryTransactionType


class Inventory(Base, PrimaryKeyMixin, TimestampMixin):
    """Current physical and allocated stock snapshot per SKU and Location."""
    __tablename__ = "inventories"

    sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="CASCADE"), index=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="CASCADE"), index=True, nullable=False)
    on_hand_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allocated_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_stock_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("sku_id", "location_id", name="uq_inventory_sku_location"),
        CheckConstraint("on_hand_qty >= 0", name="ck_inventory_on_hand_non_negative"),
        CheckConstraint("allocated_qty >= 0", name="ck_inventory_allocated_non_negative"),
        CheckConstraint("safety_stock_qty >= 0", name="ck_inventory_safety_stock_non_negative"),
        CheckConstraint("reorder_point >= 0", name="ck_inventory_reorder_point_non_negative"),
        Index("ix_inventories_sku_location", "sku_id", "location_id"),
    )

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU", back_populates="inventories")
    location: Mapped["Location"] = relationship("Location", back_populates="inventories")


class InventoryTransaction(Base, PrimaryKeyMixin):
    """Immutable audit ledger of physical inventory movements and adjustments."""
    __tablename__ = "inventory_transactions"

    sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="RESTRICT"), index=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="RESTRICT"), index=True, nullable=False)
    transaction_type: Mapped[InventoryTransactionType] = mapped_column(String(32), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("balance_after >= 0", name="ck_inv_txn_balance_after_non_negative"),
        Index("ix_inv_txns_sku_loc_created", "sku_id", "location_id", "created_at"),
    )

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU")
    location: Mapped["Location"] = relationship("Location")


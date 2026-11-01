"""SupplyChain IQ - Procurement, Inbound Orders, Supplier Capacity & Shipments."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
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
from backend.app.models.enums import PurchaseOrderStatus, ShipmentStatus


class SupplierCapacity(Base, PrimaryKeyMixin, TimestampMixin):
    """Weekly production capacity limits committed by a supplier for a specific SKU."""
    __tablename__ = "supplier_capacities"

    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("suppliers.id", ondelete="CASCADE"), index=True, nullable=False)
    sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="CASCADE"), index=True, nullable=False)
    week_bucket: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    max_capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    committed_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    surge_capacity_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("supplier_id", "sku_id", "week_bucket", name="uq_supplier_capacity_period"),
        CheckConstraint("max_capacity_units >= 0", name="ck_supplier_max_capacity_non_negative"),
        CheckConstraint("committed_units >= 0", name="ck_supplier_committed_non_negative"),
        CheckConstraint("surge_capacity_units >= 0", name="ck_supplier_surge_capacity_non_negative"),
        CheckConstraint("committed_units <= max_capacity_units + surge_capacity_units", name="ck_supplier_committed_within_limit"),
        Index("ix_supp_cap_lookup", "supplier_id", "sku_id", "week_bucket"),
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="capacities")
    sku: Mapped["SKU"] = relationship("SKU")


class PurchaseOrder(Base, PrimaryKeyMixin, TimestampMixin):
    """Inbound Purchase Order Header."""
    __tablename__ = "purchase_orders"

    po_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True, nullable=False)
    status: Mapped[PurchaseOrderStatus] = mapped_column(String(32), default=PurchaseOrderStatus.DRAFT, index=True, nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_po_total_amount_non_negative"),
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="purchase_orders")
    lines: Mapped[List["PurchaseOrderLine"]] = relationship("PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan")
    shipments: Mapped[List["Shipment"]] = relationship("Shipment", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderLine(Base, PrimaryKeyMixin, TimestampMixin):
    """Line item on a purchase order specifying ordered and received quantities."""
    __tablename__ = "purchase_order_lines"

    po_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True, nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="RESTRICT"), index=True, nullable=False)
    destination_location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="RESTRICT"), index=True, nullable=False)
    ordered_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    received_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    promised_delivery_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("po_id", "line_number", name="uq_po_line_number"),
        CheckConstraint("line_number >= 1", name="ck_po_line_number_positive"),
        CheckConstraint("ordered_qty > 0", name="ck_po_line_ordered_qty_positive"),
        CheckConstraint("received_qty >= 0", name="ck_po_line_received_qty_non_negative"),
        CheckConstraint("received_qty <= ordered_qty", name="ck_po_line_received_lte_ordered"),
        CheckConstraint("unit_cost >= 0", name="ck_po_line_unit_cost_non_negative"),
        Index("ix_po_line_sched_receipt", "sku_id", "destination_location_id", "promised_delivery_date"),
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")
    sku: Mapped["SKU"] = relationship("SKU", back_populates="po_lines")
    destination_location: Mapped["Location"] = relationship("Location")


class Shipment(Base, PrimaryKeyMixin, TimestampMixin):
    """In-transit logistics consignment tracking purchase order delivery."""
    __tablename__ = "shipments"

    po_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True, nullable=False)
    carrier_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    status: Mapped[ShipmentStatus] = mapped_column(String(32), default=ShipmentStatus.DISPATCHED, index=True, nullable=False)
    origin_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    destination_location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="RESTRICT"), index=True, nullable=False)
    etd: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("eta >= etd", name="ck_shipment_eta_after_etd"),
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="shipments")
    origin_location: Mapped[Optional["Location"]] = relationship("Location", foreign_keys=[origin_location_id])
    destination_location: Mapped["Location"] = relationship("Location", foreign_keys=[destination_location_id])


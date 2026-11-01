"""SupplyChain IQ - Master Data Models: SKU, Location, Supplier, SupplierSKU, LeadTime."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
    EffectivePeriodMixin,
    GUID,
    PrimaryKeyMixin,
    TimestampMixin,
)
from backend.app.models.enums import LocationType, SKUType, SupplierTier, TransportMode


class SKU(Base, PrimaryKeyMixin, TimestampMixin):
    """Stock Keeping Unit (Finished Good, Subassembly, Raw Material)."""
    __tablename__ = "skus"

    sku_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    sku_type: Mapped[SKUType] = mapped_column(String(32), index=True, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="EA", nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0.000"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    __table_args__ = (
        CheckConstraint("unit_cost >= 0", name="ck_sku_unit_cost_non_negative"),
        CheckConstraint("unit_price >= 0", name="ck_sku_unit_price_non_negative"),
        CheckConstraint("weight_kg >= 0", name="ck_sku_weight_non_negative"),
    )

    # Master data relationships
    supplier_skus: Mapped[List["SupplierSKU"]] = relationship("SupplierSKU", back_populates="sku", cascade="all, delete-orphan")
    inventories: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="sku")
    forecast_demands: Mapped[List["ForecastDemand"]] = relationship("ForecastDemand", back_populates="sku")
    parent_boms: Mapped[List["BOM"]] = relationship("BOM", back_populates="parent_sku")
    bom_components: Mapped[List["BOMComponent"]] = relationship("BOMComponent", back_populates="component_sku")
    production_plans: Mapped[List["ProductionPlan"]] = relationship("ProductionPlan", back_populates="sku")
    po_lines: Mapped[List["PurchaseOrderLine"]] = relationship("PurchaseOrderLine", back_populates="sku")
    shortages: Mapped[List["Shortage"]] = relationship("Shortage", back_populates="sku")


class Location(Base, PrimaryKeyMixin, TimestampMixin):
    """Physical Facility (Plant, DC, Warehouse, Hub, Retail)."""
    __tablename__ = "locations"

    location_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[LocationType] = mapped_column(String(32), index=True, nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    country: Mapped[str] = mapped_column(String(3), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    __table_args__ = (
        CheckConstraint("capacity_units >= 0", name="ck_location_capacity_non_negative"),
    )

    # Relationships
    inventories: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="location")
    forecast_demands: Mapped[List["ForecastDemand"]] = relationship("ForecastDemand", back_populates="location")
    production_plans: Mapped[List["ProductionPlan"]] = relationship("ProductionPlan", back_populates="location")
    shortages: Mapped[List["Shortage"]] = relationship("Shortage", back_populates="location")


class Supplier(Base, PrimaryKeyMixin, TimestampMixin):
    """External Vendor / Supplier."""
    __tablename__ = "suppliers"

    supplier_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[SupplierTier] = mapped_column(String(32), default=SupplierTier.TIER_1, index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(3), index=True, nullable=False)
    payment_terms: Mapped[str] = mapped_column(String(64), default="NET30", nullable=False)
    on_time_delivery_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.9500"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    __table_args__ = (
        CheckConstraint("on_time_delivery_rate >= 0.0 AND on_time_delivery_rate <= 1.0", name="ck_supplier_otd_range"),
    )

    # Relationships
    supplier_skus: Mapped[List["SupplierSKU"]] = relationship("SupplierSKU", back_populates="supplier", cascade="all, delete-orphan")
    capacities: Mapped[List["SupplierCapacity"]] = relationship("SupplierCapacity", back_populates="supplier", cascade="all, delete-orphan")
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="supplier", cascade="all, delete-orphan")


class SupplierSKU(Base, PrimaryKeyMixin, TimestampMixin, EffectivePeriodMixin):
    """Bridge table: Supplier catalog pricing, lead time, and MOQ with temporal validity."""
    __tablename__ = "supplier_skus"

    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("suppliers.id", ondelete="CASCADE"), index=True, nullable=False)
    sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="CASCADE"), index=True, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    moq: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    pack_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("supplier_id", "sku_id", "effective_from", name="uq_supplier_sku_effective"),
        CheckConstraint("unit_price >= 0", name="ck_supplier_sku_price_non_negative"),
        CheckConstraint("moq >= 1", name="ck_supplier_sku_moq_positive"),
        CheckConstraint("pack_size >= 1", name="ck_supplier_sku_pack_size_positive"),
        CheckConstraint("lead_time_days >= 1", name="ck_supplier_sku_lead_time_positive"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_supplier_sku_effective_dates"),
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="supplier_skus")
    sku: Mapped["SKU"] = relationship("SKU", back_populates="supplier_skus")


class LeadTime(Base, PrimaryKeyMixin, TimestampMixin, EffectivePeriodMixin):
    """Transportation transit times and lane costs between locations."""
    __tablename__ = "lead_times"

    origin_location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="CASCADE"), index=True, nullable=False)
    destination_location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="CASCADE"), index=True, nullable=False)
    transport_mode: Mapped[TransportMode] = mapped_column(String(32), default=TransportMode.ROAD, nullable=False)
    transit_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    variability_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)

    __table_args__ = (
        UniqueConstraint("origin_location_id", "destination_location_id", "transport_mode", "effective_from", name="uq_lead_time_lane_effective"),
        CheckConstraint("origin_location_id != destination_location_id", name="ck_lead_time_different_locations"),
        CheckConstraint("transit_days >= 0", name="ck_lead_time_transit_days_non_negative"),
        CheckConstraint("variability_days >= 0", name="ck_lead_time_variability_non_negative"),
        CheckConstraint("cost_per_unit >= 0", name="ck_lead_time_cost_non_negative"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_lead_time_effective_dates"),
    )

    # Relationships
    origin_location: Mapped["Location"] = relationship("Location", foreign_keys=[origin_location_id])
    destination_location: Mapped["Location"] = relationship("Location", foreign_keys=[destination_location_id])

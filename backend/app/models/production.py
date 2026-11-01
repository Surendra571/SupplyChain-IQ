"""SupplyChain IQ - Production, BOM & Component Substitution Models."""

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
from backend.app.models.enums import ProductionPlanStatus


class BOM(Base, PrimaryKeyMixin, TimestampMixin, EffectivePeriodMixin):
    """Bill of Materials Header linking parent Finished Good / Subassembly."""
    __tablename__ = "boms"

    parent_sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="CASCADE"), index=True, nullable=False)
    bom_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("parent_sku_id", "bom_version", name="uq_bom_parent_version"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_bom_effective_dates"),
    )

    # Relationships
    parent_sku: Mapped["SKU"] = relationship("SKU", back_populates="parent_boms")
    components: Mapped[List["BOMComponent"]] = relationship("BOMComponent", back_populates="bom", cascade="all, delete-orphan")


class BOMComponent(Base, PrimaryKeyMixin, TimestampMixin):
    """Component requirement line item within a Bill of Materials."""
    __tablename__ = "bom_components"

    bom_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("boms.id", ondelete="CASCADE"), index=True, nullable=False)
    component_sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="RESTRICT"), index=True, nullable=False)
    quantity_per_parent: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    scrap_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.0000"), nullable=False)
    lead_time_offset_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("bom_id", "component_sku_id", name="uq_bom_component_entry"),
        CheckConstraint("quantity_per_parent > 0", name="ck_bom_qty_positive"),
        CheckConstraint("scrap_percentage >= 0 AND scrap_percentage < 1", name="ck_bom_scrap_percentage_valid"),
        CheckConstraint("lead_time_offset_days >= 0", name="ck_bom_lead_time_offset_non_negative"),
    )

    # Relationships
    bom: Mapped["BOM"] = relationship("BOM", back_populates="components")
    component_sku: Mapped["SKU"] = relationship("SKU", back_populates="bom_components")


class SubstituteSKU(Base, PrimaryKeyMixin, TimestampMixin, EffectivePeriodMixin):
    """Component interchangeability and substitution rules."""
    __tablename__ = "substitute_skus"

    primary_sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="CASCADE"), index=True, nullable=False)
    substitute_sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="CASCADE"), index=True, nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("1.0000"), nullable=False)
    preference_rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("primary_sku_id", "substitute_sku_id", "effective_from", name="uq_substitute_sku_effective"),
        CheckConstraint("primary_sku_id != substitute_sku_id", name="ck_substitute_different_skus"),
        CheckConstraint("conversion_factor > 0", name="ck_substitute_conversion_positive"),
        CheckConstraint("preference_rank >= 1", name="ck_substitute_preference_positive"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_substitute_effective_dates"),
    )

    # Relationships
    primary_sku: Mapped["SKU"] = relationship("SKU", foreign_keys=[primary_sku_id])
    substitute_sku: Mapped["SKU"] = relationship("SKU", foreign_keys=[substitute_sku_id])


class ProductionPlan(Base, PrimaryKeyMixin, TimestampMixin):
    """Scheduled manufacturing order / production batch in the Master Production Schedule."""
    __tablename__ = "production_plans"

    sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="RESTRICT"), index=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="RESTRICT"), index=True, nullable=False)
    week_bucket: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    planned_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ProductionPlanStatus] = mapped_column(String(32), default=ProductionPlanStatus.PLANNED, index=True, nullable=False)
    work_center_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    __table_args__ = (
        CheckConstraint("planned_quantity >= 0", name="ck_production_planned_qty_non_negative"),
        Index("ix_prod_plan_sku_loc_week", "sku_id", "location_id", "week_bucket"),
    )

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU", back_populates="production_plans")
    location: Mapped["Location"] = relationship("Location", back_populates="production_plans")


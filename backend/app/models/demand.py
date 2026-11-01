"""SupplyChain IQ - Demand Forecasting Models."""

from typing import Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import (
    Base,
    GUID,
    PrimaryKeyMixin,
    TimestampMixin,
)


class ForecastDemand(Base, PrimaryKeyMixin, TimestampMixin):
    """Weekly time-bucketed projected demand per SKU and stocking Location."""
    __tablename__ = "forecast_demands"

    sku_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("skus.id", ondelete="CASCADE"), index=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("locations.id", ondelete="CASCADE"), index=True, nullable=False)
    week_bucket: Mapped[str] = mapped_column(String(16), index=True, nullable=False)  # e.g., '2026W01'
    forecast_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_p50: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_p90: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="v1.0", index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("sku_id", "location_id", "week_bucket", "version", name="uq_forecast_demand_point"),
        CheckConstraint("forecast_qty >= 0", name="ck_forecast_qty_non_negative"),
        CheckConstraint("confidence_p50 >= 0", name="ck_forecast_p50_non_negative"),
        CheckConstraint("confidence_p90 >= confidence_p50", name="ck_forecast_confidence_interval"),
        Index("ix_forecast_sku_loc_week", "sku_id", "location_id", "week_bucket"),
    )

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU", back_populates="forecast_demands")
    location: Mapped["Location"] = relationship("Location", back_populates="forecast_demands")


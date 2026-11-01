"""SupplyChain IQ - Pydantic Schemas for Demand Forecasting."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ForecastDemandBase(BaseModel):
    sku_id: uuid.UUID
    location_id: uuid.UUID
    week_bucket: str = Field(..., max_length=16, description="Weekly bucket e.g. 2026W01")
    forecast_qty: int = Field(..., ge=0)
    confidence_p50: int = Field(..., ge=0)
    confidence_p90: int = Field(..., ge=0)
    version: str = Field(default="v1.0", max_length=32)

    @model_validator(mode="after")
    def validate_confidence_interval(self):
        if self.confidence_p90 < self.confidence_p50:
            raise ValueError("confidence_p90 must be greater than or equal to confidence_p50")
        return self


class ForecastDemandCreate(ForecastDemandBase):
    business_id: str = Field(..., max_length=64)


class ForecastDemandResponse(ForecastDemandBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


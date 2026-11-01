"""SupplyChain IQ - Common API Request & Response Schemas."""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard query pagination and sorting parameters."""
    page: int = Field(default=1, ge=1, description="1-based page index")
    page_size: int = Field(default=50, ge=1, le=500, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field name to sort by")
    sort_dir: Optional[str] = Field(default="asc", pattern="^(asc|desc|ASC|DESC)$", description="Sort direction")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: List[T]
    total: int = Field(description="Total number of items matching filters")
    page: int = Field(description="Current page index")
    page_size: int = Field(description="Configured items per page")
    total_pages: int = Field(description="Total available pages")

    model_config = ConfigDict(from_attributes=True)


class StandardResponse(BaseModel):
    """Standard unified response envelope."""
    success: bool = True
    message: str = "Operation executed successfully."
    data: Optional[Any] = None


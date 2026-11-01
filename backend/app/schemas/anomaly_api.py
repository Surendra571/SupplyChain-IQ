"""SupplyChain IQ - Data Quality & Anomaly API Schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataQualityIssueItem(BaseModel):
    """Detected integrity violation or anomaly."""
    issue_id: str
    issue_type: str
    entity_type: str
    record_id: str
    severity: str
    detection_rule: str
    expected_result: str
    actual_result: str
    detected_at: datetime


class AnomalyScanResponse(BaseModel):
    """Comprehensive data quality scan results."""
    scan_timestamp: datetime
    data_source: str
    total_issues: int
    critical_issues: int
    warning_issues: int
    issues_by_type: Dict[str, int]
    issues_by_entity: Dict[str, int]
    items: List[DataQualityIssueItem]
    evaluation_metrics: Optional[Dict[str, Any]] = None


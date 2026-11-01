"""SupplyChain IQ - Data Quality & Validation Models."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationCategory(str, Enum):
    PRIMARY_KEY_UNIQUENESS = "PRIMARY_KEY_UNIQUENESS"
    FOREIGN_KEY_INTEGRITY = "FOREIGN_KEY_INTEGRITY"
    REQUIRED_FIELDS = "REQUIRED_FIELDS"
    ENUM_VALIDATION = "ENUM_VALIDATION"
    DATE_ORDERING = "DATE_ORDERING"
    QUANTITY_RECONCILIATION = "QUANTITY_RECONCILIATION"
    UNIT_OF_MEASURE_CONSISTENCY = "UNIT_OF_MEASURE_CONSISTENCY"
    SUPPLIER_CAPACITY = "SUPPLIER_CAPACITY"
    DUPLICATE_RECEIPT = "DUPLICATE_RECEIPT"
    SUBSTITUTE_APPROVAL = "SUBSTITUTE_APPROVAL"
    LIFECYCLE_TRANSITIONS = "LIFECYCLE_TRANSITIONS"
    INVENTORY_TRANSACTION_RECONCILIATION = "INVENTORY_TRANSACTION_RECONCILIATION"


@dataclass
class DataQualityIssue:
    """Represents an explicit data quality or anomaly issue detected in the dataset."""
    issue_id: str
    issue_type: str
    entity_type: str
    record_id: str
    severity: str
    detection_rule: str
    expected_result: str
    actual_result: str
    detected_at: str
    category: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """Aggregate result from executing the complete validation engine."""
    dataset_name: str
    total_records_checked: int
    total_issues_found: int
    issues: List[DataQualityIssue] = field(default_factory=list)
    category_counts: Dict[str, int] = field(default_factory=dict)
    severity_counts: Dict[str, int] = field(default_factory=dict)
    entity_counts: Dict[str, int] = field(default_factory=dict)
    status: str = "PASSED"

    def add_issue(self, issue: DataQualityIssue):
        self.issues.append(issue)
        self.total_issues_found = len(self.issues)
        self.category_counts[issue.category] = self.category_counts.get(issue.category, 0) + 1
        self.severity_counts[issue.severity] = self.severity_counts.get(issue.severity, 0) + 1
        self.entity_counts[issue.entity_type] = self.entity_counts.get(issue.entity_type, 0) + 1
        if issue.severity in [ValidationSeverity.CRITICAL.value, ValidationSeverity.HIGH.value]:
            self.status = "FAILED"

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "status": self.status,
            "total_records_checked": self.total_records_checked,
            "total_issues_found": self.total_issues_found,
            "severity_breakdown": self.severity_counts,
            "category_breakdown": self.category_counts,
            "entity_breakdown": self.entity_counts,
        }


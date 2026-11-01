"""SupplyChain IQ - Data Quality & Anomaly Scan Service."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.schemas.anomaly_api import AnomalyScanResponse, DataQualityIssueItem
from backend.app.validation.engine import ValidationEngine
from backend.app.validation.evaluation import EvaluationModule


class AnomalyService:
    def __init__(self, data_dir: Path = Path("data/generated/starter/csv")):
        self.data_dir = data_dir
        self.ground_truth_path = data_dir.parent / "ground_truth.csv"

    def run_scan(self, include_evaluation: bool = True) -> AnomalyScanResponse:
        """Execute full 12-suite validation scan and return structured issue report."""
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {self.data_dir}")

        dataset = ValidationEngine.load_from_directory(self.data_dir)
        engine = ValidationEngine(dataset_name=self.data_dir.name)
        result = engine.validate(dataset)

        eval_metrics = None
        if include_evaluation and self.ground_truth_path.exists():
            eval_mod = EvaluationModule.load_ground_truth(self.ground_truth_path)
            eval_metrics = eval_mod.evaluate(result)

        items = [
            DataQualityIssueItem(
                issue_id=i.issue_id,
                issue_type=i.issue_type,
                entity_type=i.entity_type,
                record_id=i.record_id,
                severity=i.severity.value if hasattr(i.severity, "value") else str(i.severity),
                detection_rule=i.detection_rule,
                expected_result=i.expected_result,
                actual_result=i.actual_result,
                detected_at=i.detected_at,
            )
            for i in result.issues
        ]

        # Calculate category and entity counts
        by_type: Dict[str, int] = {}
        by_entity: Dict[str, int] = {}
        critical_count = 0
        warning_count = 0

        for i in items:
            by_type[i.issue_type] = by_type.get(i.issue_type, 0) + 1
            by_entity[i.entity_type] = by_entity.get(i.entity_type, 0) + 1
            if i.severity.upper() == "CRITICAL":
                critical_count += 1
            else:
                warning_count += 1

        return AnomalyScanResponse(
            scan_timestamp=datetime.now(timezone.utc),
            data_source=str(self.data_dir),
            total_issues=result.total_issues_found,
            critical_issues=critical_count,
            warning_issues=warning_count,
            issues_by_type=by_type,
            issues_by_entity=by_entity,
            items=items,
            evaluation_metrics=eval_metrics,
        )

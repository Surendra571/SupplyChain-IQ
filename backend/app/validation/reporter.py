"""SupplyChain IQ - Data Quality & Validation Report Exporter."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from backend.app.validation.evaluation import TARGET_ANOMALY_TYPES
from backend.app.validation.models import ValidationResult


class ValidationReporter:
    """Exports validation results and evaluation metrics into standardized reports."""

    def __init__(self, validation_result: ValidationResult, evaluation_metrics: Optional[Dict[str, Any]] = None):
        self.validation_result = validation_result
        self.evaluation_metrics = evaluation_metrics

    def export_reports(self, output_dir: Path) -> Dict[str, Path]:
        """Generate all four required reporting artifacts."""
        output_dir.mkdir(parents=True, exist_ok=True)

        summary_path = output_dir / "validation_summary.json"
        details_path = output_dir / "validation_details.csv"
        anomaly_path = output_dir / "anomaly_report.csv"
        metrics_path = output_dir / "validation_metrics.json"

        # 1. Export validation_summary.json
        summary_data = self.validation_result.to_summary_dict()
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        # 2. Export validation_details.csv
        issues_dicts = [i.to_dict() for i in self.validation_result.issues]
        if issues_dicts:
            df_details = pd.DataFrame(issues_dicts)
        else:
            df_details = pd.DataFrame(columns=[
                "issue_id", "issue_type", "entity_type", "record_id",
                "severity", "detection_rule", "expected_result", "actual_result",
                "detected_at", "category"
            ])
        df_details.to_csv(details_path, index=False)

        # 3. Export anomaly_report.csv
        anomaly_issues = [
            i.to_dict() for i in self.validation_result.issues
            if i.issue_type in TARGET_ANOMALY_TYPES
        ]
        if anomaly_issues:
            df_anomalies = pd.DataFrame(anomaly_issues)
        else:
            df_anomalies = pd.DataFrame(columns=[
                "issue_id", "issue_type", "entity_type", "record_id",
                "severity", "detection_rule", "expected_result", "actual_result",
                "detected_at", "category"
            ])
        df_anomalies.to_csv(anomaly_path, index=False)

        # 4. Export validation_metrics.json
        metrics_data = self.evaluation_metrics or {
            "status": "NO_EVALUATION_PERFORMED",
            "message": "Ground truth not provided for evaluation comparison.",
        }
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2)

        return {
            "validation_summary": summary_path,
            "validation_details": details_path,
            "anomaly_report": anomaly_path,
            "validation_metrics": metrics_path,
        }


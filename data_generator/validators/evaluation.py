"""SupplyChain IQ - Independent Evaluation Module for Anomaly Detection Benchmarking."""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.validation.models import DataQualityIssue, ValidationResult

TARGET_ANOMALY_TYPES = {
    "INBOUND_INVENTORY_COUNTED_TWICE",
    "SUBSTITUTE_SKU_NOT_APPROVED",
    "SUPPLIER_CAPACITY_EXCEEDED",
    "SHORTAGE_CALCULATED_WITHOUT_LEAD_TIME",
    "UNIT_OF_MEASURE_MISMATCH",
}


class EvaluationModule:
    """Compares validation results against isolated ground-truth labels.
    Calculates precision, recall, F1 score, false positives, and false negatives.
    """

    def __init__(self, ground_truth: List[Dict[str, Any]]):
        self.ground_truth = ground_truth

    @classmethod
    def load_ground_truth(cls, ground_truth_path: Path) -> "EvaluationModule":
        """Load ground truth records from ground_truth.csv."""
        if not ground_truth_path.exists():
            raise FileNotFoundError(f"Ground truth file not found at: {ground_truth_path}")

        records = []
        with open(ground_truth_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
        return cls(records)

    def evaluate(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """Perform strict evaluation of detected anomalies against ground-truth labels."""
        # Filter validation issues to anomaly types
        detected_anomalies = [
            issue for issue in validation_result.issues
            if issue.issue_type in TARGET_ANOMALY_TYPES
        ]

        # Build ground-truth signatures: (anomaly_type, target_business_id)
        gt_signatures = {
            (gt["anomaly_type"], gt["target_business_id"]): gt
            for gt in self.ground_truth
        }

        matched_gt_signatures: Set[Tuple[str, str]] = set()
        true_positives: List[Dict[str, Any]] = []
        false_positives: List[Dict[str, Any]] = []

        for issue in detected_anomalies:
            sig = (issue.issue_type, issue.record_id)
            if sig in gt_signatures:
                matched_gt_signatures.add(sig)
                gt_rec = gt_signatures[sig]
                true_positives.append({
                    "issue_id": issue.issue_id,
                    "anomaly_id": gt_rec.get("anomaly_id"),
                    "scenario_name": gt_rec.get("scenario_name"),
                    "anomaly_type": issue.issue_type,
                    "record_id": issue.record_id,
                    "entity_type": issue.entity_type,
                    "detection_rule": issue.detection_rule,
                })
            else:
                false_positives.append(issue.to_dict())

        # False negatives: ground truth entries that were not detected
        false_negatives: List[Dict[str, Any]] = []
        for sig, gt_rec in gt_signatures.items():
            if sig not in matched_gt_signatures:
                false_negatives.append(gt_rec)

        tp_count = len(true_positives)
        fp_count = len(false_positives)
        fn_count = len(false_negatives)

        precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 1.0
        recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 1.0
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 1.0

        # Detailed breakdown by scenario
        scenario_breakdown = {}
        for gt in self.ground_truth:
            anom_id = gt.get("anomaly_id", "UNKNOWN")
            is_detected = any(tp["anomaly_id"] == anom_id for tp in true_positives)
            scenario_breakdown[anom_id] = {
                "scenario_name": gt.get("scenario_name"),
                "anomaly_type": gt.get("anomaly_type"),
                "target_entity": gt.get("target_entity"),
                "target_business_id": gt.get("target_business_id"),
                "detected": is_detected,
                "status": "PASS" if is_detected else "FAIL",
            }

        return {
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_ground_truth_anomalies": len(self.ground_truth),
            "true_positives_count": tp_count,
            "false_positives_count": fp_count,
            "false_negatives_count": fn_count,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "scenario_breakdown": scenario_breakdown,
            "evaluation_result": "SUCCESS" if (precision == 1.0 and recall == 1.0) else "BENCHMARK_FAILED",
        }


"""SupplyChain IQ - Data Quality & Validation Engine."""

import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from backend.app.validation.models import DataQualityIssue, ValidationResult
from backend.app.validation.rules import (
    validate_date_ordering,
    validate_duplicate_receipts,
    validate_enums,
    validate_foreign_key_integrity,
    validate_inventory_transaction_reconciliation,
    validate_lifecycle_transitions,
    validate_primary_key_uniqueness,
    validate_quantity_reconciliation,
    validate_required_fields,
    validate_substitute_approval,
    validate_supplier_capacity,
    validate_unit_of_measure_consistency,
)

logger = logging.getLogger("validation.engine")


class ValidationEngine:
    """Executes all 12 validation suites against supply chain planning datasets."""

    def __init__(self, dataset_name: str = "dataset"):
        self.dataset_name = dataset_name

    @classmethod
    def load_from_directory(cls, dir_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Load entity tables from CSV or JSON in directory."""
        dataset: Dict[str, List[Dict[str, Any]]] = {}

        csv_dir = dir_path / "csv" if (dir_path / "csv").exists() else dir_path
        json_dir = dir_path / "json" if (dir_path / "json").exists() else None

        if json_dir and list(json_dir.glob("*.json")):
            for json_file in json_dir.glob("*.json"):
                if json_file.name in ["manifest.json", "validation_summary.json", "validation_metrics.json", "checksums.json"]:
                    continue
                table_name = json_file.stem
                with open(json_file, "r", encoding="utf-8") as f:
                    dataset[table_name] = json.load(f)
            return dataset

        # Fallback to CSV
        for csv_file in csv_dir.glob("*.csv"):
            if csv_file.name in ["ground_truth.csv", "validation_details.csv", "anomaly_report.csv"]:
                continue
            table_name = csv_file.stem
            rows: List[Dict[str, Any]] = []
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse numeric fields where appropriate
                    parsed = {}
                    for k, v in row.items():
                        if v == "" or v == "None":
                            parsed[k] = None
                        elif k in ["on_hand_qty", "allocated_qty", "safety_stock_qty", "reorder_point",
                                   "forecast_qty", "confidence_p50", "confidence_p90",
                                   "moq", "pack_size", "lead_time_days", "transit_days", "variability_days",
                                   "planned_quantity", "ordered_qty", "received_qty",
                                   "max_capacity_units", "committed_units", "surge_capacity_units"]:
                            try:
                                parsed[k] = int(v)
                            except (ValueError, TypeError):
                                parsed[k] = v
                        elif k in ["unit_cost", "unit_price", "weight_kg", "quantity_per_parent",
                                   "scrap_percentage", "conversion_factor", "cost_per_unit", "total_amount"]:
                            try:
                                parsed[k] = float(v)
                            except (ValueError, TypeError):
                                parsed[k] = v
                        elif k in ["is_active", "is_preferred", "is_bidirectional"]:
                            parsed[k] = v.lower() == "true"
                        else:
                            parsed[k] = v
                    rows.append(parsed)
            dataset[table_name] = rows

        return dataset

    def validate(self, dataset: Dict[str, List[Dict[str, Any]]]) -> ValidationResult:
        """Run all 12 validation suites and return aggregated ValidationResult."""
        total_records = sum(len(records) for records in dataset.values())
        result = ValidationResult(
            dataset_name=self.dataset_name,
            total_records_checked=total_records,
            total_issues_found=0,
            status="PASSED",
        )

        issue_counter = [0]

        # 1. Primary key uniqueness
        for issue in validate_primary_key_uniqueness(dataset, issue_counter):
            result.add_issue(issue)

        # 2. Foreign key integrity
        for issue in validate_foreign_key_integrity(dataset, issue_counter):
            result.add_issue(issue)

        # 3. Required field validation
        for issue in validate_required_fields(dataset, issue_counter):
            result.add_issue(issue)

        # 4. Enum validation
        for issue in validate_enums(dataset, issue_counter):
            result.add_issue(issue)

        # 5. Date ordering
        for issue in validate_date_ordering(dataset, issue_counter):
            result.add_issue(issue)

        # 6. Quantity reconciliation
        for issue in validate_quantity_reconciliation(dataset, issue_counter):
            result.add_issue(issue)

        # 7. Unit of measure consistency
        for issue in validate_unit_of_measure_consistency(dataset, issue_counter):
            result.add_issue(issue)

        # 8. Supplier capacity validation
        for issue in validate_supplier_capacity(dataset, issue_counter):
            result.add_issue(issue)

        # 9. Duplicate purchase order receipt detection
        for issue in validate_duplicate_receipts(dataset, issue_counter):
            result.add_issue(issue)

        # 10. Substitute approval validation
        for issue in validate_substitute_approval(dataset, issue_counter):
            result.add_issue(issue)

        # 11. Lifecycle transition validation
        for issue in validate_lifecycle_transitions(dataset, issue_counter):
            result.add_issue(issue)

        # 12. Inventory transaction reconciliation
        # Note: If duplicate receipt already identified for an inventory, avoid duplicate logging
        for issue in validate_inventory_transaction_reconciliation(dataset, issue_counter):
            # Check if this inventory record already has an issue logged under DUPLICATE_RECEIPT
            existing_dups = {i.record_id for i in result.issues if i.issue_type == "INBOUND_INVENTORY_COUNTED_TWICE"}
            if issue.record_id not in existing_dups:
                result.add_issue(issue)

        return result


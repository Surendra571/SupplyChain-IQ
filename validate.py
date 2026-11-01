"""SupplyChain IQ - Data Quality & Validation CLI Tool."""

import argparse
import json
import logging
from pathlib import Path
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.app.validation.engine import ValidationEngine
from backend.app.validation.evaluation import EvaluationModule
from backend.app.validation.reporter import ValidationReporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate")


def run_validation(data_dir: Path, ground_truth_path: Path = None, output_dir: Path = None) -> int:
    """Execute complete validation suite and generate quality reports."""
    logger.info(f"Loading dataset from: {data_dir}...")
    dataset = ValidationEngine.load_from_directory(data_dir)

    total_records = sum(len(r) for r in dataset.values())
    logger.info(f"Loaded {len(dataset)} entities with {total_records:,} total records.")

    engine = ValidationEngine(dataset_name=data_dir.name)
    logger.info("Running 12 validation suites across dataset...")
    result = engine.validate(dataset)

    logger.info(f"Validation complete: {result.total_issues_found} issues detected. Status: {result.status}")
    logger.info(f"Severity breakdown: {result.severity_counts}")
    logger.info(f"Category breakdown: {result.category_counts}")

    # Evaluate against ground truth if provided
    eval_metrics = None
    if ground_truth_path and ground_truth_path.exists():
        logger.info(f"Evaluating detected anomalies against ground truth: {ground_truth_path}...")
        eval_mod = EvaluationModule.load_ground_truth(ground_truth_path)
        eval_metrics = eval_mod.evaluate(result)

        logger.info("=== EVALUATION BENCHMARK METRICS ===")
        logger.info(f"  Precision: {eval_metrics['precision']:.4f}")
        logger.info(f"  Recall:    {eval_metrics['recall']:.4f}")
        logger.info(f"  F1 Score:  {eval_metrics['f1_score']:.4f}")
        logger.info(f"  True Positives:  {eval_metrics['true_positives_count']}")
        logger.info(f"  False Positives: {eval_metrics['false_positives_count']}")
        logger.info(f"  False Negatives: {eval_metrics['false_negatives_count']}")

        for anom_id, sc in eval_metrics["scenario_breakdown"].items():
            logger.info(f"  [{sc['status']}] {anom_id}: {sc['scenario_name']} -> Detected: {sc['detected']}")

    # Export reports
    out = output_dir or data_dir
    reporter = ValidationReporter(result, eval_metrics)
    exported_files = reporter.export_reports(out)
    logger.info("Generated reports:")
    for report_name, report_path in exported_files.items():
        logger.info(f"  - {report_name}: {report_path}")

    return 0 if (eval_metrics and eval_metrics["f1_score"] == 1.0) or (not eval_metrics and result.status == "PASSED") else 1


def main():
    parser = argparse.ArgumentParser(description="SupplyChain IQ Data Quality & Validation Engine")
    parser.add_argument("--data-dir", type=str, default="data/generated/starter", help="Directory containing dataset")
    parser.add_argument("--ground-truth", type=str, default=None, help="Path to ground_truth.csv")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save quality reports")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    gt_path = Path(args.ground_truth) if args.ground_truth else (data_dir / "ground_truth.csv")
    out_dir = Path(args.output_dir) if args.output_dir else data_dir

    sys.exit(run_validation(data_dir, gt_path, out_dir))


if __name__ == "__main__":
    main()


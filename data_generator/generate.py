"""SupplyChain IQ - Synthetic Data Generator CLI & Pipeline Orchestrator."""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
import sys

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_generator.generators.config import GeneratorConfig
from data_generator.generators.core import SyntheticDataGenerator
from data_generator.generators.exporters import DatasetExporter
from data_generator.scenarios.anomalies import AnomalyInjector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("data_generator")

MASTER_ENTITIES = {
    "skus", "locations", "suppliers", "boms", "bom_components",
    "supplier_skus", "substitute_skus", "lead_times",
}
TRANSACTION_ENTITIES = {
    "purchase_orders", "purchase_order_lines", "production_plans",
    "forecast_demands", "inventories", "supplier_capacities",
}
EVENT_ENTITIES = {
    "inventory_transactions", "shipments",
}


def organize_dataset_into_directories(raw_csv_dir: Path, data_root: Path):
    """Organize generated flat CSV files into master, transactions, events, ground_truth, and manifests."""
    master_dir = data_root / "generated" / "master"
    tx_dir = data_root / "generated" / "transactions"
    events_dir = data_root / "generated" / "events"
    gt_dir = data_root / "ground_truth"
    man_dir = data_root / "manifests"

    for d in [master_dir, tx_dir, events_dir, gt_dir, man_dir]:
        d.mkdir(parents=True, exist_ok=True)

    for csv_file in raw_csv_dir.glob("*.csv"):
        entity = csv_file.stem
        if entity in MASTER_ENTITIES:
            shutil.copy2(csv_file, master_dir / csv_file.name)
        elif entity in TRANSACTION_ENTITIES:
            shutil.copy2(csv_file, tx_dir / csv_file.name)
        elif entity in EVENT_ENTITIES:
            shutil.copy2(csv_file, events_dir / csv_file.name)

    parent_dir = raw_csv_dir.parent
    for gt_name in ["ground_truth.csv", "anomaly_report.csv"]:
        gt_file = parent_dir / gt_name
        if gt_file.exists():
            shutil.copy2(gt_file, gt_dir / gt_name)

    for man_name in ["manifest.json", "checksums.json", "validation_metrics.json", "validation_report.json", "validation_summary.json"]:
        man_file = parent_dir / man_name
        if man_file.exists():
            shutil.copy2(man_file, man_dir / man_name)

    logger.info("Organized generated data into structured master/, transactions/, events/, ground_truth/, and manifests/.")


def run_generation(scale: str, seed: int, output_dir: Path, config_path: Path, inject_anomalies: bool = True, organize: bool = True) -> dict:
    """Execute complete generation pipeline for specified scale and seed."""
    logger.info(f"Loading configuration from {config_path} for scale '{scale}' with seed {seed}...")
    config = GeneratorConfig.load_from_yaml(config_path, scale_name=scale)
    config.seed = seed

    logger.info("Starting deterministic synthetic data generation...")
    generator = SyntheticDataGenerator(config)
    baseline_dataset = generator.generate_all()

    for entity_name, records in baseline_dataset.items():
        logger.info(f"  Generated {len(records):6d} records for {entity_name}")

    if inject_anomalies:
        logger.info("Injecting deliberate anomaly scenarios and generating ground_truth catalog...")
        injector = AnomalyInjector(baseline_dataset)
        final_dataset, ground_truth = injector.inject_all()
        logger.info(f"  Injected {len(ground_truth)} anomalies into operational dataset.")
    else:
        final_dataset = baseline_dataset
        ground_truth = []

    logger.info(f"Exporting dataset to {output_dir} in multiple formats (CSV, GZ, JSON, SQL, Parquet)...")
    meta = {
        "scale": scale,
        "seed": seed,
        "generated_at": "2026-01-05T00:00:00+00:00",
    }
    exporter = DatasetExporter(final_dataset, ground_truth, output_dir, meta)
    checksums = exporter.export_all()

    if organize:
        organize_dataset_into_directories(output_dir / "csv", REPO_ROOT / "data")

    logger.info(f"Generation completed successfully! Output directory: {output_dir}")
    return checksums


def compare_runs(scale: str, seed: int, config_path: Path) -> bool:
    """Run generation twice and verify deterministic byte-for-byte reproducibility."""
    dir1 = Path(f"data/generated_run1_{scale}")
    dir2 = Path(f"data/generated_run2_{scale}")

    logger.info(f"=== Determinism Test: Run 1 on {dir1} ===")
    chk1 = run_generation(scale, seed, dir1, config_path, organize=False)

    logger.info(f"=== Determinism Test: Run 2 on {dir2} ===")
    chk2 = run_generation(scale, seed, dir2, config_path, organize=False)

    logger.info("Comparing checksums between Run 1 and Run 2...")
    match = (chk1 == chk2)
    if match:
        logger.info("DETERMINISM VERIFIED: All row counts and SHA-256 file checksums match 100%!")
    else:
        logger.error("DETERMINISM FAILED: Checksums differ between runs!")
        diffs = {k: (chk1.get(k), chk2.get(k)) for k in chk1 if chk1.get(k) != chk2.get(k)}
        logger.error(f"Differences: {diffs}")
    return match


def main():
    parser = argparse.ArgumentParser(description="SupplyChain IQ Deterministic Synthetic Data Generator")
    parser.add_argument("--scale", choices=["starter", "medium", "full"], default="starter", help="Data scale preset")
    parser.add_argument("--seed", type=int, default=20261022, help="Fixed random seed (default: 20261022)")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--compare-determinism", action="store_true", help="Run twice and verify identical outputs")
    parser.add_argument("--no-anomalies", action="store_true", help="Disable anomaly injection")
    parser.add_argument("--no-organize", action="store_true", help="Skip populating structured data/ subdirectories")

    args = parser.parse_args()

    config_path = Path(args.config)
    output_dir = Path(args.output_dir) if args.output_dir else REPO_ROOT / "data" / "generated" / args.scale

    if args.compare_determinism:
        success = compare_runs(args.scale, args.seed, config_path)
        sys.exit(0 if success else 1)
    else:
        run_generation(
            args.scale,
            args.seed,
            output_dir,
            config_path,
            inject_anomalies=not args.no_anomalies,
            organize=not args.no_organize,
        )


if __name__ == "__main__":
    main()


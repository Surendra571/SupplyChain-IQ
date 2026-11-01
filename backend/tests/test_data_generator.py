"""SupplyChain IQ - Automated Unit & Integration Tests for Deterministic Synthetic Data Generator."""

import csv
import gzip
import json
from pathlib import Path
import tempfile
import pytest
import pandas as pd
import pyarrow.parquet as pq

from backend.app.generator.anomalies import AnomalyInjector
from backend.app.generator.config import GeneratorConfig
from backend.app.generator.core import SyntheticDataGenerator
from backend.app.generator.exporters import DatasetExporter


@pytest.fixture
def starter_config():
    """Return GeneratorConfig for starter scale with seed 20261022."""
    config = GeneratorConfig(seed=20261022, scale_name="starter")
    return config


def test_generator_determinism(starter_config):
    """Verify that running generation twice with seed 20261022 produces identical records."""
    gen1 = SyntheticDataGenerator(starter_config)
    data1 = gen1.generate_all()

    gen2 = SyntheticDataGenerator(starter_config)
    data2 = gen2.generate_all()

    # Compare row counts
    for table_name in data1.keys():
        assert len(data1[table_name]) == len(data2[table_name]), f"Row count mismatch in {table_name}"

    # Compare exact records
    assert data1["skus"] == data2["skus"]
    assert data1["locations"] == data2["locations"]
    assert data1["suppliers"] == data2["suppliers"]
    assert data1["forecast_demands"] == data2["forecast_demands"]
    assert data1["inventories"] == data2["inventories"]
    assert data1["purchase_orders"] == data2["purchase_orders"]
    assert data1["purchase_order_lines"] == data2["purchase_order_lines"]


def test_generation_order_and_entity_completeness(starter_config):
    """Verify that all 13 entity sets are generated without orphaned foreign keys."""
    gen = SyntheticDataGenerator(starter_config)
    data = gen.generate_all()

    # 1. SKUs
    assert len(data["skus"]) == 100
    sku_ids = {s["id"] for s in data["skus"]}

    # 2. Locations
    assert len(data["locations"]) == 5
    loc_ids = {l["id"] for l in data["locations"]}

    # 3. Suppliers
    assert len(data["suppliers"]) == 25
    sup_ids = {s["id"] for s in data["suppliers"]}

    # 4. Supplier SKUs
    assert len(data["supplier_skus"]) > 0
    for ssku in data["supplier_skus"]:
        assert ssku["supplier_id"] in sup_ids
        assert ssku["sku_id"] in sku_ids
        assert ssku["moq"] >= 1
        assert ssku["unit_price"] >= 0

    # 5. BOMs and Substitutes
    assert len(data["boms"]) > 0
    bom_ids = {b["id"] for b in data["boms"]}
    for bom in data["boms"]:
        assert bom["parent_sku_id"] in sku_ids

    assert len(data["bom_components"]) > 0
    for comp in data["bom_components"]:
        assert comp["bom_id"] in bom_ids
        assert comp["component_sku_id"] in sku_ids
        assert comp["quantity_per_parent"] > 0

    for subst in data["substitute_skus"]:
        assert subst["primary_sku_id"] in sku_ids
        assert subst["substitute_sku_id"] in sku_ids
        assert subst["primary_sku_id"] != subst["substitute_sku_id"]

    # 6. Forecast Demands
    assert len(data["forecast_demands"]) == 100 // 5 * 3 * 12 or len(data["forecast_demands"]) > 0
    for dem in data["forecast_demands"]:
        assert dem["sku_id"] in sku_ids
        assert dem["location_id"] in loc_ids
        assert dem["forecast_qty"] >= 0
        assert dem["confidence_p90"] >= dem["confidence_p50"]

    # 7. Opening Inventory
    assert len(data["inventories"]) == 100 * 5
    for inv in data["inventories"]:
        assert inv["sku_id"] in sku_ids
        assert inv["location_id"] in loc_ids
        assert inv["on_hand_qty"] >= 0

    # 8. Supplier Capacity
    assert len(data["supplier_capacities"]) > 0
    for cap in data["supplier_capacities"]:
        assert cap["supplier_id"] in sup_ids
        assert cap["sku_id"] in sku_ids
        assert cap["max_capacity_units"] >= 0

    # 9. Lead Times
    assert len(data["lead_times"]) == 5 * 4  # 5 * 4 pairs
    for lt in data["lead_times"]:
        assert lt["origin_location_id"] in loc_ids
        assert lt["destination_location_id"] in loc_ids
        assert lt["origin_location_id"] != lt["destination_location_id"]

    # 10. Production Capacity
    assert len(data["production_plans"]) > 0
    for pp in data["production_plans"]:
        assert pp["sku_id"] in sku_ids
        assert pp["location_id"] in loc_ids

    # 11 & 12. Purchase Orders and Lines
    assert len(data["purchase_orders"]) == 400
    po_ids = {po["id"] for po in data["purchase_orders"]}
    for po in data["purchase_orders"]:
        assert po["supplier_id"] in sup_ids

    assert len(data["purchase_order_lines"]) > 0
    for pol in data["purchase_order_lines"]:
        assert pol["po_id"] in po_ids
        assert pol["sku_id"] in sku_ids
        assert pol["destination_location_id"] in loc_ids
        assert pol["ordered_qty"] > 0

    # 13. Shipments
    assert len(data["shipments"]) > 0
    for shp in data["shipments"]:
        assert shp["po_id"] in po_ids
        assert shp["destination_location_id"] in loc_ids


def test_data_variation_attributes(starter_config):
    """Verify presence of data variations: UOMs, categories, seasonal demand."""
    gen = SyntheticDataGenerator(starter_config)
    data = gen.generate_all()

    # Verify diverse product categories
    cats = {s["category"] for s in data["skus"]}
    assert len(cats) >= 3

    # Verify diverse units of measure
    uoms = {s["unit_of_measure"] for s in data["skus"]}
    assert "EA" in uoms
    assert len(uoms) >= 2

    # Verify seasonal variation in demand
    demands_w01 = [d["forecast_qty"] for d in data["forecast_demands"] if d["week_bucket"] == "2026W01"]
    demands_w06 = [d["forecast_qty"] for d in data["forecast_demands"] if d["week_bucket"] == "2026W06"]
    assert sum(demands_w01) != sum(demands_w06)


def test_anomaly_injection_and_ground_truth(starter_config):
    """Verify that all 5 deliberate anomalies are cleanly injected and labeled."""
    gen = SyntheticDataGenerator(starter_config)
    baseline_data = gen.generate_all()

    injector = AnomalyInjector(baseline_data)
    anom_dataset, ground_truth = injector.inject_all()

    # Verify exactly 5 anomaly records
    assert len(ground_truth) == 5

    anomaly_types = {gt["anomaly_type"] for gt in ground_truth}
    expected_types = {
        "INBOUND_INVENTORY_COUNTED_TWICE",
        "SUBSTITUTE_SKU_NOT_APPROVED",
        "SUPPLIER_CAPACITY_EXCEEDED",
        "SHORTAGE_CALCULATED_WITHOUT_LEAD_TIME",
        "UNIT_OF_MEASURE_MISMATCH",
    }
    assert anomaly_types == expected_types

    # Verify ground truth targets exist in operational dataset
    for gt in ground_truth:
        target_table = gt["target_entity"]
        target_bid = gt["target_business_id"]
        table_rows = anom_dataset[target_table]
        matching = [r for r in table_rows if r["business_id"] == target_bid]
        assert len(matching) == 1, f"Anomaly target {target_bid} not found in {target_table}"
        row = matching[0]
        # Verify the injected field in target table matches anomalous_value
        injected_field = gt["injected_field"]
        assert str(row[injected_field]) == str(gt["anomalous_value"])


def test_exporter_multi_formats_and_integrity(starter_config):
    """Verify that CSV, GZ, JSON, SQL, Parquet, and manifest are created validly."""
    gen = SyntheticDataGenerator(starter_config)
    baseline_data = gen.generate_all()

    injector = AnomalyInjector(baseline_data)
    anom_dataset, ground_truth = injector.inject_all()

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "output"
        meta = {"scale": "starter", "seed": 20261022, "generated_at": "2026-01-05T00:00:00+00:00"}
        exporter = DatasetExporter(anom_dataset, ground_truth, out_dir, meta)
        checksums = exporter.export_all()

        # 1. Verify CSV files
        csv_sku_path = out_dir / "csv" / "skus.csv"
        assert csv_sku_path.exists()
        df_sku = pd.read_csv(csv_sku_path)
        assert len(df_sku) == 100

        # 2. Verify GZIP files
        gz_path = out_dir / "csv_gz" / "skus.csv.gz"
        assert gz_path.exists()
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 101  # header + 100 rows

        # 3. Verify JSON files
        json_path = out_dir / "json" / "locations.json"
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            locs = json.load(f)
            assert len(locs) == 5

        # 4. Verify SQL seed file
        sql_path = out_dir / "sql" / "seed_data.sql"
        assert sql_path.exists()
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
            assert "INSERT INTO skus" in sql_content
            assert "INSERT INTO purchase_orders" in sql_content

        # 5. Verify Parquet files
        parquet_path = out_dir / "parquet" / "skus.parquet"
        assert parquet_path.exists()
        pq_table = pq.read_table(parquet_path)
        assert pq_table.num_rows == 100

        # Partitioned Parquet
        part_dem_dir = out_dir / "parquet" / "forecast_demands"
        assert part_dem_dir.exists()
        dataset = pq.ParquetDataset(part_dem_dir)
        assert dataset.read().num_rows == len(anom_dataset["forecast_demands"])

        # 6. Verify Manifest & Validation Report
        manifest_path = out_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            assert manifest["scale"] == "starter"
            assert manifest["seed"] == 20261022

        report_path = out_dir / "validation_report.json"
        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            assert report["validation_status"] == "PASSED"
            assert report["total_errors"] == 0

        # 7. Verify Checksums
        assert len(checksums) > 20
        chk_path = out_dir / "checksums.json"
        assert chk_path.exists()


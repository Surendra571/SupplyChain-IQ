"""SupplyChain IQ - Multi-Format Dataset Exporters (CSV, GZIP, JSON, SQL, Parquet)."""

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class DatasetExporter:
    """Exports generated supply chain datasets to CSV, CSV.GZ, JSON, SQL, and Parquet."""

    def __init__(self, dataset: Dict[str, List[Dict[str, Any]]], ground_truth: List[Dict[str, Any]], output_dir: Path, meta: Dict[str, Any]):
        self.dataset = dataset
        self.ground_truth = ground_truth
        self.output_dir = output_dir
        self.meta = meta

        # Subdirectories
        self.csv_dir = self.output_dir / "csv"
        self.gz_dir = self.output_dir / "csv_gz"
        self.json_dir = self.output_dir / "json"
        self.sql_dir = self.output_dir / "sql"
        self.parquet_dir = self.output_dir / "parquet"

        for d in [self.csv_dir, self.gz_dir, self.json_dir, self.sql_dir, self.parquet_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def export_all(self) -> Dict[str, str]:
        """Execute all export formats, generate manifest, validation report, and checksums."""
        self._export_csv()
        self._export_csv_gz()
        self._export_json()
        self._export_sql()
        self._export_parquet()
        self._export_ground_truth()

        self._export_manifest()
        self._export_validation_report()
        checksums = self._generate_checksums()

        return checksums

    def _export_csv(self):
        for table_name, rows in self.dataset.items():
            df = pd.DataFrame(rows)
            csv_path = self.csv_dir / f"{table_name}.csv"
            df.to_csv(csv_path, index=False)

    def _export_csv_gz(self):
        for table_name in self.dataset.keys():
            csv_path = self.csv_dir / f"{table_name}.csv"
            gz_path = self.gz_dir / f"{table_name}.csv.gz"
            # Use fixed mtime=0 so gzip bytes are 100% deterministic
            with open(csv_path, "rb") as f_in, gzip.GzipFile(gz_path, "wb", mtime=0) as f_out:
                f_out.writelines(f_in)

    def _export_json(self):
        for table_name, rows in self.dataset.items():
            json_path = self.json_dir / f"{table_name}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, default=str)

    def _export_sql(self):
        sql_path = self.sql_dir / "seed_data.sql"
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write("-- SupplyChain IQ Synthetic Data Seed Script\n")
            f.write(f"-- Scale: {self.meta.get('scale')}, Seed: {self.meta.get('seed')}\n\n")

            for table_name, rows in self.dataset.items():
                if not rows:
                    continue
                f.write(f"-- Table: {table_name}\n")
                columns = list(rows[0].keys())
                col_str = ", ".join(columns)

                for r in rows:
                    vals = []
                    for c in columns:
                        v = r[c]
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bool):
                            vals.append("TRUE" if v else "FALSE")
                        else:
                            clean_str = str(v).replace("'", "''")
                            vals.append(f"'{clean_str}'")
                    val_str = ", ".join(vals)
                    f.write(f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str}) ON CONFLICT DO NOTHING;\n")
                f.write("\n")

    def _export_parquet(self):
        for table_name, rows in self.dataset.items():
            if not rows:
                continue
            df = pd.DataFrame(rows)
            # Partition large time-series tables with deterministic basename
            if table_name == "forecast_demands" and "week_bucket" in df.columns:
                table = pa.Table.from_pandas(df)
                pq.write_to_dataset(table, root_path=str(self.parquet_dir / table_name), partition_cols=["week_bucket"], basename_template="part_{i}.parquet")
            elif table_name == "production_plans" and "week_bucket" in df.columns:
                table = pa.Table.from_pandas(df)
                pq.write_to_dataset(table, root_path=str(self.parquet_dir / table_name), partition_cols=["week_bucket"], basename_template="part_{i}.parquet")
            else:
                table = pa.Table.from_pandas(df)
                pq.write_table(table, self.parquet_dir / f"{table_name}.parquet")

    def _export_ground_truth(self):
        gt_path = self.output_dir / "ground_truth.csv"
        df_gt = pd.DataFrame(self.ground_truth)
        df_gt.to_csv(gt_path, index=False)

    def _export_manifest(self):
        row_counts = {name: len(rows) for name, rows in self.dataset.items()}
        manifest = {
            "project": "SupplyChain IQ",
            "seed": self.meta.get("seed"),
            "scale": self.meta.get("scale"),
            "generated_at": self.meta.get("generated_at"),
            "total_entities": len(self.dataset),
            "row_counts": row_counts,
            "anomaly_count": len(self.ground_truth),
        }
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def _export_validation_report(self):
        # Validate foreign key references across dataset
        errors = []
        sku_ids = {s["id"] for s in self.dataset["skus"]}
        loc_ids = {l["id"] for l in self.dataset["locations"]}
        sup_ids = {s["id"] for s in self.dataset["suppliers"]}
        po_ids = {p["id"] for p in self.dataset["purchase_orders"]}

        # Check inventory foreign keys
        for inv in self.dataset["inventories"]:
            if inv["sku_id"] not in sku_ids:
                errors.append(f"Orphaned inventory SKU: {inv['sku_id']}")
            if inv["location_id"] not in loc_ids:
                errors.append(f"Orphaned inventory Location: {inv['location_id']}")

        # Check forecast demand foreign keys
        for dem in self.dataset["forecast_demands"]:
            if dem["sku_id"] not in sku_ids:
                errors.append(f"Orphaned demand SKU: {dem['sku_id']}")
            if dem["location_id"] not in loc_ids:
                errors.append(f"Orphaned demand Location: {dem['location_id']}")

        # Check PO line foreign keys
        for pol in self.dataset["purchase_order_lines"]:
            if pol["po_id"] not in po_ids:
                errors.append(f"Orphaned PO line PO: {pol['po_id']}")
            if pol["sku_id"] not in sku_ids:
                errors.append(f"Orphaned PO line SKU: {pol['sku_id']}")

        report = {
            "validation_status": "PASSED" if not errors else "FAILED",
            "total_errors": len(errors),
            "errors": errors[:50],  # cap at 50 for readability
            "integrity_checks": {
                "foreign_keys_valid": len(errors) == 0,
                "anomalies_separated": (self.output_dir / "ground_truth.csv").exists(),
                "all_tables_populated": all(len(rows) > 0 for rows in self.dataset.values()),
            }
        }
        report_path = self.output_dir / "validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    def _generate_checksums(self) -> Dict[str, str]:
        checksums = {}
        # Collect all files recursively in output_dir
        for file_path in sorted(self.output_dir.rglob("*")):
            if file_path.is_file() and file_path.name != "checksums.json":
                rel_path = file_path.relative_to(self.output_dir).as_posix()
                hasher = hashlib.sha256()
                with open(file_path, "rb") as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
                checksums[rel_path] = hasher.hexdigest()

        checksum_path = self.output_dir / "checksums.json"
        with open(checksum_path, "w", encoding="utf-8") as f:
            json.dump(checksums, f, indent=2)

        return checksums

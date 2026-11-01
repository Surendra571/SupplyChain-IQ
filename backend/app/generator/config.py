"""SupplyChain IQ - Synthetic Data Generator Configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class ScaleConfig:
    skus: int
    locations: int
    weeks: int
    suppliers: int
    purchase_orders: int


@dataclass
class GeneratorConfig:
    seed: int = 20261022
    scale_name: str = "starter"
    scales: Dict[str, ScaleConfig] = field(default_factory=lambda: {
        "starter": ScaleConfig(skus=100, locations=5, weeks=12, suppliers=25, purchase_orders=400),
        "medium": ScaleConfig(skus=500, locations=15, weeks=26, suppliers=120, purchase_orders=2500),
        "full": ScaleConfig(skus=3000, locations=50, weeks=52, suppliers=500, purchase_orders=10000),
    })
    categories: List[str] = field(default_factory=lambda: [
        "Electronics", "Mechanical", "Raw Materials", "Packaging", "Subassemblies"
    ])
    units_of_measure: List[str] = field(default_factory=lambda: [
        "EA", "KG", "METER", "LITER", "BOX"
    ])

    @classmethod
    def load_from_yaml(cls, yaml_path: Path, scale_name: str = "starter") -> "GeneratorConfig":
        if not yaml_path.exists():
            return cls(scale_name=scale_name)
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        seed = data.get("seed", 20261022)
        scales_dict = {}
        for s_name, s_vals in data.get("scales", {}).items():
            scales_dict[s_name] = ScaleConfig(
                skus=s_vals["skus"],
                locations=s_vals["locations"],
                weeks=s_vals["weeks"],
                suppliers=s_vals.get("suppliers", 25),
                purchase_orders=s_vals.get("purchase_orders", 400),
            )

        return cls(
            seed=seed,
            scale_name=scale_name,
            scales=scales_dict or cls().scales,
            categories=data.get("categories", cls().categories),
            units_of_measure=data.get("units_of_measure", cls().units_of_measure),
        )

    @property
    def current_scale(self) -> ScaleConfig:
        return self.scales.get(self.scale_name, self.scales["starter"])


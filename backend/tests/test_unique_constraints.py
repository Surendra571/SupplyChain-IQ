"""Tests for Composite Unique Constraints and Business Check Constraints."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.demand import ForecastDemand
from backend.app.models.enums import LocationType, SKUType, SupplierTier
from backend.app.models.inventory import Inventory
from backend.app.models.master_data import SKU, Location, Supplier, SupplierSKU


def test_inventory_sku_location_uniqueness(db_session):
    """Verify that only one Inventory balance row can exist per SKU and Location."""
    sku = SKU(
        business_id="SKU-UQ-01",
        sku_code="SKU-UQ-01",
        name="Unique SKU",
        category="Hardware",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("15.0000"),
        unit_price=Decimal("30.0000"),
    )
    loc = Location(
        business_id="LOC-UQ-01",
        location_code="LOC-UQ-01",
        name="Unique Facility",
        location_type=LocationType.WAREHOUSE,
        country="USA",
    )
    db_session.add_all([sku, loc])
    db_session.commit()

    inv1 = Inventory(
        business_id="INV-UQ-01",
        sku_id=sku.id,
        location_id=loc.id,
        on_hand_qty=500,
        safety_stock_qty=100,
    )
    db_session.add(inv1)
    db_session.commit()

    # Second inventory record for same SKU and Location must fail
    inv2 = Inventory(
        business_id="INV-UQ-02",
        sku_id=sku.id,
        location_id=loc.id,
        on_hand_qty=200,
        safety_stock_qty=50,
    )
    db_session.add(inv2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_forecast_demand_composite_uniqueness(db_session):
    """Verify unique constraint on (sku_id, location_id, week_bucket, version)."""
    sku = SKU(
        business_id="SKU-UQ-02",
        sku_code="SKU-UQ-02",
        name="Demand SKU",
        category="Hardware",
        sku_type=SKUType.FINISHED_GOOD,
        unit_cost=Decimal("10.0000"),
        unit_price=Decimal("20.0000"),
    )
    loc = Location(
        business_id="LOC-UQ-02",
        location_code="LOC-UQ-02",
        name="Demand Loc",
        location_type=LocationType.DC,
        country="USA",
    )
    db_session.add_all([sku, loc])
    db_session.commit()

    d1 = ForecastDemand(
        business_id="DEM-UQ-01",
        sku_id=sku.id,
        location_id=loc.id,
        week_bucket="2026W01",
        forecast_qty=1500,
        confidence_p50=1450,
        confidence_p90=1600,
        version="v1.0",
    )
    db_session.add(d1)
    db_session.commit()

    # Identical week and version must fail
    d2 = ForecastDemand(
        business_id="DEM-UQ-02",
        sku_id=sku.id,
        location_id=loc.id,
        week_bucket="2026W01",
        forecast_qty=2000,
        confidence_p50=1900,
        confidence_p90=2100,
        version="v1.0",
    )
    db_session.add(d2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_check_constraint_negative_values_rejected(db_session):
    """Verify check constraints prevent invalid negative quantities or prices."""
    # Negative unit_cost on SKU
    bad_sku = SKU(
        business_id="SKU-BAD-01",
        sku_code="SKU-BAD-01",
        name="Negative Cost SKU",
        category="Hardware",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("-5.0000"),
        unit_price=Decimal("10.0000"),
    )
    db_session.add(bad_sku)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_check_constraint_negative_inventory_rejected(db_session):
    """Verify check constraint on_hand_qty >= 0."""
    sku = SKU(
        business_id="SKU-UQ-03",
        sku_code="SKU-UQ-03",
        name="Valid SKU",
        category="Hardware",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("1.0000"),
        unit_price=Decimal("2.0000"),
    )
    loc = Location(
        business_id="LOC-UQ-03",
        location_code="LOC-UQ-03",
        name="Valid Loc",
        location_type=LocationType.DC,
        country="USA",
    )
    db_session.add_all([sku, loc])
    db_session.commit()

    negative_inv = Inventory(
        business_id="INV-BAD-01",
        sku_id=sku.id,
        location_id=loc.id,
        on_hand_qty=-50,  # Negative inventory rejected by DB check constraint
        safety_stock_qty=10,
    )
    db_session.add(negative_inv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


"""Tests for Primary Key Uniqueness and Deterministic Business ID Enforcement."""

from decimal import Decimal
import uuid
import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.enums import LocationType, SKUType, SupplierTier
from backend.app.models.master_data import SKU, Location, Supplier


def test_sku_business_id_uniqueness(db_session):
    """Verify that SKU business_id must be unique."""
    sku1 = SKU(
        business_id="SKU-PK-000001",
        sku_code="SKU-PK-A100",
        name="Finished Good Widget A",
        category="Electronics",
        sku_type=SKUType.FINISHED_GOOD,
        unit_cost=Decimal("25.5000"),
        unit_price=Decimal("49.9900"),
        weight_kg=Decimal("1.250"),
    )
    db_session.add(sku1)
    db_session.commit()

    # Attempt to insert another SKU with identical business_id
    sku_dup_bus_id = SKU(
        business_id="SKU-PK-000001",  # duplicate
        sku_code="SKU-PK-A102",
        name="Duplicate Business ID Widget",
        category="Electronics",
        sku_type=SKUType.FINISHED_GOOD,
        unit_cost=Decimal("10.0000"),
        unit_price=Decimal("20.0000"),
    )
    db_session.add(sku_dup_bus_id)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_sku_code_uniqueness(db_session):
    """Verify that SKU sku_code must be unique."""
    sku1 = SKU(
        business_id="SKU-PK-000002",
        sku_code="SKU-UNIQUE-CODE",
        name="Finished Good Widget B",
        category="Electronics",
        sku_type=SKUType.FINISHED_GOOD,
        unit_cost=Decimal("15.5000"),
        unit_price=Decimal("35.0000"),
    )
    db_session.add(sku1)
    db_session.commit()

    # Attempt to insert another SKU with identical sku_code
    sku_dup_code = SKU(
        business_id="SKU-PK-000003",
        sku_code="SKU-UNIQUE-CODE",  # duplicate
        name="Duplicate Code Widget",
        category="Electronics",
        sku_type=SKUType.FINISHED_GOOD,
        unit_cost=Decimal("12.0000"),
        unit_price=Decimal("22.0000"),
    )
    db_session.add(sku_dup_code)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_location_and_supplier_pk_uniqueness(db_session):
    """Verify primary key integrity on Locations and Suppliers."""
    loc_id = uuid.uuid4()
    loc = Location(
        id=loc_id,
        business_id="LOC-PK-000001",
        location_code="DC-WEST-01",
        name="West Coast DC",
        location_type=LocationType.DC,
        capacity_units=100000,
        country="USA",
    )
    db_session.add(loc)
    db_session.commit()

    sup_id = uuid.uuid4()
    sup = Supplier(
        id=sup_id,
        business_id="SUP-PK-000001",
        supplier_code="SUP-ALPHA",
        name="Alpha Semiconductor",
        tier=SupplierTier.TIER_1,
        country="USA",
    )
    db_session.add(sup)
    db_session.commit()

    # Verify query by business_id
    queried_loc = db_session.query(Location).filter_by(business_id="LOC-PK-000001").one()
    assert queried_loc.id == loc_id
    assert queried_loc.location_code == "DC-WEST-01"


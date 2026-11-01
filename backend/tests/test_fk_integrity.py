"""Tests for Foreign Key Integrity, Cascades, and Restrict Constraints."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.enums import (
    LocationType,
    PurchaseOrderStatus,
    SKUType,
    SupplierTier,
)
from backend.app.models.inventory import Inventory
from backend.app.models.master_data import SKU, Location, Supplier
from backend.app.models.procurement import PurchaseOrder, PurchaseOrderLine


def test_orphaned_fk_rejection(db_session):
    """Verify that referencing non-existent parent IDs raises an IntegrityError."""
    non_existent_sku_id = uuid.uuid4()
    non_existent_loc_id = uuid.uuid4()

    inv = Inventory(
        business_id="INV-INVALID-01",
        sku_id=non_existent_sku_id,
        location_id=non_existent_loc_id,
        on_hand_qty=100,
        safety_stock_qty=20,
    )
    db_session.add(inv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_po_line_cascade_delete(db_session):
    """Verify that deleting a parent PurchaseOrder cascades to its lines."""
    sup = Supplier(
        business_id="SUP-FK-01",
        supplier_code="SUP-FK-01",
        name="Cascade Supplier",
        tier=SupplierTier.TIER_1,
        country="USA",
    )
    loc = Location(
        business_id="LOC-FK-01",
        location_code="LOC-FK-01",
        name="Receiving Plant",
        location_type=LocationType.PLANT,
        country="USA",
    )
    sku = SKU(
        business_id="SKU-FK-01",
        sku_code="SKU-FK-01",
        name="Component X",
        category="Parts",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("5.0000"),
        unit_price=Decimal("10.0000"),
    )
    db_session.add_all([sup, loc, sku])
    db_session.commit()

    po = PurchaseOrder(
        business_id="PO-FK-TEST-000010",
        po_number="PO-10001-TEST",
        supplier_id=sup.id,
        status=PurchaseOrderStatus.PLACED,
        total_amount=Decimal("5000.00"),
    )
    db_session.add(po)
    db_session.commit()

    line = PurchaseOrderLine(
        business_id="POL-FK-TEST-000010-01",
        po_id=po.id,
        line_number=1,
        sku_id=sku.id,
        destination_location_id=loc.id,
        ordered_qty=500,
        received_qty=0,
        unit_cost=Decimal("10.0000"),
        promised_delivery_date=datetime.now(timezone.utc),
    )
    db_session.add(line)
    db_session.commit()

    assert db_session.query(PurchaseOrderLine).filter_by(po_id=po.id).count() == 1

    # Delete parent PO
    db_session.delete(po)
    db_session.commit()

    # Child line must be deleted by cascade
    assert db_session.query(PurchaseOrderLine).filter_by(po_id=po.id).count() == 0


def test_master_data_restrict_on_delete(db_session):
    """Verify that deleting a SKU referenced in active orders is restricted."""
    sup = Supplier(
        business_id="SUP-FK-02",
        supplier_code="SUP-FK-02",
        name="Restrict Supplier",
        tier=SupplierTier.TIER_2,
        country="USA",
    )
    loc = Location(
        business_id="LOC-FK-02",
        location_code="LOC-FK-02",
        name="DC South",
        location_type=LocationType.DC,
        country="USA",
    )
    sku = SKU(
        business_id="SKU-FK-02",
        sku_code="SKU-FK-02",
        name="Restricted SKU",
        category="Parts",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("12.0000"),
        unit_price=Decimal("24.0000"),
    )
    db_session.add_all([sup, loc, sku])
    db_session.commit()

    po = PurchaseOrder(
        business_id="PO-FK-TEST-000020",
        po_number="PO-20002-TEST",
        supplier_id=sup.id,
        status=PurchaseOrderStatus.PLACED,
        total_amount=Decimal("1200.00"),
    )
    db_session.add(po)
    db_session.commit()

    line = PurchaseOrderLine(
        business_id="POL-FK-TEST-000020-01",
        po_id=po.id,
        line_number=1,
        sku_id=sku.id,
        destination_location_id=loc.id,
        ordered_qty=100,
        received_qty=0,
        unit_cost=Decimal("12.0000"),
        promised_delivery_date=datetime.now(timezone.utc),
    )
    db_session.add(line)
    db_session.commit()

    # Deleting SKU must be rejected because po_lines has ondelete=RESTRICT
    db_session.delete(sku)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


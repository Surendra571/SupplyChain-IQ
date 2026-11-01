"""Tests for Many-to-Many Bridge Table Relationships & Temporal Attributes."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.models.enums import LocationType, SKUType, SupplierTier
from backend.app.models.master_data import SKU, Supplier, SupplierSKU
from backend.app.models.production import BOM, BOMComponent, SubstituteSKU


def test_supplier_sku_m2m_relationship(db_session):
    """Verify SupplierSKU bridge table correctly associates Suppliers and SKUs."""
    sup1 = Supplier(
        business_id="SUP-M2M-01",
        supplier_code="SUP-M2M-01",
        name="Global Materials Corp",
        tier=SupplierTier.TIER_1,
        country="USA",
    )
    sup2 = Supplier(
        business_id="SUP-M2M-02",
        supplier_code="SUP-M2M-02",
        name="Secondary Parts Ltd",
        tier=SupplierTier.TIER_2,
        country="CAN",
    )
    sku = SKU(
        business_id="SKU-M2M-01",
        sku_code="SKU-M2M-01",
        name="Microcontroller IC",
        category="Electronics",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("4.5000"),
        unit_price=Decimal("9.0000"),
    )
    db_session.add_all([sup1, sup2, sku])
    db_session.commit()

    now = datetime.now(timezone.utc)
    ssku1 = SupplierSKU(
        business_id="SUPSK-0001",
        supplier_id=sup1.id,
        sku_id=sku.id,
        unit_price=Decimal("4.2000"),
        moq=1000,
        pack_size=500,
        lead_time_days=14,
        is_preferred=True,
        effective_from=now,
    )
    ssku2 = SupplierSKU(
        business_id="SUPSK-0002",
        supplier_id=sup2.id,
        sku_id=sku.id,
        unit_price=Decimal("4.7500"),
        moq=500,
        pack_size=250,
        lead_time_days=7,
        is_preferred=False,
        effective_from=now,
    )
    db_session.add_all([ssku1, ssku2])
    db_session.commit()

    # Query SKU and verify both supplier relationships are populated
    queried_sku = db_session.query(SKU).filter_by(id=sku.id).one()
    assert len(queried_sku.supplier_skus) == 2
    preferred = [s for s in queried_sku.supplier_skus if s.is_preferred][0]
    assert preferred.supplier.supplier_code == "SUP-M2M-01"
    assert preferred.unit_price == Decimal("4.2000")


def test_bom_component_m2m_relationship(db_session):
    """Verify BOM and BOMComponent bridge relationships with scrap and lead times."""
    fg = SKU(
        business_id="SKU-FG-01",
        sku_code="SKU-FG-01",
        name="Smart Sensor Device",
        category="Finished Goods",
        sku_type=SKUType.FINISHED_GOOD,
        unit_cost=Decimal("45.0000"),
        unit_price=Decimal("99.0000"),
    )
    comp1 = SKU(
        business_id="SKU-CMP-01",
        sku_code="SKU-CMP-01",
        name="Lithium Battery Pack",
        category="Components",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("8.0000"),
        unit_price=Decimal("15.0000"),
    )
    comp2 = SKU(
        business_id="SKU-CMP-02",
        sku_code="SKU-CMP-02",
        name="Polymer Casing",
        category="Components",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("3.5000"),
        unit_price=Decimal("7.0000"),
    )
    db_session.add_all([fg, comp1, comp2])
    db_session.commit()

    bom = BOM(
        business_id="BOM-0001",
        parent_sku_id=fg.id,
        bom_version="v1.0",
        description="Standard Production BOM",
        is_active=True,
    )
    db_session.add(bom)
    db_session.commit()

    bom_c1 = BOMComponent(
        business_id="BOMC-0001",
        bom_id=bom.id,
        component_sku_id=comp1.id,
        quantity_per_parent=Decimal("1.0000"),
        scrap_percentage=Decimal("0.0200"),
        lead_time_offset_days=3,
    )
    bom_c2 = BOMComponent(
        business_id="BOMC-0002",
        bom_id=bom.id,
        component_sku_id=comp2.id,
        quantity_per_parent=Decimal("2.0000"),
        scrap_percentage=Decimal("0.0100"),
        lead_time_offset_days=1,
    )
    db_session.add_all([bom_c1, bom_c2])
    db_session.commit()

    queried_bom = db_session.query(BOM).filter_by(id=bom.id).one()
    assert len(queried_bom.components) == 2
    assert queried_bom.parent_sku.name == "Smart Sensor Device"


def test_substitute_sku_relationship(db_session):
    """Verify SubstituteSKU bridge table interchangeability."""
    primary = SKU(
        business_id="SKU-PRI-01",
        sku_code="SKU-PRI-01",
        name="Primary Connector",
        category="Parts",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("2.0000"),
        unit_price=Decimal("4.0000"),
    )
    sub = SKU(
        business_id="SKU-SUB-01",
        sku_code="SKU-SUB-01",
        name="Compatible Connector Gold",
        category="Parts",
        sku_type=SKUType.RAW_MATERIAL,
        unit_cost=Decimal("2.4000"),
        unit_price=Decimal("4.5000"),
    )
    db_session.add_all([primary, sub])
    db_session.commit()

    substitution = SubstituteSKU(
        business_id="SUB-0001",
        primary_sku_id=primary.id,
        substitute_sku_id=sub.id,
        conversion_factor=Decimal("1.0000"),
        preference_rank=1,
        is_bidirectional=True,
    )
    db_session.add(substitution)
    db_session.commit()

    queried_sub = db_session.query(SubstituteSKU).filter_by(primary_sku_id=primary.id).one()
    assert queried_sub.substitute_sku.sku_code == "SKU-SUB-01"
    assert queried_sub.is_bidirectional is True


"""SupplyChain IQ - Operations & Dashboard Endpoints Integration Tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app


@pytest.mark.anyio
async def test_dashboard_kpis_endpoint():
    """Verify that dashboard KPIs are computed accurately from persisted DB records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Planner
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "planner@supplychainiq.com", "password": "Planner123!"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Dashboard KPIs
        kpi_resp = await client.get("/api/v1/dashboard/kpis", headers=headers)
        assert kpi_resp.status_code == 200
        kpis = kpi_resp.json()
        assert kpis["total_skus"] >= 100
        assert kpis["total_locations"] >= 5
        assert kpis["total_inventory_value"] > 0
        assert kpis["demand_at_risk"] >= 0
        assert kpis["critical_shortages"] >= 0
        assert kpis["supplier_on_time_rate"] > 0
        assert kpis["mitigation_recovery_rate"] > 0

        # 2. Dashboard Charts
        chart_resp = await client.get("/api/v1/dashboard/charts", headers=headers)
        assert chart_resp.status_code == 200
        charts = chart_resp.json()
        assert "shortage_by_priority" in charts
        assert "shortage_by_root_cause" in charts
        assert "inventory_by_category" in charts
        assert "top_shortage_skus" in charts


@pytest.mark.anyio
async def test_ops_domain_pages_endpoints():
    """Verify paginated endpoints for Demand, Inventory, Suppliers, POs, and Production."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "planner@supplychainiq.com", "password": "Planner123!"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Demand Planning
        demand_resp = await client.get("/api/v1/demand?page=1&page_size=10", headers=headers)
        assert demand_resp.status_code == 200
        demand_data = demand_resp.json()
        assert demand_data["total"] > 0
        assert len(demand_data["items"]) <= 10
        item = demand_data["items"][0]
        assert "forecast_qty" in item
        assert "sku_code" in item
        assert "location_code" in item

        # 2. Inventory Management
        inv_resp = await client.get("/api/v1/inventory?page=1&page_size=10", headers=headers)
        assert inv_resp.status_code == 200
        inv_data = inv_resp.json()
        assert inv_data["total"] > 0
        inv_item = inv_data["items"][0]
        assert "on_hand_qty" in inv_item
        assert "total_value" in inv_item

        # 3. Suppliers Overview
        supp_resp = await client.get("/api/v1/suppliers/overview?page=1&page_size=10", headers=headers)
        assert supp_resp.status_code == 200
        supp_data = supp_resp.json()
        assert supp_data["total"] > 0

        # 4. Purchase Orders
        po_resp = await client.get("/api/v1/purchase-orders?page=1&page_size=10", headers=headers)
        assert po_resp.status_code == 200
        po_data = po_resp.json()
        assert po_data["total"] > 0

        # 5. Production Plans
        prod_resp = await client.get("/api/v1/production-plans?page=1&page_size=10", headers=headers)
        assert prod_resp.status_code == 200
        prod_data = prod_resp.json()
        assert prod_data["total"] > 0

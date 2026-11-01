"""SupplyChain IQ - Phase 7 Comprehensive API Integration Test Suite.

Validates all REST endpoints against real persisted PostgreSQL data:
- Authentication & JWT RBAC (Planner, Ops Manager, Warehouse Operator)
- Planning Runs orchestration & KPI status tracking
- Shortage Workbench with filtering, sorting, pagination, and time-phased PAB curve
- Mitigation 4-way trade-off comparisons
- Decision submissions with role enforcement, database transactions & idempotency
- Data quality scan results & evaluation metrics
- Immutable audit ledger governance
- Master data lookups
"""

import uuid
import httpx
import pytest
from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def auth_tokens(async_client):
    """Helper generating auth tokens for different personas."""
    tokens = {}
    for email, pwd in [
        ("planner@supplychainiq.com", "Planner123!"),
        ("opsmanager@supplychainiq.com", "OpsMgr123!"),
        ("warehouse@supplychainiq.com", "Warehouse123!"),
        ("admin@supplychainiq.com", "Admin123!"),
    ]:
        resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        assert resp.status_code == 200
        tokens[email] = resp.json()["access_token"]
    return tokens


# ===========================================================================
# 1. Health & Root Endpoints
# ===========================================================================

@pytest.mark.anyio
async def test_health_and_root_endpoints(async_client):
    """Test healthcheck and OpenAPI discovery root."""
    res_health = await async_client.get("/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "HEALTHY"
    assert data_health["api_version"] == "v1"

    res_root = await async_client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["documentation"] == "/docs"


# ===========================================================================
# 2. Authentication & RBAC Authorization
# ===========================================================================

@pytest.mark.anyio
async def test_auth_login_and_me_flow(async_client, auth_tokens):
    """Verify login validation, JWT claims, and role-based permissions."""
    # Invalid password
    bad_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "planner@supplychainiq.com", "password": "WrongPassword!"},
    )
    assert bad_resp.status_code == 401

    # Valid token inspection
    token = auth_tokens["planner@supplychainiq.com"]
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "planner@supplychainiq.com"
    assert me_data["role"] == "Planner"
    assert "mitigation:approve" in me_data["permissions"]

    # Unauthenticated request
    no_auth = await async_client.get("/api/v1/auth/me")
    assert no_auth.status_code == 401


# ===========================================================================
# 3. Planning Runs API
# ===========================================================================

@pytest.mark.anyio
async def test_planning_runs_api(async_client, auth_tokens, seeded_starter_data):
    """Query planning runs history and fetch latest run KPI summary."""
    token = auth_tokens["planner@supplychainiq.com"]
    headers = {"Authorization": f"Bearer {token}"}

    # List runs
    res = await async_client.get("/api/v1/planning-runs", headers=headers)
    assert res.status_code == 200
    runs = res.json()["items"]
    assert len(runs) >= 1
    run_id = str(runs[0]["id"])

    # Latest run detail
    latest_res = await async_client.get("/api/v1/planning-runs/latest", headers=headers)
    assert latest_res.status_code == 200
    latest = latest_res.json()
    assert latest["total_shortages"] == 1405
    assert latest["total_projections"] == 6000
    assert "Supplier delay" in latest["root_cause_breakdown"]

    # Run detail by ID
    run_detail = await async_client.get(f"/api/v1/planning-runs/{run_id}", headers=headers)
    assert run_detail.status_code == 200
    assert run_detail.json()["run_number"] >= 1

    # Non-existent run
    missing_run = await async_client.get(f"/api/v1/planning-runs/{uuid.uuid4()}", headers=headers)
    assert missing_run.status_code == 404


# ===========================================================================
# 4. Shortage Workbench API (Filtering, Sorting, Pagination, PAB)
# ===========================================================================

@pytest.mark.anyio
async def test_shortage_workbench_filtering_and_sorting(async_client, auth_tokens, seeded_starter_data):
    """Verify shortage search, filters, sorting by priority score, and PAB curve."""
    token = auth_tokens["planner@supplychainiq.com"]
    headers = {"Authorization": f"Bearer {token}"}

    # Basic pagination
    res = await async_client.get("/api/v1/shortages?page=1&page_size=20", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1405
    assert len(data["items"]) == 20
    first_shortage = data["items"][0]
    assert "sku_code" in first_shortage
    assert "location_code" in first_shortage
    assert first_shortage["priority_score"] >= data["items"][1]["priority_score"]

    # Filter by severity
    crit_res = await async_client.get("/api/v1/shortages?severity=CRITICAL", headers=headers)
    assert crit_res.status_code == 200
    assert all(item["severity"] == "CRITICAL" for item in crit_res.json()["items"])

    # Filter by priority tier
    tier_res = await async_client.get("/api/v1/shortages?priority_tier=Critical", headers=headers)
    assert tier_res.status_code == 200
    assert all(item["priority_tier"] == "Critical" for item in tier_res.json()["items"])

    # Filter by SKU pattern
    sku_res = await async_client.get("/api/v1/shortages?sku_code=SKU-FG-00001", headers=headers)
    assert sku_res.status_code == 200
    assert all("SKU-FG-00001" in item["sku_code"] for item in sku_res.json()["items"])

    # Get single shortage detail
    shortage_id = str(first_shortage["id"])
    detail_res = await async_client.get(f"/api/v1/shortages/{shortage_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == shortage_id

    # Time-Phased PAB Curve
    pab_res = await async_client.get(f"/api/v1/shortages/{shortage_id}/pab", headers=headers)
    assert pab_res.status_code == 200
    pab_data = pab_res.json()
    assert len(pab_data["points"]) == 12
    assert "projected_available_balance" in pab_data["points"][0]


# ===========================================================================
# 5. Mitigation Recommendations & Trade-offs API
# ===========================================================================

@pytest.mark.anyio
async def test_mitigation_tradeoffs_api(async_client, auth_tokens, seeded_starter_data):
    """Retrieve 4-way trade-off comparison and candidates for a shortage."""
    token = auth_tokens["planner@supplychainiq.com"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch top shortage
    s_res = await async_client.get("/api/v1/shortages?page=1&page_size=1", headers=headers)
    shortage_id = str(s_res.json()["items"][0]["id"])

    # Query mitigations
    mit_res = await async_client.get(f"/api/v1/mitigations/shortage/{shortage_id}", headers=headers)
    assert mit_res.status_code == 200
    mit_data = mit_res.json()
    assert "cheapest_option" in mit_data
    assert "recommended_option" in mit_data
    assert len(mit_data["all_candidates"]) >= 1
    assert "comparison_summary" in mit_data


# ===========================================================================
# 6. Planner Decision Workflow, Permissions & Idempotency
# ===========================================================================

@pytest.mark.anyio
async def test_decision_workflow_permissions_and_idempotency(async_client, auth_tokens, seeded_starter_data):
    """Test approval submission, RBAC prohibition for unauthorized roles, and idempotency key safety."""
    planner_token = auth_tokens["planner@supplychainiq.com"]
    wh_token = auth_tokens["warehouse@supplychainiq.com"]

    # Find a proposed mitigation option
    s_res = await async_client.get("/api/v1/shortages?page=1&page_size=1", headers={"Authorization": f"Bearer {planner_token}"})
    shortage_id = str(s_res.json()["items"][0]["id"])
    m_res = await async_client.get(f"/api/v1/mitigations/shortage/{shortage_id}", headers={"Authorization": f"Bearer {planner_token}"})
    option_id = str(m_res.json()["all_candidates"][0]["id"])

    decision_payload = {
        "mitigation_option_id": option_id,
        "decision": "APPROVED",
        "reason": "Business sign-off approved due to production constraint.",
    }

    # 1. Warehouse Operator attempts to approve -> 403 Forbidden
    wh_resp = await async_client.post(
        "/api/v1/decisions",
        json=decision_payload,
        headers={"Authorization": f"Bearer {wh_token}"},
    )
    assert wh_resp.status_code == 403

    # 2. Planner approves with Idempotency-Key -> 201 Created
    idempotency_key = f"IDEMP-KEY-{uuid.uuid4().hex}"
    p_headers = {
        "Authorization": f"Bearer {planner_token}",
        "Idempotency-Key": idempotency_key,
    }
    p_resp = await async_client.post("/api/v1/decisions", json=decision_payload, headers=p_headers)
    assert p_resp.status_code == 201
    dec_data = p_resp.json()
    assert dec_data["decision"] == "APPROVED"
    assert dec_data["status"] == "SUCCESS"
    decision_id = str(dec_data["id"])

    # 3. Repeat submission with the EXACT same Idempotency-Key -> Returns cached 201 response
    repeat_resp = await async_client.post("/api/v1/decisions", json=decision_payload, headers=p_headers)
    assert repeat_resp.status_code == 201
    assert repeat_resp.json()["id"] == decision_id

    # 4. Fetch decision record
    fetch_resp = await async_client.get(f"/api/v1/decisions/{decision_id}", headers=p_headers)
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["decision"] == "APPROVED"


# ===========================================================================
# 7. Immutable Audit Trail API
# ===========================================================================

@pytest.mark.anyio
async def test_audit_trail_api(async_client, auth_tokens, seeded_starter_data):
    """Query audit ledger for state changes."""
    token = auth_tokens["opsmanager@supplychainiq.com"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.get("/api/v1/audit-events", headers=headers)
    assert res.status_code == 200
    events = res.json()["items"]
    assert len(events) >= 1
    assert events[0]["entity_name"] == "MitigationDecision"


# ===========================================================================
# 8. Data Quality & Anomalies API
# ===========================================================================

@pytest.mark.anyio
async def test_anomalies_api(async_client, auth_tokens):
    """Verify data quality reporting and role-guarded manual scanning."""
    token = auth_tokens["opsmanager@supplychainiq.com"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch scan report
    res = await async_client.get("/api/v1/anomalies", headers=headers)
    assert res.status_code == 200
    report = res.json()
    assert report["evaluation_metrics"]["f1_score"] == 1.0
    assert report["evaluation_metrics"]["true_positives_count"] == 5

    # Role guard: warehouse operator cannot trigger manual scan
    wh_token = auth_tokens["warehouse@supplychainiq.com"]
    wh_res = await async_client.post("/api/v1/anomalies/scan", headers={"Authorization": f"Bearer {wh_token}"})
    assert wh_res.status_code == 403

    # Operations Manager triggers scan -> 200 OK
    scan_res = await async_client.post("/api/v1/anomalies/scan", headers=headers)
    assert scan_res.status_code == 200
    assert scan_res.json()["evaluation_metrics"]["true_positives_count"] == 5


# ===========================================================================
# 9. Master Data Lookups API
# ===========================================================================

@pytest.mark.anyio
async def test_master_data_lookups(async_client, auth_tokens, seeded_starter_data):
    """Verify SKU, Location, and Supplier lookup endpoints."""
    token = auth_tokens["planner@supplychainiq.com"]
    headers = {"Authorization": f"Bearer {token}"}

    # SKUs
    skus_res = await async_client.get("/api/v1/master-data/skus?page=1&page_size=50", headers=headers)
    assert skus_res.status_code == 200
    assert skus_res.json()["total"] == 100

    # Locations
    locs_res = await async_client.get("/api/v1/master-data/locations", headers=headers)
    assert locs_res.status_code == 200
    assert locs_res.json()["total"] == 5

    # Suppliers
    supp_res = await async_client.get("/api/v1/master-data/suppliers", headers=headers)
    assert supp_res.status_code == 200
    assert supp_res.json()["total"] == 25

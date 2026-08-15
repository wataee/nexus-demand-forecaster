import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_root_and_dashboard(client):
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "Demand Forecasting API" in r_root.json()["message"]

    r_dash = client.get("/dashboard")
    assert r_dash.status_code == 200
    assert "Nexus" in r_dash.text
    assert "DemandForecaster" in r_dash.text


def test_sku_management_flow(client):
    payload = {
        "sku_id": "SKU-RAD-881",
        "description": "Aluminum Core Radiator 2.0L",
        "category": "Cooling Systems",
        "lead_time_days": 75,
        "unit_cost": 89.0,
        "minimum_order_qty": 40,
        "supplier_name": "Thermal Tech Supplies",
    }
    # Create SKU
    r_create = client.post("/api/v1/skus", json=payload)
    assert r_create.status_code == 201
    assert r_create.json()["sku_id"] == "SKU-RAD-881"

    # List SKUs
    r_list = client.get("/api/v1/skus")
    assert r_list.status_code == 200
    assert any(s["sku_id"] == "SKU-RAD-881" for s in r_list.json())

    # Get Single SKU
    r_get = client.get("/api/v1/skus/SKU-RAD-881")
    assert r_get.status_code == 200
    assert r_get.json()["unit_cost"] == 89.0


def test_sales_import(client):
    payload = {
        "records": [
            {"sku_id": "SKU-BRK-109", "date": "2024-01-15", "quantity": 120.0, "revenue": 5400.0},
            {"sku_id": "SKU-BRK-109", "date": "2024-02-15", "quantity": 135.0, "revenue": 6075.0},
        ]
    }
    res = client.post("/api/v1/sales/import", json=payload)
    assert res.status_code == 200
    assert res.json()["imported_count"] == 2


def test_forecast_and_optimization(client):
    # Ad-hoc forecast
    f_res = client.post("/api/v1/forecasts/generate", json={"sku_id": "SKU-BRK-109", "horizon_periods": 6})
    assert f_res.status_code == 200
    assert f_res.json()["generated_points"] == 6

    # Inventory optimization
    opt_res = client.post("/api/v1/inventory/optimize")
    assert opt_res.status_code == 200
    assert opt_res.json()["status"] == "optimized"


def test_metrics_and_jobs(client):
    # Evaluation metrics
    m_res = client.get("/api/v1/metrics/evaluation")
    assert m_res.status_code == 200
    assert len(m_res.json()) >= 1
    assert "wape" in m_res.json()[0]

    # Background job dispatch and poll
    j_res = client.post("/api/v1/jobs/forecast")
    assert j_res.status_code == 200
    job_id = j_res.json()["job_id"]

    poll_res = client.get(f"/api/v1/jobs/{job_id}")
    assert poll_res.status_code == 200
    assert poll_res.json()["status"] == "completed"

"""Integration Tests for FastAPI Upgrades: Data Quality, Forecasting, and RAG Triage."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from scripts.seed_data import seed_database
from pipeline.run import run_pipeline

@pytest.fixture(scope="module")
def upgrade_client(tmp_path_factory):
    test_db = tmp_path_factory.mktemp("upgrades") / "test_upgrades.db"
    settings.DATABASE_PATH = str(test_db)
    seed_database(db_path=test_db)
    # Run pipeline once to populate clean layer and data quality metadata
    run_pipeline(db_path=test_db)
    
    with TestClient(app) as c:
        yield c

def test_api_data_quality_endpoint(upgrade_client):
    res = upgrade_client.get("/data-quality")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["total_records"] > 0
    assert "SYNTHETIC" in data["disclaimer"]

def test_api_data_quality_runs(upgrade_client):
    res = upgrade_client.get("/data-quality/runs")
    assert res.status_code == 200
    runs = res.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1
    assert "run_id" in runs[0]

def test_api_data_quality_run_detail(upgrade_client):
    # Fetch first run_id
    runs = upgrade_client.get("/data-quality/runs").json()
    first_run_id = runs[0]["run_id"]
    
    res = upgrade_client.get(f"/data-quality/runs/{first_run_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["run"]["run_id"] == first_run_id
    assert "quality_report" in detail

def test_api_data_quality_run_not_found(upgrade_client):
    res = upgrade_client.get("/data-quality/runs/NON_EXISTENT_RUN_999")
    assert res.status_code == 404

def test_api_forecast_failure_rate(upgrade_client):
    res = upgrade_client.get("/forecast?target=failure_rate&horizon=5")
    assert res.status_code == 200
    data = res.json()
    assert data["target"] == "failure_rate"
    assert data["status"] == "SUCCESS"
    assert len(data["forecast"]) == 5
    assert len(data["historical"]) > 0

def test_api_forecast_incident_volume(upgrade_client):
    res = upgrade_client.get("/forecast?target=incident_volume&horizon=3")
    assert res.status_code == 200
    data = res.json()
    assert data["target"] == "incident_volume"
    assert len(data["forecast"]) == 3

def test_api_forecast_invalid_target(upgrade_client):
    res = upgrade_client.get("/forecast?target=invalid_target_xyz")
    assert res.status_code == 422

def test_api_rag_triage_with_incident(upgrade_client):
    payload = {"incident_id": "INC-2026-1001", "top_k": 3}
    res = upgrade_client.post("/triage/rag", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == "INC-2026-1001"
    assert len(data["empirical_facts"]) > 0
    assert len(data["citations"]) > 0
    assert data["refusal"] is False
    assert data["confidence"] > 0.40

def test_api_rag_triage_refusal_guardrail(upgrade_client):
    payload = {"query": "completely unrelated query about ancient roman architecture", "min_score": 0.15}
    res = upgrade_client.post("/triage/rag", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["refusal"] is True
    assert "Refusal" in data["summary"]

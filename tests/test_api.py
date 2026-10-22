"""
Integration Tests for SyncOps Assistant REST API Endpoints.
Uses FastAPI TestClient and isolated temporary SQLite databases.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from scripts.seed_data import seed_database

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # Set isolated temporary database for API tests
    test_db = tmp_path_factory.mktemp("data") / "test_api.db"
    settings.DATABASE_PATH = str(test_db)
    seed_database(db_path=test_db)
    
    with TestClient(app) as c:
        yield c

def test_api_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert "customers" in data["record_counts"]
    assert data["record_counts"]["customers"] > 0
    assert "SYNTHETIC" in data["disclosure"]

def test_api_kpis(client):
    response = client.get("/kpis")
    assert response.status_code == 200
    data = response.json()
    assert "sync_success_rate" in data
    assert "recovery_rate" in data
    assert "time_to_recover" in data
    assert "repeat_failure_rate" in data
    assert "sync_related_support_tickets" in data
    assert "self_service_resolution_rate" in data
    assert "adoption_rate" in data
    assert data["disclosure"] == "SYNTHETIC_DATA_ONLY"

def test_api_kpis_with_window(client):
    response = client.get("/kpis?window_hours=24")
    assert response.status_code == 200
    data = response.json()
    assert data["window_hours"] == 24

def test_api_list_incidents(client):
    response = client.get("/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "severity" in data[0]

def test_api_filter_incidents_by_severity(client):
    response = client.get("/incidents?severity=SEV1")
    assert response.status_code == 200
    data = response.json()
    for inc in data:
        assert inc["severity"] == "SEV1"

def test_api_get_incident_detail_success(client):
    response = client.get("/incidents/INC-2026-1001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "INC-2026-1001"
    assert "cohort_telemetry" in data
    assert "associated_tickets" in data

def test_api_get_incident_not_found(client):
    response = client.get("/incidents/NON_EXISTENT_INCIDENT_999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_api_invalid_query_parameter_validation(client):
    # limit must be >= 1 and <= 200
    response = client.get("/incidents?limit=9999")
    assert response.status_code == 422

def test_api_prometheus_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "syncops_http_requests_total" in text
    assert "syncops_http_request_duration_seconds" in text

def test_api_triage_endpoint(client):
    payload = {"incident_id": "INC-2026-1001", "force_fallback": True}
    response = client.post("/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "INC-2026-1001"
    assert data["analysis_mode"] == "deterministic_fallback"
    assert len(data["evidence"]) > 0
    assert len(data["runbook_references"]) > 0
    assert 0.0 <= data["confidence"] <= 1.0

"""
Unit Tests for Incident Data Access and Filtering Queries.
"""

import sqlite3
import pytest
from app.incidents import list_incidents, get_incident_by_id
from scripts.seed_data import seed_database

@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("incidents") / "inc_test.db"
    seed_database(db_path=db_file)
    return db_file

def test_list_all_incidents(seeded_db):
    conn = sqlite3.connect(str(seeded_db))
    conn.row_factory = sqlite3.Row
    incs = list_incidents(conn)
    conn.close()
    assert len(incs) >= 5

def test_list_incidents_filter_status(seeded_db):
    conn = sqlite3.connect(str(seeded_db))
    conn.row_factory = sqlite3.Row
    investigating = list_incidents(conn, status="INVESTIGATING")
    resolved = list_incidents(conn, status="RESOLVED")
    conn.close()

    assert all(i["status"] == "INVESTIGATING" for i in investigating)
    assert all(i["status"] == "RESOLVED" for i in resolved)

def test_list_incidents_pagination(seeded_db):
    conn = sqlite3.connect(str(seeded_db))
    conn.row_factory = sqlite3.Row
    page1 = list_incidents(conn, limit=2, offset=0)
    page2 = list_incidents(conn, limit=2, offset=2)
    conn.close()

    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0]["id"] != page2[0]["id"]

def test_get_incident_by_id_with_telemetry(seeded_db):
    conn = sqlite3.connect(str(seeded_db))
    conn.row_factory = sqlite3.Row
    inc = get_incident_by_id(conn, "INC-2026-1001")
    conn.close()

    assert inc is not None
    assert inc["id"] == "INC-2026-1001"
    assert "cohort_telemetry" in inc
    assert inc["cohort_telemetry"]["cohort"] == "iOS-Production"
    assert inc["cohort_telemetry"]["total_events_sampled"] > 0

def test_get_non_existent_incident(seeded_db):
    conn = sqlite3.connect(str(seeded_db))
    conn.row_factory = sqlite3.Row
    inc = get_incident_by_id(conn, "INVALID_ID_999")
    conn.close()
    assert inc is None

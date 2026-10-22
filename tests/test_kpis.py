"""
Unit Tests for Customer-Experience KPIs and Edge Cases.
Validates pure calculation formulas, zero denominators, and database query logic.
"""

import pytest
import sqlite3
from app.kpis import (
    calculate_sync_success_rate,
    calculate_recovery_rate,
    calculate_time_to_recover,
    calculate_repeat_failure_rate,
    calculate_sync_related_support_tickets,
    calculate_self_service_resolution_rate,
    calculate_adoption_rate,
    compute_all_kpis,
)
from app.database import init_db
from scripts.seed_data import seed_database

def test_kpi_sync_success_rate_normal():
    res = calculate_sync_success_rate(95, 100)
    assert res["value"] == 95.0
    assert res["unit"] == "%"
    assert res["sample_size"] == 100

def test_kpi_sync_success_rate_zero_denominator():
    res = calculate_sync_success_rate(0, 0)
    assert res["value"] == 0.0
    assert res["sample_size"] == 0

def test_kpi_sync_success_rate_all_failures():
    res = calculate_sync_success_rate(0, 50)
    assert res["value"] == 0.0

def test_kpi_sync_success_rate_all_successes():
    res = calculate_sync_success_rate(50, 50)
    assert res["value"] == 100.0

def test_kpi_recovery_rate_normal():
    res = calculate_recovery_rate(4, 5)
    assert res["value"] == 80.0
    assert res["numerator"] == 4
    assert res["denominator"] == 5

def test_kpi_recovery_rate_zero_denominator():
    res = calculate_recovery_rate(0, 0)
    assert res["value"] == 0.0
    assert res["sample_size"] == 0

def test_kpi_time_to_recover_normal():
    res = calculate_time_to_recover(120.0, 2)
    assert res["value"] == 60.0
    assert res["unit"] == "minutes"

def test_kpi_time_to_recover_zero_denominator():
    res = calculate_time_to_recover(0.0, 0)
    assert res["value"] == 0.0

def test_kpi_repeat_failure_rate_normal():
    res = calculate_repeat_failure_rate(15, 60)
    assert res["value"] == 25.0

def test_kpi_repeat_failure_rate_zero_denominator():
    res = calculate_repeat_failure_rate(0, 0)
    assert res["value"] == 0.0

def test_kpi_sync_related_support_tickets_normal():
    res = calculate_sync_related_support_tickets(25, 100)
    assert res["value"] == 25
    assert res["ticket_to_failure_ratio"] == 25.0

def test_kpi_sync_related_support_tickets_zero_denominator():
    res = calculate_sync_related_support_tickets(0, 0)
    assert res["value"] == 0
    assert res["ticket_to_failure_ratio"] == 0.0

def test_kpi_self_service_resolution_rate_normal():
    res = calculate_self_service_resolution_rate(40, 100)
    assert res["value"] == 40.0

def test_kpi_self_service_resolution_rate_zero_denominator():
    res = calculate_self_service_resolution_rate(0, 0)
    assert res["value"] == 0.0

def test_kpi_adoption_rate_normal():
    res = calculate_adoption_rate(8000, 10000, 40000)
    assert res["value"] == 80.0
    assert res["total_registered_users"] == 40000

def test_kpi_adoption_rate_zero_denominator():
    res = calculate_adoption_rate(0, 0, 0)
    assert res["value"] == 0.0

def test_compute_all_kpis_with_seeded_db(tmp_path):
    db_file = tmp_path / "test_kpis.db"
    seed_database(db_path=db_file)
    
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    kpis = compute_all_kpis(conn, window_hours=None)
    conn.close()

    assert kpis["sync_success_rate"]["sample_size"] > 0
    assert 0.0 <= kpis["sync_success_rate"]["value"] <= 100.0
    assert kpis["recovery_rate"]["sample_size"] > 0
    assert kpis["time_to_recover"]["value"] >= 0.0
    assert kpis["adoption_rate"]["value"] > 0.0
    assert kpis["disclosure"] == "SYNTHETIC_DATA_ONLY"

def test_compute_all_kpis_empty_db(tmp_path):
    db_file = tmp_path / "empty.db"
    init_db(db_file)
    
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    kpis = compute_all_kpis(conn)
    conn.close()

    assert kpis["sync_success_rate"]["value"] == 0.0
    assert kpis["recovery_rate"]["value"] == 0.0
    assert kpis["time_to_recover"]["value"] == 0.0
    assert kpis["repeat_failure_rate"]["value"] == 0.0
    assert kpis["sync_related_support_tickets"]["value"] == 0
    assert kpis["self_service_resolution_rate"]["value"] == 0.0
    assert kpis["adoption_rate"]["value"] == 0.0

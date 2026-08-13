"""
Unit tests for sea freight module (models, seed data, API endpoints).
海运货物模块单元测试
"""
import os

os.environ["AIR_SIM_ENABLED"] = "false"
os.environ["ROAD_SIM_ENABLED"] = "false"
os.environ["SEA_SIM_ENABLED"] = "false"
os.environ["PORTCONNECT_API_ENABLED"] = "false"
os.environ["EVENT_CLASSIFIER_LEARNING"] = "false"
os.environ["LLM_ENABLED"] = "false"


import json
import pytest

from database import Base, engine, SessionLocal
from sea_freight_models import (
    SeaPort, VesselVisit, SeaContainer, SeaTrackingEvent, SeaException
)
from sea_freight_seed import seed_sea_freight
from risk_calculator import categorize_risk

VALID_EVENT_CODES = {"VAD", "DIS", "CHD", "CHR", "BIO", "AVC", "GTO", "DLV", "DLY", "TEMP"}


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    if session.query(SeaPort).count() == 0:
        seed_sea_freight()
    yield session
    session.close()


def test_ports_seeded(db):
    """Test NZ ports exist."""
    ports = db.query(SeaPort).all()
    assert len(ports) >= 5

    akl = db.query(SeaPort).filter(SeaPort.port_code == "NZAKL").first()
    assert akl is not None
    assert akl.is_nz_port is True


def test_vessel_visits_are_real(db):
    """Test vessel visits come from real PortConnect data."""
    visits = db.query(VesselVisit).all()
    assert len(visits) > 1000

    # Real vessel operators present
    operators = {v.vessel_operator for v in visits if v.vessel_operator}
    assert len(operators) > 5

    # NZ ports only
    for v in visits:
        assert v.port_code in {"NZAKL", "NZTRG", "NZWLG", "NZLYT", "NZTIU"}


def test_containers_iso6346_format(db):
    """Test container numbers follow ISO 6346 format."""
    containers = db.query(SeaContainer).all()
    assert len(containers) > 0

    for c in containers:
        assert len(c.container_number) == 11
        assert c.declared_value_nzd > 0


def test_tracking_events_use_valid_codes(db):
    """Test all tracking events use valid milestone codes."""
    events = db.query(SeaTrackingEvent).all()
    assert len(events) > 0

    for e in events:
        assert e.event_code in VALID_EVENT_CODES, f"Invalid event code: {e.event_code}"
        assert e.timestamp is not None


def test_exceptions_risk_consistency(db):
    """Test sea exceptions risk scores are consistent with the risk categorizer."""
    exceptions = db.query(SeaException).all()
    assert len(exceptions) > 0

    for exc in exceptions:
        assert 0 <= exc.risk_score <= 100
        assert exc.risk_level == categorize_risk(exc.risk_score)
        assert exc.recovery_options is not None
        json.loads(exc.recovery_options)


def test_sea_api_endpoints():
    """Test sea freight API endpoints via FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        resp = client.get("/api/sea/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vessels"]["expected"] >= 0

        resp = client.get("/api/sea/ports")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 5

        resp = client.get("/api/sea/vessels?status=DEPARTED")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

        resp = client.get("/api/sea/containers")
        assert resp.status_code == 200
        assert resp.json()["count"] > 0

        cn = resp.json()["containers"][0]["container_number"]
        resp = client.get(f"/api/sea/containers/{cn}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["container_number"] == cn
        assert "events" in detail
        assert "exceptions" in detail

        resp = client.get("/api/sea/containers/MSCU9999999")
        assert resp.status_code == 404

        resp = client.get("/api/sea/exceptions")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

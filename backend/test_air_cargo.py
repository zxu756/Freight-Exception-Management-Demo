"""
Unit tests for air cargo module (models, seed data, API endpoints).
空运货物模块单元测试
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
from datetime import datetime

from database import Base, engine, SessionLocal
from air_cargo_models import (
    Airport, AirFlight, AirWaybill, AirTrackingEvent, AirCustomsInspection, AirException
)
from air_cargo_seed import seed_air_cargo
from risk_calculator import categorize_risk

VALID_EVENT_CODES = {"FNA", "BKD", "RCS", "DEP", "ARR", "MNF", "CDZ", "CCD", "NFD", "OFF", "AWD", "DLV", "DLY", "DIS"}
VALID_ROUTE_TYPES = {"domestic", "international", "transshipment"}


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    if session.query(Airport).count() == 0:
        seed_air_cargo()
    yield session
    session.close()


def test_airports_seeded(db):
    """Test airports contain NZ domestic network and international gateways."""
    nz = db.query(Airport).filter(Airport.country == "New Zealand").all()
    intl = db.query(Airport).filter(Airport.region == "international").all()

    assert len(nz) >= 14
    assert len(intl) >= 15

    akl = db.query(Airport).filter(Airport.iata_code == "AKL").first()
    assert akl is not None
    assert akl.is_nz_gateway is True


def test_flights_seeded(db):
    """Test flights exist with both belly cargo and freighters."""
    flights = db.query(AirFlight).all()
    assert len(flights) >= 20

    freighters = db.query(AirFlight).filter(AirFlight.is_freighter == True).all()
    assert len(freighters) >= 3

    for f in flights:
        assert f.origin_airport != f.destination_airport
        assert 0 <= f.loaded_pct <= 100


def test_waybills_seeded(db):
    """Test waybills cover domestic, international and transshipment routes."""
    for route_type in VALID_ROUTE_TYPES:
        count = db.query(AirWaybill).filter(AirWaybill.route_type == route_type).count()
        assert count > 0, f"No waybills for route type: {route_type}"

    waybills = db.query(AirWaybill).all()
    for w in waybills:
        assert w.awb_number.startswith("086-")
        assert w.chargeable_weight_kg > 0
        assert w.declared_value_nzd > 0


def test_tracking_events_use_valid_imp_codes(db):
    """Test all tracking events use valid Cargo IMP milestone codes."""
    events = db.query(AirTrackingEvent).all()
    assert len(events) > 0

    for e in events:
        assert e.event_code in VALID_EVENT_CODES, f"Invalid event code: {e.event_code}"
        assert e.timestamp is not None


def test_exceptions_risk_consistency(db):
    """Test air exceptions risk scores are consistent with the risk categorizer."""
    exceptions = db.query(AirException).all()
    assert len(exceptions) > 0

    for exc in exceptions:
        assert 0 <= exc.risk_score <= 100
        assert exc.risk_level == categorize_risk(exc.risk_score)
        assert exc.recovery_options is not None
        json.loads(exc.recovery_options)  # must be valid JSON


def test_customs_inspections_for_imports(db):
    """Test MPI/customs inspections exist for import and food shipments."""
    inspections = db.query(AirCustomsInspection).all()
    assert len(inspections) > 0

    for i in inspections:
        waybill = db.query(AirWaybill).filter(
            AirWaybill.awb_number == i.awb_number
        ).first()
        assert waybill is not None
        assert waybill.route_type != "domestic"


def test_air_api_endpoints():
    """Test air cargo API endpoints via FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        # Dashboard
        resp = client.get("/api/air/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["waybills"]["total"] > 0

        # Airports
        resp = client.get("/api/air/airports")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 29

        # NZ domestic airports only
        resp = client.get("/api/air/airports?region=nz_domestic")
        assert resp.status_code == 200
        assert all(a["region"] == "nz_domestic" for a in resp.json()["airports"])

        # Flights with delay
        resp = client.get("/api/air/flights?status=delayed")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

        # Waybills
        resp = client.get("/api/air/waybills?route_type=international")
        assert resp.status_code == 200
        assert resp.json()["count"] > 0

        # Waybill detail
        awb = resp.json()["waybills"][0]["awb_number"]
        resp = client.get(f"/api/air/waybills/{awb}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["awb_number"] == awb
        assert "events" in detail
        assert "exceptions" in detail

        # 404 for unknown waybill
        resp = client.get("/api/air/waybills/086-99999999")
        assert resp.status_code == 404

        # Exceptions
        resp = client.get("/api/air/exceptions")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

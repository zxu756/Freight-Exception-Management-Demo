"""
Unit tests for road freight module (models, seed data, API endpoints).
陆运货物模块单元测试
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
from road_freight_models import (
    Depot, RoadTrip, RoadConsignment, RoadTrackingEvent, RoadException
)
from road_freight_seed import seed_road_freight
from risk_calculator import categorize_risk

VALID_EVENT_CODES = {"PUP", "LOAD", "DEP", "CKP", "ARR", "FERRY", "UNLD", "POD", "DLY"}
VALID_ROUTE_TYPES = {"line_haul", "regional", "inter_island"}


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    if session.query(Depot).count() == 0:
        seed_road_freight()
    yield session
    session.close()


def test_depots_seeded(db):
    """Test depots cover both North and South Island."""
    north = db.query(Depot).filter(Depot.island == "north").count()
    south = db.query(Depot).filter(Depot.island == "south").count()
    assert north >= 10
    assert south >= 10

    akl = db.query(Depot).filter(Depot.depot_code == "AKL").first()
    assert akl is not None
    assert akl.is_hub is True


def test_trips_seeded(db):
    """Test trips exist across vehicle types."""
    trips = db.query(RoadTrip).all()
    assert len(trips) >= 8

    for t in trips:
        assert t.origin_depot != t.destination_depot
        assert 0 <= t.loaded_pct <= 100


def test_consignments_seeded(db):
    """Test consignments cover route types."""
    for route_type in VALID_ROUTE_TYPES:
        count = db.query(RoadConsignment).filter(RoadConsignment.route_type == route_type).count()
        if route_type != "inter_island":
            assert count > 0, f"No consignments for route type: {route_type}"

    consignments = db.query(RoadConsignment).all()
    for c in consignments:
        assert c.consignment_number.startswith("RD-")
        assert c.declared_value_nzd > 0


def test_tracking_events_use_valid_codes(db):
    """Test all tracking events use valid POD milestone codes."""
    events = db.query(RoadTrackingEvent).all()
    assert len(events) > 0

    for e in events:
        assert e.event_code in VALID_EVENT_CODES, f"Invalid event code: {e.event_code}"
        assert e.timestamp is not None


def test_exceptions_risk_consistency(db):
    """Test road exceptions risk scores are consistent with the risk categorizer."""
    exceptions = db.query(RoadException).all()
    assert len(exceptions) > 0

    for exc in exceptions:
        assert 0 <= exc.risk_score <= 100
        assert exc.risk_level == categorize_risk(exc.risk_score)
        assert exc.recovery_options is not None
        json.loads(exc.recovery_options)  # must be valid JSON


def test_road_api_endpoints():
    """Test road freight API endpoints via FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        # Dashboard
        resp = client.get("/api/road/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["consignments"]["total"] > 0

        # Depots
        resp = client.get("/api/road/depots")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 20

        # North Island depots only
        resp = client.get("/api/road/depots?island=north")
        assert resp.status_code == 200
        assert all(d["island"] == "north" for d in resp.json()["depots"])

        # Trips with inter-island filter
        resp = client.get("/api/road/trips?is_inter_island=true")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

        # Consignments
        resp = client.get("/api/road/consignments")
        assert resp.status_code == 200
        assert resp.json()["count"] > 0

        # Consignment detail
        cn = resp.json()["consignments"][0]["consignment_number"]
        resp = client.get(f"/api/road/consignments/{cn}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["consignment_number"] == cn
        assert "events" in detail
        assert "exceptions" in detail

        # 404 for unknown consignment
        resp = client.get("/api/road/consignments/RD-99999999")
        assert resp.status_code == 404

        # Exceptions
        resp = client.get("/api/road/exceptions")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

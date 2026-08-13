"""
Unit tests for the sea freight simulator (real PortConnect schedules + generated cargo).
实时海运模拟器单元测试
"""
import os

os.environ["AIR_SIM_ENABLED"] = "false"
os.environ["ROAD_SIM_ENABLED"] = "false"
os.environ["SEA_SIM_ENABLED"] = "false"
os.environ["PORTCONNECT_API_ENABLED"] = "false"
os.environ["EVENT_CLASSIFIER_LEARNING"] = "false"
os.environ["LLM_ENABLED"] = "false"


import pytest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import sea_freight_simulator as sim_module
from sea_freight_simulator import SeaFreightSimulator
from sea_freight_models import (
    SeaPort, VesselVisit, SeaContainer, SeaTrackingEvent, SeaException
)
from sea_freight_seed import generate_ports


@pytest.fixture()
def sim_db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr(sim_module, "SessionLocal", TestSession)
    db = TestSession()
    generate_ports(db)
    db.commit()
    yield db
    db.close()


@pytest.fixture()
def sim(sim_db):
    s = SeaFreightSimulator(speed=60)
    s._init_counters()
    return s


def test_vessel_visits_loaded_from_real_data(sim, sim_db):
    """Test real PortConnect vessel visits are loaded."""
    sim._load_vessel_visits(sim_db)
    sim_db.commit()

    visits = sim_db.query(VesselVisit).count()
    assert visits > 1000, f"Expected >1000 real vessel visits, got {visits}"

    commercial = sim_db.query(VesselVisit).filter(VesselVisit.vessel_type == "COMMERCIAL").count()
    assert commercial > 1000

    # Real vessels should have known names / operators
    akl = sim_db.query(VesselVisit).filter(VesselVisit.port_code == "NZAKL").count()
    assert akl > 100


def test_containers_generated_against_real_visits(sim, sim_db):
    """Test containers are generated (20-60 per commercial visit)."""
    sim._load_vessel_visits(sim_db)
    sim_db.commit()
    sim._backfill(sim_db)
    sim_db.commit()

    containers = sim_db.query(SeaContainer).all()
    assert len(containers) > 1000

    for c in containers:
        assert len(c.container_number) == 11  # ISO 6346
        assert c.declared_value_nzd > 0
        assert c.gross_weight_kg > 0


def test_container_lifecycle_transitions(sim, sim_db):
    """Test container status derives correctly as sim time advances."""
    sim._load_vessel_visits(sim_db)
    sim_db.commit()
    sim._backfill(sim_db)
    sim_db.commit()

    for _ in range(6):
        sim.sim_now += timedelta(hours=12)
        sim.tick()
    sim_db.commit()

    delivered = sim_db.query(SeaContainer).filter(SeaContainer.current_status == "delivered").count()
    discharged = sim_db.query(SeaContainer).filter(
        SeaContainer.current_status.in_(["discharged", "available", "gate_out", "delivered"])).count()
    assert discharged > 0
    assert delivered > 0

    dis_events = sim_db.query(SeaTrackingEvent).filter(SeaTrackingEvent.event_code == "DIS").count()
    assert dis_events > 0


def test_exceptions_generated(sim, sim_db):
    """Test sea exceptions are generated across multiple types."""
    sim._load_vessel_visits(sim_db)
    sim_db.commit()
    sim._backfill(sim_db)
    sim_db.commit()

    for _ in range(4):
        sim.sim_now += timedelta(hours=12)
        sim.tick()
    sim_db.commit()

    exceptions = sim_db.query(SeaException).all()
    assert len(exceptions) > 0

    types = {e.exception_type for e in exceptions}
    assert "vessel_delay" in types  # vessel delay always injected for some visits

    for e in exceptions:
        assert e.risk_level in ("low", "medium", "high")
        assert 0 <= e.risk_score <= 100


def test_restart_rebuild_continues(sim, sim_db):
    """Test a simulated restart reloads vessels without duplicating."""
    sim._load_vessel_visits(sim_db)
    sim_db.commit()

    count_before = sim_db.query(VesselVisit).count()

    sim2 = SeaFreightSimulator(speed=60)
    sim2._init_counters()
    sim2._load_vessel_visits(sim_db)
    sim_db.commit()

    count_after = sim_db.query(VesselVisit).count()
    assert count_after == count_before


def test_live_endpoint():
    """Test /api/sea/live endpoint returns simulator status."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        resp = client.get("/api/sea/live")
        assert resp.status_code == 200
        data = resp.json()
        assert "simulator" in data
        assert "vessels" in data
        assert "recent_events" in data
        assert "open_exceptions" in data

        resp = client.post("/api/sea/sim/control", json={"action": "set_speed", "speed": 120})
        assert resp.status_code == 200
        assert resp.json()["speed"] == 120.0

        resp = client.post("/api/sea/sim/control", json={"action": "bad_action"})
        assert resp.status_code == 400

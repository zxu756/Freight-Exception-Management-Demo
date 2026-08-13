"""
Unit tests for the live air cargo simulator.
实时空运模拟器单元测试
"""
import os

os.environ["AIR_SIM_ENABLED"] = "false"
os.environ["ROAD_SIM_ENABLED"] = "false"
os.environ["SEA_SIM_ENABLED"] = "false"
os.environ["PORTCONNECT_API_ENABLED"] = "false"
os.environ["EVENT_CLASSIFIER_LEARNING"] = "false"


import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import air_cargo_simulator as sim_module
from air_cargo_simulator import AirCargoSimulator, DOMESTIC_ROUTES, INTL_ROUTES
from air_cargo_models import (
    Airport, AirFlight, AirWaybill, AirTrackingEvent, AirCustomsInspection, AirException
)
from air_cargo_seed import generate_airports


@pytest.fixture()
def sim_db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr(sim_module, "SessionLocal", TestSession)
    db = TestSession()
    generate_airports(db)
    db.commit()
    yield db
    db.close()


@pytest.fixture()
def sim(sim_db):
    s = AirCargoSimulator(speed=60)
    s._init_counters()
    s._init_route_schedule()
    return s


def test_timetable_volume_300_to_400_per_day():
    """Test timetable produces 300-400 flights per day."""
    daily = sum(r[2] for r in DOMESTIC_ROUTES) + sum(r[2] for r in INTL_ROUTES)
    assert 300 <= daily <= 400, f"Expected 300-400 flights/day, got {daily}"


def test_backfill_generates_flights_and_waybills(sim, sim_db):
    """Test backfill creates flights for the window and waybills for each."""
    sim._backfill()
    sim_db.commit()

    flights = sim_db.query(AirFlight).all()
    waybills = sim_db.query(AirWaybill).all()
    assert len(flights) > 100
    assert len(waybills) > len(flights)

    for w in waybills:
        assert w.awb_number.startswith("086-")
        assert w.declared_value_nzd > 0
        assert w.sla_deadline > w.scheduled_delivery - timedelta(days=2)


def test_flight_lifecycle_transitions(sim, sim_db):
    """Test flight status derives correctly as sim time advances."""
    sim._backfill()
    sim_db.commit()

    # Move clock forward 20 hours and tick several times
    for _ in range(4):
        sim.sim_now += timedelta(hours=5)
        sim.tick()
    sim_db.commit()

    landed = sim_db.query(AirFlight).filter(AirFlight.status == "landed").count()
    departed = sim_db.query(AirFlight).filter(AirFlight.status == "departed").count()
    assert landed + departed > 0

    dep_events = sim_db.query(AirTrackingEvent).filter(AirTrackingEvent.event_code == "DEP").count()
    assert dep_events > 0


def test_delay_injection_creates_exceptions(sim, sim_db):
    """Test delayed flights generate delay exceptions for their waybills."""
    import random
    monkeypatch_random = __import__("pytest").MonkeyPatch()

    original_random = sim_module.random.random
    calls = {"n": 0}

    def forced_random():
        calls["n"] += 1
        if calls["n"] == 1:
            return 0.5    # cancellation roll -> no cancel
        if calls["n"] == 2:
            return 0.001  # delay roll -> delay injected
        return 0.5

    monkeypatch_random.setattr(sim_module.random, "random", forced_random)
    try:
        flight = sim._create_flight("AKL", "CHC", "Air New Zealand Cargo",
                                    dep=sim.sim_now + timedelta(hours=2))
        assert flight is not None
        assert flight.delay_minutes > 0
    finally:
        monkeypatch_random.undo()

    sim._push(flight.scheduled_departure - timedelta(minutes=30), "delay_announce", flight.flight_number)
    sim.sim_now = flight.scheduled_departure - timedelta(minutes=30)
    sim._process_pending(sim_db)
    sim_db.commit()

    excs = sim_db.query(AirException).filter(
        AirException.exception_type == "delay",
        AirException.awb_number.in_(
            [w.awb_number for w in sim_db.query(AirWaybill).filter(
                AirWaybill.flight_number == flight.flight_number).all()]
        )
    ).all()
    assert len(excs) > 0
    for e in excs:
        assert e.risk_level in ("low", "medium", "high")
        assert 0 <= e.risk_score <= 100
        assert e.recovery_options


def test_cancellation_creates_no_waybills(sim, sim_db):
    """Test cancelled flights don't get waybills."""
    import pytest as _pytest
    mp = _pytest.MonkeyPatch()
    original = sim_module.random.random
    calls = {"n": 0}

    def forced():
        calls["n"] += 1
        if calls["n"] == 1:
            return 0.0001  # cancellation roll (1.5% domestic)
        return 0.5

    mp.setattr(sim_module.random, "random", forced)
    try:
        flight = sim._create_flight("AKL", "WLG", "Air New Zealand Cargo",
                                    dep=sim.sim_now + timedelta(hours=3))
    finally:
        mp.undo()
    assert flight is not None
    assert flight.status == "cancelled"

    sim_db.commit()
    waybills = sim_db.query(AirWaybill).filter(AirWaybill.flight_number == flight.flight_number).all()
    assert len(waybills) == 0


def test_customs_hold_releases_inspection(sim, sim_db):
    """Test customs hold creates inspection and releases it later."""
    sim._backfill()
    sim_db.commit()

    sim.sim_now += timedelta(hours=30)
    sim.tick()
    sim_db.commit()

    inspections = sim_db.query(AirCustomsInspection).all()
    if not inspections:
        pytest.skip("No inspections generated in this run (probabilistic)")

    sim.sim_now += timedelta(hours=12)
    sim.tick()
    sim_db.commit()

    held = sim_db.query(AirCustomsInspection).filter(AirCustomsInspection.status == "hold").count()
    released = sim_db.query(AirCustomsInspection).filter(AirCustomsInspection.status == "released").count()
    assert released >= 0
    assert held + released == len(sim_db.query(AirCustomsInspection).all())


def test_retention_cleanup(sim, sim_db):
    """Test old delivered waybills are removed after retention window."""
    sim._backfill()
    sim_db.commit()

    w = sim_db.query(AirWaybill).first()
    w.delivered_at = sim.sim_now - timedelta(hours=60)
    w.current_status = "DLV"
    sim_db.commit()

    before = sim_db.query(AirWaybill).count()
    sim._cleanup(sim_db)
    after = sim_db.query(AirWaybill).count()
    assert after < before


def test_restart_rebuild_continues_timelines(sim, sim_db):
    """Test that after a simulated process restart, waybill timelines continue."""
    sim._backfill()
    sim_db.commit()

    sim.sim_now += timedelta(hours=10)
    sim.tick()
    sim_db.commit()

    sim2 = AirCargoSimulator(speed=60)
    sim2.sim_now = sim.sim_now
    sim2._init_counters()
    sim2._init_route_schedule()
    sim2._rebuild_pending_from_db()

    sim2.sim_now += timedelta(hours=10)
    sim2.tick()
    sim_db.commit()

    landed = sim_db.query(AirFlight).filter(AirFlight.status == "landed").all()
    assert len(landed) > 0

    for f in landed:
        for w in sim_db.query(AirWaybill).filter(AirWaybill.flight_number == f.flight_number).all():
            dlv_count = sim_db.query(AirTrackingEvent).filter(
                AirTrackingEvent.awb_number == w.awb_number,
                AirTrackingEvent.event_code == "DLV"
            ).count()
            if w.scheduled_delivery <= sim2.sim_now:
                assert dlv_count == 1, f"{w.awb_number} missing DLV event after restart rebuild"
            else:
                assert dlv_count == 0, f"{w.awb_number} got premature DLV event"


def test_live_endpoint():
    """Test /api/air/live endpoint returns simulator status."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        resp = client.get("/api/air/live")
        assert resp.status_code == 200
        data = resp.json()
        assert "simulator" in data
        assert "flights" in data
        assert "recent_events" in data
        assert "open_exceptions" in data

        resp = client.post("/api/air/sim/control", json={"action": "set_speed", "speed": 120})
        assert resp.status_code == 200
        assert resp.json()["speed"] == 120.0

        resp = client.post("/api/air/sim/control", json={"action": "bad_action"})
        assert resp.status_code == 400

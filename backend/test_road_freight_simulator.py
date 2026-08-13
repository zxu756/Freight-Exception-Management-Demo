"""
Unit tests for the live road freight simulator.
实时陆运模拟器单元测试
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
import road_freight_simulator as sim_module
from road_freight_simulator import RoadFreightSimulator, ROAD_ROUTES
from road_freight_models import (
    Depot, RoadTrip, RoadConsignment, RoadTrackingEvent, RoadException
)
from road_freight_seed import generate_depots


@pytest.fixture()
def sim_db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr(sim_module, "SessionLocal", TestSession)
    db = TestSession()
    generate_depots(db)
    db.commit()
    yield db
    db.close()


@pytest.fixture()
def sim(sim_db):
    s = RoadFreightSimulator(speed=60)
    s._init_counters()
    s._init_route_schedule()
    return s


def test_timetable_volume_1000_to_1500_per_day():
    """Test timetable produces 1000-1500 trips per day."""
    daily = sum(r[2] for r in ROAD_ROUTES)
    assert 1000 <= daily <= 1500, f"Expected 1000-1500 trips/day, got {daily}"


def test_backfill_generates_trips_and_consignments(sim, sim_db):
    """Test backfill creates trips for the window and consignments for each."""
    sim._backfill()
    sim_db.commit()

    trips = sim_db.query(RoadTrip).all()
    consignments = sim_db.query(RoadConsignment).all()
    assert len(trips) > 200
    assert len(consignments) > len(trips)

    for c in consignments:
        assert c.consignment_number.startswith("RD-")
        assert c.declared_value_nzd > 0
        assert c.gross_weight_kg > 0


def test_inter_island_event_chain_has_ferry(sim, sim_db):
    """Test inter-island consignments include a Cook Strait ferry milestone."""
    sim._backfill()
    sim_db.commit()

    trip = sim_db.query(RoadTrip).filter(RoadTrip.is_inter_island == True).first()
    assert trip is not None
    cons = sim_db.query(RoadConsignment).filter(
        RoadConsignment.trip_number == trip.trip_number).first()
    assert cons is not None

    chain = sim._event_chain(trip, cons)
    codes = [code for _, code, _, _ in chain]
    assert codes == ["PUP", "LOAD", "DEP", "FERRY", "ARR", "UNLD", "POD"]


def test_trip_lifecycle_transitions(sim, sim_db):
    """Test trip status derives correctly as sim time advances."""
    sim._backfill()
    sim_db.commit()

    for _ in range(6):
        sim.sim_now += timedelta(hours=5)
        sim.tick()
    sim_db.commit()

    arrived = sim_db.query(RoadTrip).filter(RoadTrip.status == "arrived").count()
    in_transit = sim_db.query(RoadTrip).filter(RoadTrip.status == "in_transit").count()
    assert arrived + in_transit > 0

    dep_events = sim_db.query(RoadTrackingEvent).filter(RoadTrackingEvent.event_code == "DEP").count()
    assert dep_events > 0


def test_delay_injection_creates_exceptions(sim, sim_db):
    """Test delayed trips generate delay exceptions for their consignments."""
    mp = pytest.MonkeyPatch()
    original = sim_module.random.random
    calls = {"n": 0}

    def forced_random():
        calls["n"] += 1
        if calls["n"] == 1:
            return 0.5    # cancellation roll -> no cancel
        if calls["n"] == 2:
            return 0.001  # delay roll -> delay injected
        return 0.5

    mp.setattr(sim_module.random, "random", forced_random)
    try:
        trip = sim._create_trip("AKL", "HLZ", "Mainfreight",
                                dep=sim.sim_now + timedelta(hours=2))
        assert trip is not None
        assert trip.delay_minutes > 0
    finally:
        mp.undo()

    sim._push(trip.scheduled_departure - timedelta(minutes=30), "delay_announce", trip.trip_number)
    sim.sim_now = trip.scheduled_departure - timedelta(minutes=30)
    sim._process_pending(sim_db)
    sim_db.commit()

    excs = sim_db.query(RoadException).filter(
        RoadException.consignment_number.in_(
            [c.consignment_number for c in sim_db.query(RoadConsignment).filter(
                RoadConsignment.trip_number == trip.trip_number).all()]
        )
    ).all()
    assert len(excs) > 0
    for e in excs:
        assert e.risk_level in ("low", "medium", "high")
        assert 0 <= e.risk_score <= 100
        assert e.recovery_options


def test_ferry_delay_creates_ferry_delay_exception(sim, sim_db):
    """Test inter-island trips with ferry delay produce ferry_delay exceptions."""
    mp = pytest.MonkeyPatch()
    original = sim_module.random.random
    calls = {"n": 0}

    def forced_random():
        calls["n"] += 1
        if calls["n"] == 1:
            return 0.001  # ferry delay roll -> delay injected (inter-island has no cancel roll)
        return 0.5

    mp.setattr(sim_module.random, "random", forced_random)
    try:
        trip = sim._create_trip("AKL", "CHC", "Mainfreight",
                                dep=sim.sim_now + timedelta(hours=2))
        assert trip is not None
        assert trip.is_inter_island is True
        assert trip.delay_reason_code == "ferry"
    finally:
        mp.undo()

    sim._push(trip.scheduled_departure - timedelta(minutes=30), "delay_announce", trip.trip_number)
    sim.sim_now = trip.scheduled_departure - timedelta(minutes=30)
    sim._process_pending(sim_db)
    sim_db.commit()

    excs = sim_db.query(RoadException).filter(
        RoadException.exception_type == "ferry_delay"
    ).all()
    assert len(excs) > 0


def test_cancellation_creates_no_consignments(sim, sim_db):
    """Test cancelled trips don't get consignments."""
    mp = pytest.MonkeyPatch()
    original = sim_module.random.random
    calls = {"n": 0}

    def forced():
        calls["n"] += 1
        if calls["n"] == 1:
            return 0.0001  # cancellation roll (0.8% domestic)
        return 0.5

    mp.setattr(sim_module.random, "random", forced)
    try:
        trip = sim._create_trip("AKL", "WLG", "Mainfreight",
                                dep=sim.sim_now + timedelta(hours=3))
    finally:
        mp.undo()
    assert trip is not None
    assert trip.status == "cancelled"

    sim_db.commit()
    consignments = sim_db.query(RoadConsignment).filter(
        RoadConsignment.trip_number == trip.trip_number).all()
    assert len(consignments) == 0


def test_temp_alert_creates_exception(sim, sim_db):
    """Test temperature excursion alerts generate temp_excursion exceptions."""
    sim._backfill()
    sim_db.commit()

    trip = sim_db.query(RoadTrip).filter(RoadTrip.vehicle_type == "refrigerated").first()
    if not trip:
        pytest.skip("No refrigerated trip generated in this run")
    cons = sim_db.query(RoadConsignment).filter(
        RoadConsignment.trip_number == trip.trip_number).first()

    sim._push(sim.sim_now, "temp_alert", cons.consignment_number)
    sim._process_pending(sim_db)
    sim_db.commit()

    exc = sim_db.query(RoadException).filter(
        RoadException.consignment_number == cons.consignment_number,
        RoadException.exception_type == "temp_excursion"
    ).first()
    assert exc is not None
    assert sim_db.query(RoadConsignment).filter(
        RoadConsignment.consignment_number == cons.consignment_number).first().temp_excursion_alert is True


def test_restart_rebuild_continues_timelines(sim, sim_db):
    """Test that after a simulated process restart, consignment timelines continue."""
    sim._backfill()
    sim_db.commit()

    sim.sim_now += timedelta(hours=10)
    sim.tick()
    sim_db.commit()

    sim2 = RoadFreightSimulator(speed=60)
    sim2.sim_now = sim.sim_now
    sim2._init_counters()
    sim2._init_route_schedule()
    sim2._rebuild_pending_from_db()

    sim2.sim_now += timedelta(hours=10)
    sim2.tick()
    sim_db.commit()

    arrived = sim_db.query(RoadTrip).filter(RoadTrip.status == "arrived").all()
    assert len(arrived) > 0

    for t in arrived:
        for c in sim_db.query(RoadConsignment).filter(
                RoadConsignment.trip_number == t.trip_number).all():
            pod_count = sim_db.query(RoadTrackingEvent).filter(
                RoadTrackingEvent.consignment_number == c.consignment_number,
                RoadTrackingEvent.event_code == "POD"
            ).count()
            if c.scheduled_delivery <= sim2.sim_now:
                assert pod_count == 1, f"{c.consignment_number} missing POD event after restart rebuild"
            else:
                assert pod_count == 0, f"{c.consignment_number} got premature POD event"


def test_live_endpoint():
    """Test /api/road/live endpoint returns simulator status."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        resp = client.get("/api/road/live")
        assert resp.status_code == 200
        data = resp.json()
        assert "simulator" in data
        assert "trips" in data
        assert "recent_events" in data
        assert "open_exceptions" in data

        resp = client.post("/api/road/sim/control", json={"action": "set_speed", "speed": 120})
        assert resp.status_code == 200
        assert resp.json()["speed"] == 120.0

        resp = client.post("/api/road/sim/control", json={"action": "bad_action"})
        assert resp.status_code == 400

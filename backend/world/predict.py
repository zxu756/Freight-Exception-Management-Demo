"""
Prediction engine - forecasts which freight movements will be impacted while
a weather event is still in its buffer period (started_at <= now < impact_at).

During the buffer the weather is not yet delaying anything. This module scans
upcoming air flights / road trips / vessel visits that will cross the affected
location once the event materializes, and records a PredictedImpact for each -
a proactive heads-up before the actual delay hits.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from database import Base
from environment_models import SEVERITY_DELAY_MINUTES


class PredictedImpact(Base):
    """A forecast that a movement will be delayed once an event materializes."""
    __tablename__ = "predicted_impacts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    mode = Column(String(10))  # air / road / sea
    reference = Column(String(40), index=True)  # flight/trip/vessel id
    location = Column(String(20))
    predicted_delay_minutes = Column(Integer)
    impact_at = Column(DateTime)
    predicted_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='predicted')  # predicted / materialized / expired
    description = Column(Text)


def _predicted_delay(severity):
    lo, hi = SEVERITY_DELAY_MINUTES.get(severity, (15, 60))
    return int((lo + hi) / 2)


def predict_impacts(db, now):
    """Scan buffer-period events and forecast affected movements."""
    from environment_models import EnvironmentEvent
    buffering = db.query(EnvironmentEvent).filter(
        EnvironmentEvent.impact_at.isnot(None),
        EnvironmentEvent.started_at <= now,
        EnvironmentEvent.impact_at > now,
    ).all()
    for ev in buffering:
        _predict_for_event(db, ev, now)


def _predict_for_event(db, ev, now):
    lo = ev.impact_at
    hi = ev.ends_at
    delay = _predicted_delay(ev.severity)

    if ev.mode == 'air':
        from air_cargo_models import AirFlight
        cands = db.query(AirFlight).filter(
            AirFlight.scheduled_departure >= lo,
            AirFlight.scheduled_departure <= hi,
            AirFlight.status.in_(['scheduled', 'boarding', 'delayed']),
        ).all()
        for x in cands:
            if ev.location not in (x.origin_airport, x.destination_airport):
                continue
            _record(db, ev, 'air', x.flight_number, ev.location, delay, now)
    elif ev.mode == 'road':
        from road_freight_models import RoadTrip
        cands = db.query(RoadTrip).filter(
            RoadTrip.scheduled_departure >= lo,
            RoadTrip.scheduled_departure <= hi,
            RoadTrip.status.in_(['scheduled', 'in_transit']),
        ).all()
        for x in cands:
            if ev.location not in (x.origin_depot, x.destination_depot):
                continue
            _record(db, ev, 'road', x.trip_number, ev.location, delay, now)
    elif ev.mode == 'sea':
        from sea_freight_models import VesselVisit
        cands = db.query(VesselVisit).filter(
            VesselVisit.arrival_datetime >= lo,
            VesselVisit.arrival_datetime <= hi,
            VesselVisit.vessel_status == 'EXPECTED',
        ).all()
        for x in cands:
            if ev.location != x.port_code:
                continue
            _record(db, ev, 'sea', x.vessel_visit_id, ev.location, delay, now)


def _record(db, ev, mode, reference, location, delay, now):
    existing = db.query(PredictedImpact).filter(
        PredictedImpact.event_id == ev.id,
        PredictedImpact.reference == reference,
    ).first()
    if existing:
        return
    when = ev.impact_at.strftime('%m-%d %H:%M')
    db.add(PredictedImpact(
        event_id=ev.id, mode=mode, reference=reference, location=location,
        predicted_delay_minutes=delay, impact_at=ev.impact_at,
        predicted_at=now, status='predicted',
        description=f"{ev.description}；预计 {reference} 在 {when} 后延误约 {delay} 分钟",
    ))


def cleanup_predictions(db, now):
    """Mark predictions whose event has materialized (impact period started)."""
    db.query(PredictedImpact).filter(
        PredictedImpact.status == 'predicted',
        PredictedImpact.impact_at <= now,
    ).update({'status': 'materialized'}, synchronize_session=False)

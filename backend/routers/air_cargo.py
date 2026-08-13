"""
Air cargo API endpoints.
空运货物管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from air_cargo_models import (
    Airport, AirFlight, AirWaybill, AirTrackingEvent, AirCustomsInspection, AirException
)

router = APIRouter()


@router.get("/air/airports")
async def get_airports(
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get airport list.

    Args:
        region: Filter by region ('nz_domestic' or 'international')

    Returns:
        List of airports
    """
    query = db.query(Airport)
    if region:
        query = query.filter(Airport.region == region)
    airports = query.all()
    return {
        "count": len(airports),
        "airports": [
            {
                "iata_code": a.iata_code,
                "name": a.name,
                "city": a.city,
                "country": a.country,
                "region": a.region,
                "is_nz_gateway": a.is_nz_gateway,
                "curfew_hours": a.curfew_hours,
                "congestion_level": a.congestion_level,
                "weather": a.weather
            }
            for a in airports
        ]
    }


@router.get("/air/flights")
async def get_flights(
    status: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    is_freighter: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get flight schedule.

    Args:
        status: Filter by flight status
        origin: Filter by origin airport IATA code
        destination: Filter by destination airport IATA code
        is_freighter: Filter by freighter vs passenger belly

    Returns:
        List of flights
    """
    query = db.query(AirFlight)
    if status:
        query = query.filter(AirFlight.status == status)
    if origin:
        query = query.filter(AirFlight.origin_airport == origin)
    if destination:
        query = query.filter(AirFlight.destination_airport == destination)
    if is_freighter is not None:
        query = query.filter(AirFlight.is_freighter == is_freighter)
    flights = query.all()
    return {
        "count": len(flights),
        "flights": [
            {
                "flight_number": f.flight_number,
                "airline": f.airline,
                "aircraft_type": f.aircraft_type,
                "is_freighter": f.is_freighter,
                "origin": f.origin_airport,
                "destination": f.destination_airport,
                "scheduled_departure": f.scheduled_departure.isoformat(),
                "scheduled_arrival": f.scheduled_arrival.isoformat(),
                "actual_departure": f.actual_departure.isoformat() if f.actual_departure else None,
                "actual_arrival": f.actual_arrival.isoformat() if f.actual_arrival else None,
                "status": f.status,
                "delay_minutes": f.delay_minutes,
                "delay_reason_code": f.delay_reason_code,
                "loaded_pct": f.loaded_pct,
                "capacity_kg": f.capacity_kg
            }
            for f in flights
        ]
    }


@router.get("/air/waybills")
async def get_waybills(
    route_type: Optional[str] = None,
    status: Optional[str] = None,
    customer_tier: Optional[str] = None,
    has_exception: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get air waybills.

    Args:
        route_type: Filter by 'domestic', 'international', 'transshipment'
        status: Filter by current Cargo IMP milestone
        customer_tier: Filter by customer tier
        has_exception: Filter by whether waybill has active exceptions

    Returns:
        List of waybills
    """
    query = db.query(AirWaybill)
    if route_type:
        query = query.filter(AirWaybill.route_type == route_type)
    if status:
        query = query.filter(AirWaybill.current_status == status)
    if customer_tier:
        query = query.filter(AirWaybill.customer_tier == customer_tier)
    if has_exception is not None:
        query = query.join(AirException, AirException.awb_number == AirWaybill.awb_number)
    waybills = query.all()
    return {
        "count": len(waybills),
        "waybills": [
            {
                "awb_number": w.awb_number,
                "hawb_number": w.hawb_number,
                "route_type": w.route_type,
                "origin": w.origin_airport,
                "destination": w.destination_airport,
                "flight_number": w.flight_number,
                "commodity_desc": w.commodity_desc,
                "commodity_code": w.commodity_code,
                "pieces": w.pieces,
                "chargeable_weight_kg": w.chargeable_weight_kg,
                "declared_value_nzd": w.declared_value_nzd,
                "customer_name": w.customer_name,
                "customer_tier": w.customer_tier,
                "service_level": w.service_level,
                "priority": w.priority,
                "special_handling_codes": w.special_handling_codes,
                "current_status": w.current_status,
                "current_location": w.current_location,
                "scheduled_delivery": w.scheduled_delivery.isoformat(),
                "estimated_delivery": w.estimated_delivery.isoformat() if w.estimated_delivery else None,
                "sla_deadline": w.sla_deadline.isoformat()
            }
            for w in waybills
        ]
    }


@router.get("/air/waybills/{awb_number}")
async def get_waybill_detail(awb_number: str, db: Session = Depends(get_db)):
    """
    Get detailed air waybill information.

    Args:
        awb_number: Air waybill number (e.g., 086-80000001)

    Returns:
        Waybill details including events, inspections and exceptions
    """
    waybill = db.query(AirWaybill).filter(AirWaybill.awb_number == awb_number).first()
    if not waybill:
        raise HTTPException(status_code=404, detail="Air waybill not found")

    events = db.query(AirTrackingEvent).filter(
        AirTrackingEvent.awb_number == awb_number
    ).order_by(AirTrackingEvent.timestamp.asc()).all()

    inspections = db.query(AirCustomsInspection).filter(
        AirCustomsInspection.awb_number == awb_number
    ).all()

    exceptions = db.query(AirException).filter(
        AirException.awb_number == awb_number
    ).all()

    return {
        "awb_number": waybill.awb_number,
        "hawb_number": waybill.hawb_number,
        "route_type": waybill.route_type,
        "origin": waybill.origin_airport,
        "destination": waybill.destination_airport,
        "transit_points": waybill.transit_points,
        "flight_number": waybill.flight_number,
        "commodity": {
            "desc": waybill.commodity_desc,
            "hs_code": waybill.commodity_code,
            "pieces": waybill.pieces,
            "gross_weight_kg": waybill.gross_weight_kg,
            "volume_cbm": waybill.volume_cbm,
            "chargeable_weight_kg": waybill.chargeable_weight_kg,
            "special_handling_codes": waybill.special_handling_codes,
            "dg_class": waybill.dg_class,
            "un_number": waybill.un_number,
            "temp_min_c": waybill.temp_min_c,
            "temp_max_c": waybill.temp_max_c,
            "temp_excursion_alert": waybill.temp_excursion_alert,
            "expiry_date": waybill.expiry_date.isoformat() if waybill.expiry_date else None
        },
        "parties": {
            "shipper": waybill.shipper_name,
            "consignee": waybill.consignee_name,
            "customer": waybill.customer_name,
            "customer_tier": waybill.customer_tier
        },
        "commercial": {
            "declared_value_nzd": waybill.declared_value_nzd,
            "service_level": waybill.service_level,
            "priority": waybill.priority,
            "sla_tier": waybill.sla_tier
        },
        "status": {
            "current_status": waybill.current_status,
            "current_location": waybill.current_location,
            "scheduled_delivery": waybill.scheduled_delivery.isoformat(),
            "estimated_delivery": waybill.estimated_delivery.isoformat() if waybill.estimated_delivery else None,
            "sla_deadline": waybill.sla_deadline.isoformat(),
            "delivered_at": waybill.delivered_at.isoformat() if waybill.delivered_at else None
        },
        "events": [
            {
                "event_code": e.event_code,
                "event_desc": e.event_desc,
                "location": e.location,
                "timestamp": e.timestamp.isoformat(),
                "source": e.source,
                "reason_code": e.reason_code,
                "message": e.message
            }
            for e in events
        ],
        "inspections": [
            {
                "inspection_id": i.inspection_id,
                "inspection_type": i.inspection_type,
                "agency": i.agency,
                "status": i.status,
                "initiated_at": i.initiated_at.isoformat(),
                "released_at": i.released_at.isoformat() if i.released_at else None,
                "finding": i.finding
            }
            for i in inspections
        ],
        "exceptions": [
            {
                "exception_id": x.exception_id,
                "exception_type": x.exception_type,
                "severity": x.severity,
                "risk_level": x.risk_level,
                "risk_score": x.risk_score,
                "status": x.status,
                "root_cause": x.root_cause,
                "ai_diagnosis": x.ai_diagnosis,
                "ai_confidence": x.ai_confidence,
                "recovery_options": x.recovery_options,
                "delay_hours": x.delay_hours,
                "business_section": x.business_section,
                "classification_confidence": x.classification_confidence,
                "classification_decision": x.classification_decision,
                "ood_score": x.ood_score,
                "is_ood": x.is_ood,
                "anomaly_score": x.anomaly_score,
                "anomaly_reason": x.anomaly_reason,
                "exception_category": x.exception_category,
                "root_cause_category": x.root_cause_category,
                "predicted_downstream_impact": x.predicted_downstream_impact,
                "recovery_cost": x.recovery_cost,
                "detected_at": x.detected_at.isoformat()
            }
            for x in exceptions
        ]
    }


@router.get("/air/exceptions")
async def get_air_exceptions(
    exception_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get air cargo exceptions.

    Args:
        exception_type: Filter by exception type
        risk_level: Filter by risk level ('low', 'medium', 'high')
        status: Filter by exception status

    Returns:
        List of air exceptions
    """
    query = db.query(AirException)
    if exception_type:
        query = query.filter(AirException.exception_type == exception_type)
    if risk_level:
        query = query.filter(AirException.risk_level == risk_level)
    if status:
        query = query.filter(AirException.status == status)
    exceptions = query.order_by(AirException.risk_score.desc()).all()
    return {
        "count": len(exceptions),
        "exceptions": [
            {
                "exception_id": x.exception_id,
                "awb_number": x.awb_number,
                "exception_type": x.exception_type,
                "severity": x.severity,
                "risk_level": x.risk_level,
                "risk_score": x.risk_score,
                "status": x.status,
                "requires_human_approval": x.requires_human_approval,
                "root_cause": x.root_cause,
                "ai_diagnosis": x.ai_diagnosis,
                "ai_confidence": x.ai_confidence,
                "recovery_options": x.recovery_options,
                "delay_hours": x.delay_hours,
                "business_section": x.business_section,
                "classification_confidence": x.classification_confidence,
                "classification_decision": x.classification_decision,
                "ood_score": x.ood_score,
                "is_ood": x.is_ood,
                "anomaly_score": x.anomaly_score,
                "anomaly_reason": x.anomaly_reason,
                "exception_category": x.exception_category,
                "root_cause_category": x.root_cause_category,
                "predicted_downstream_impact": x.predicted_downstream_impact,
                "recovery_cost": x.recovery_cost,
                "detected_at": x.detected_at.isoformat()
            }
            for x in exceptions
        ]
    }


@router.get("/air/dashboard")
async def get_air_dashboard(db: Session = Depends(get_db)):
    """
    Get air cargo operations dashboard summary.

    Returns:
        Aggregated air cargo KPIs
    """
    total_waybills = db.query(AirWaybill).count()
    domestic = db.query(AirWaybill).filter(AirWaybill.route_type == "domestic").count()
    international = db.query(AirWaybill).filter(AirWaybill.route_type == "international").count()
    transshipment = db.query(AirWaybill).filter(AirWaybill.route_type == "transshipment").count()

    active_flights = db.query(AirFlight).filter(AirFlight.status.in_(["scheduled", "departed", "delayed"])).count()
    delayed_flights = db.query(AirFlight).filter(AirFlight.status == "delayed").count()

    open_exceptions = db.query(AirException).filter(AirException.status != "resolved").count()
    high_risk = db.query(AirException).filter(AirException.risk_level == "high").count()
    pending_approval = db.query(AirException).filter(AirException.status == "pending_approval").count()

    by_type = {}
    for exc_type in ["delay", "offload", "diversion", "customs_hold", "damage", "misroute", "temp_excursion"]:
        count = db.query(AirException).filter(AirException.exception_type == exc_type).count()
        if count:
            by_type[exc_type] = count

    by_risk_level = {"low": 0, "medium": 0, "high": 0}
    for level in by_risk_level:
        by_risk_level[level] = db.query(AirException).filter(AirException.risk_level == level).count()

    temp_alerts = db.query(AirWaybill).filter(AirWaybill.temp_excursion_alert == True).count()
    inspections_open = db.query(AirCustomsInspection).filter(AirCustomsInspection.status != "released").count()

    return {
        "waybills": {
            "total": total_waybills,
            "domestic": domestic,
            "international": international,
            "transshipment": transshipment
        },
        "flights": {
            "active": active_flights,
            "delayed": delayed_flights
        },
        "exceptions": {
            "open": open_exceptions,
            "high_risk": high_risk,
            "pending_approval": pending_approval,
            "by_type": by_type,
            "by_risk_level": by_risk_level
        },
        "cold_chain": {
            "temp_excursion_alerts": temp_alerts
        },
        "customs": {
            "open_inspections": inspections_open
        }
    }


@router.get("/air/kpi")
async def get_air_kpi(db: Session = Depends(get_db)):
    """Get air cargo exception-management KPIs (Kratos Task 12)."""
    total = db.query(AirException).count()
    if total == 0:
        return {"total": 0}
    diagnosed = db.query(AirException).filter(AirException.status == "diagnosed").count()
    pending = db.query(AirException).filter(AirException.status == "pending_approval").count()
    escalated = db.query(AirException).filter(AirException.status == "escalated").count()
    high_risk = db.query(AirException).filter(AirException.risk_level == "high").count()
    ood = db.query(AirException).filter(AirException.is_ood == True).count()

    by_category = {}
    by_root_cause = {}
    for e in db.query(AirException).all():
        cat = e.exception_category or "Unknown"
        rc = e.root_cause_category or "Unknown"
        by_category[cat] = by_category.get(cat, 0) + 1
        by_root_cause[rc] = by_root_cause.get(rc, 0) + 1

    return {
        "total": total,
        "automation_rate": round(diagnosed / total, 3),
        "pending_approval_rate": round(pending / total, 3),
        "escalation_rate": round(escalated / total, 3),
        "high_risk_rate": round(high_risk / total, 3),
        "ood_rate": round(ood / total, 3),
        "sla_breach_rate": round(high_risk / total, 3),
        "by_category": by_category,
        "by_root_cause": by_root_cause,
    }


@router.get("/air/notifications")
async def get_air_notifications(limit: int = 20, db: Session = Depends(get_db)):
    """Get proactive customer notifications for air cargo exceptions."""
    from notification_models import ExceptionNotification
    notifs = db.query(ExceptionNotification).filter(
        ExceptionNotification.mode == "air"
    ).order_by(ExceptionNotification.sent_at.desc()).limit(limit).all()
    return {
        "count": len(notifs),
        "notifications": [
            {
                "notification_id": n.notification_id,
                "exception_id": n.exception_id,
                "reference": n.reference,
                "recipient": n.recipient,
                "message": n.message,
                "revised_eta": n.revised_eta.isoformat() if n.revised_eta else None,
                "confidence": n.confidence,
                "sent_at": n.sent_at.isoformat(),
            }
            for n in notifs
        ]
    }


@router.get("/air/live")
async def get_air_live(db: Session = Depends(get_db)):
    """
    Get live air cargo simulation status and recent activity.
    获取实时空运模拟状态与近期动态

    Returns:
        Sim clock, flight counts, recent events, upcoming departures, exceptions summary
    """
    from air_cargo_simulator import simulator

    flights_total = db.query(AirFlight).count()
    status_counts = {}
    for f in db.query(AirFlight).all():
        status_counts[f.status] = status_counts.get(f.status, 0) + 1

    recent_events = db.query(AirTrackingEvent).order_by(
        AirTrackingEvent.timestamp.desc()
    ).limit(20).all()

    upcoming = db.query(AirFlight).filter(
        AirFlight.scheduled_departure > simulator.sim_now,
        AirFlight.status.in_(["scheduled", "boarding", "delayed"])
    ).order_by(AirFlight.scheduled_departure.asc()).limit(10).all()

    delayed_flights = db.query(AirFlight).filter(
        AirFlight.status == "delayed"
    ).order_by(AirFlight.delay_minutes.desc()).limit(10).all()

    open_exceptions = db.query(AirException).filter(
        AirException.status != "resolved"
    ).order_by(AirException.risk_score.desc()).limit(10).all()

    return {
        "simulator": {
            "running": simulator.running,
            "paused": simulator.paused,
            "speed": simulator.speed,
            "sim_now": simulator.sim_now.isoformat(),
            "flights_generated": simulator.flights_generated,
            "waybills_generated": simulator.waybills_generated,
            "exceptions_generated": simulator.exceptions_generated,
            "events_generated": simulator.events_generated
        },
        "flights": {
            "total_in_db": flights_total,
            "by_status": status_counts
        },
        "upcoming_departures": [
            {
                "flight_number": f.flight_number,
                "airline": f.airline,
                "origin": f.origin_airport,
                "destination": f.destination_airport,
                "scheduled_departure": f.scheduled_departure.isoformat(),
                "status": f.status,
                "delay_minutes": f.delay_minutes,
                "delay_reason_code": f.delay_reason_code
            }
            for f in upcoming
        ],
        "delayed_flights": [
            {
                "flight_number": f.flight_number,
                "origin": f.origin_airport,
                "destination": f.destination_airport,
                "delay_minutes": f.delay_minutes,
                "delay_reason_code": f.delay_reason_code
            }
            for f in delayed_flights
        ],
        "open_exceptions": [
            {
                "exception_id": x.exception_id,
                "awb_number": x.awb_number,
                "exception_type": x.exception_type,
                "risk_level": x.risk_level,
                "risk_score": x.risk_score,
                "status": x.status,
                "root_cause": x.root_cause,
                "business_section": x.business_section,
                "classification_decision": x.classification_decision,
                "is_ood": x.is_ood
            }
            for x in open_exceptions
        ],
        "recent_events": [
            {
                "event_code": e.event_code,
                "event_desc": e.event_desc,
                "awb_number": e.awb_number,
                "location": e.location,
                "timestamp": e.timestamp.isoformat(),
                "reason_code": e.reason_code
            }
            for e in recent_events
        ]
    }


@router.post("/air/sim/control")
async def control_air_sim(body: dict, db: Session = Depends(get_db)):
    """
    Control the live air cargo simulator.

    Body:
        {"action": "pause" | "resume" | "set_speed", "speed": 60}

    Returns:
        Simulator status
    """
    from air_cargo_simulator import simulator

    action = body.get("action")
    if action == "pause":
        simulator.paused = True
        message = "Simulator paused"
    elif action == "resume":
        simulator.paused = False
        message = "Simulator resumed"
    elif action == "set_speed":
        speed = body.get("speed", 60.0)
        simulator.set_speed(speed)
        message = f"Simulator speed set to {speed}x"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    return {
        "success": True,
        "message": message,
        "running": simulator.running,
        "paused": simulator.paused,
        "speed": simulator.speed,
        "sim_now": simulator.sim_now.isoformat()
    }

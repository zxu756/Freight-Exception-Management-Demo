"""
Road freight API endpoints.
陆运货物管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from road_freight_models import (
    Depot, RoadTrip, RoadConsignment, RoadTrackingEvent, RoadException
)

router = APIRouter()


@router.get("/road/depots")
async def get_depots(
    island: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get depot list, optionally filtered by island ('north' or 'south')."""
    query = db.query(Depot)
    if island:
        query = query.filter(Depot.island == island)
    depots = query.all()
    return {
        "count": len(depots),
        "depots": [
            {
                "depot_code": d.depot_code,
                "name": d.name,
                "city": d.city,
                "region": d.region,
                "island": d.island,
                "is_hub": d.is_hub,
                "congestion_level": d.congestion_level,
                "weather": d.weather
            }
            for d in depots
        ]
    }


@router.get("/road/trips")
async def get_trips(
    status: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    is_inter_island: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get road trips, with optional filters."""
    query = db.query(RoadTrip)
    if status:
        query = query.filter(RoadTrip.status == status)
    if origin:
        query = query.filter(RoadTrip.origin_depot == origin)
    if destination:
        query = query.filter(RoadTrip.destination_depot == destination)
    if is_inter_island is not None:
        query = query.filter(RoadTrip.is_inter_island == is_inter_island)
    trips = query.all()
    return {
        "count": len(trips),
        "trips": [
            {
                "trip_number": t.trip_number,
                "carrier": t.carrier,
                "vehicle_type": t.vehicle_type,
                "origin": t.origin_depot,
                "destination": t.destination_depot,
                "is_inter_island": t.is_inter_island,
                "scheduled_departure": t.scheduled_departure.isoformat(),
                "scheduled_arrival": t.scheduled_arrival.isoformat(),
                "actual_departure": t.actual_departure.isoformat() if t.actual_departure else None,
                "actual_arrival": t.actual_arrival.isoformat() if t.actual_arrival else None,
                "status": t.status,
                "delay_minutes": t.delay_minutes,
                "delay_reason_code": t.delay_reason_code,
                "distance_km": t.distance_km,
                "loaded_pct": t.loaded_pct,
                "capacity_kg": t.capacity_kg,
                "driver_name": t.driver_name,
                "driver_hours_remaining": t.driver_hours_remaining
            }
            for t in trips
        ]
    }


@router.get("/road/consignments")
async def get_consignments(
    route_type: Optional[str] = None,
    status: Optional[str] = None,
    customer_tier: Optional[str] = None,
    has_exception: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get road consignments, with optional filters."""
    query = db.query(RoadConsignment)
    if route_type:
        query = query.filter(RoadConsignment.route_type == route_type)
    if status:
        query = query.filter(RoadConsignment.current_status == status)
    if customer_tier:
        query = query.filter(RoadConsignment.customer_tier == customer_tier)
    if has_exception is not None:
        query = query.join(RoadException, RoadException.consignment_number == RoadConsignment.consignment_number)
    consignments = query.all()
    return {
        "count": len(consignments),
        "consignments": [
            {
                "consignment_number": c.consignment_number,
                "trip_number": c.trip_number,
                "route_type": c.route_type,
                "origin": c.origin_depot,
                "destination": c.destination_depot,
                "commodity_desc": c.commodity_desc,
                "commodity_code": c.commodity_code,
                "pieces": c.pieces,
                "gross_weight_kg": c.gross_weight_kg,
                "declared_value_nzd": c.declared_value_nzd,
                "customer_name": c.customer_name,
                "customer_tier": c.customer_tier,
                "service_level": c.service_level,
                "priority": c.priority,
                "current_status": c.current_status,
                "current_location": c.current_location,
                "scheduled_delivery": c.scheduled_delivery.isoformat(),
                "estimated_delivery": c.estimated_delivery.isoformat() if c.estimated_delivery else None,
                "sla_deadline": c.sla_deadline.isoformat()
            }
            for c in consignments
        ]
    }


@router.get("/road/consignments/{consignment_number}")
async def get_consignment_detail(consignment_number: str, db: Session = Depends(get_db)):
    """Get detailed road consignment information."""
    cons = db.query(RoadConsignment).filter(
        RoadConsignment.consignment_number == consignment_number).first()
    if not cons:
        raise HTTPException(status_code=404, detail="Road consignment not found")

    events = db.query(RoadTrackingEvent).filter(
        RoadTrackingEvent.consignment_number == consignment_number
    ).order_by(RoadTrackingEvent.timestamp.asc()).all()

    exceptions = db.query(RoadException).filter(
        RoadException.consignment_number == consignment_number
    ).all()

    return {
        "consignment_number": cons.consignment_number,
        "trip_number": cons.trip_number,
        "route_type": cons.route_type,
        "origin": cons.origin_depot,
        "destination": cons.destination_depot,
        "commodity": {
            "desc": cons.commodity_desc,
            "hs_code": cons.commodity_code,
            "pieces": cons.pieces,
            "gross_weight_kg": cons.gross_weight_kg,
            "volume_cbm": cons.volume_cbm,
            "dg_class": cons.dg_class,
            "un_number": cons.un_number,
            "temp_min_c": cons.temp_min_c,
            "temp_max_c": cons.temp_max_c,
            "temp_excursion_alert": cons.temp_excursion_alert
        },
        "parties": {
            "shipper": cons.shipper_name,
            "consignee": cons.consignee_name,
            "customer": cons.customer_name,
            "customer_tier": cons.customer_tier
        },
        "commercial": {
            "declared_value_nzd": cons.declared_value_nzd,
            "service_level": cons.service_level,
            "priority": cons.priority,
            "sla_tier": cons.sla_tier
        },
        "status": {
            "current_status": cons.current_status,
            "current_location": cons.current_location,
            "scheduled_delivery": cons.scheduled_delivery.isoformat(),
            "estimated_delivery": cons.estimated_delivery.isoformat() if cons.estimated_delivery else None,
            "sla_deadline": cons.sla_deadline.isoformat(),
            "delivered_at": cons.delivered_at.isoformat() if cons.delivered_at else None
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
                "recommended_action": x.recommended_action,
                "recommendation_reason": x.recommendation_reason,
                "detected_at": x.detected_at.isoformat()
            }
            for x in exceptions
        ]
    }


@router.get("/road/exceptions")
async def get_road_exceptions(
    exception_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get road freight exceptions."""
    query = db.query(RoadException)
    if exception_type:
        query = query.filter(RoadException.exception_type == exception_type)
    if risk_level:
        query = query.filter(RoadException.risk_level == risk_level)
    if status:
        query = query.filter(RoadException.status == status)
    exceptions = query.order_by(RoadException.risk_score.desc()).all()
    return {
        "count": len(exceptions),
        "exceptions": [
            {
                "exception_id": x.exception_id,
                "consignment_number": x.consignment_number,
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
                "recommended_action": x.recommended_action,
                "recommendation_reason": x.recommendation_reason,
                "detected_at": x.detected_at.isoformat()
            }
            for x in exceptions
        ]
    }


@router.get("/road/exceptions/{exception_id}")
async def get_road_exception_detail(exception_id: str, db: Session = Depends(get_db)):
    """Get a single exception with full detail for the four-step AI pipeline view."""
    exc = db.query(RoadException).filter(RoadException.exception_id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    cons = db.query(RoadConsignment).filter(
        RoadConsignment.consignment_number == exc.consignment_number).first()

    from notification_models import ExceptionNotification
    notifications = db.query(ExceptionNotification).filter(
        ExceptionNotification.exception_id == exception_id).all()

    return {
        "exception_id": exc.exception_id,
        "exception_type": exc.exception_type,
        "exception_category": exc.exception_category,
        "root_cause_category": exc.root_cause_category,
        "severity": exc.severity,
        "risk_level": exc.risk_level,
        "risk_score": exc.risk_score,
        "status": exc.status,
        "requires_human_approval": exc.requires_human_approval,
        "root_cause": exc.root_cause,
        "ai_diagnosis": exc.ai_diagnosis,
        "ai_confidence": exc.ai_confidence,
        "business_section": exc.business_section,
        "classification_confidence": exc.classification_confidence,
        "classification_decision": exc.classification_decision,
        "ood_score": exc.ood_score,
        "is_ood": exc.is_ood,
        "anomaly_score": exc.anomaly_score,
        "anomaly_reason": exc.anomaly_reason,
        "recovery_options": exc.recovery_options,
        "recommended_action": exc.recommended_action,
        "recommendation_reason": exc.recommendation_reason,
        "recovery_cost": exc.recovery_cost,
        "predicted_downstream_impact": exc.predicted_downstream_impact,
        "delay_hours": exc.delay_hours,
        "detected_at": exc.detected_at.isoformat(),
        "cargo": {
            "consignment_number": cons.consignment_number if cons else exc.consignment_number,
            "commodity_desc": cons.commodity_desc if cons else None,
            "declared_value_nzd": cons.declared_value_nzd if cons else None,
            "customer_name": cons.customer_name if cons else None,
            "customer_tier": cons.customer_tier if cons else None,
            "service_level": cons.service_level if cons else None,
            "sla_tier": cons.sla_tier if cons else None,
            "is_sla_breached": cons.is_sla_breached if cons else False,
            "breach_type": cons.breach_type if cons else None,
            "sla_penalty_nzd": cons.sla_penalty_nzd if cons else None,
            "service_level": cons.service_level if cons else None,
            "sla_tier": cons.sla_tier if cons else None,
            "is_sla_breached": cons.is_sla_breached if cons else False,
            "breach_type": cons.breach_type if cons else None,
            "sla_penalty_nzd": cons.sla_penalty_nzd if cons else None,
            "route_type": cons.route_type if cons else None,
        },
        "notifications": [
            {
                "notification_id": n.notification_id,
                "message": n.message,
                "revised_eta": n.revised_eta.isoformat() if n.revised_eta else None,
                "confidence": n.confidence,
                "sent_at": n.sent_at.isoformat(),
            }
            for n in notifications
        ],
    }


@router.get("/road/dashboard")
async def get_road_dashboard(db: Session = Depends(get_db)):
    """Get road freight operations dashboard summary."""
    total_cons = db.query(RoadConsignment).count()
    line_haul = db.query(RoadConsignment).filter(RoadConsignment.route_type == "line_haul").count()
    regional = db.query(RoadConsignment).filter(RoadConsignment.route_type == "regional").count()
    inter_island = db.query(RoadConsignment).filter(RoadConsignment.route_type == "inter_island").count()

    active_trips = db.query(RoadTrip).filter(RoadTrip.status.in_(["scheduled", "loading", "in_transit", "delayed"])).count()
    delayed_trips = db.query(RoadTrip).filter(RoadTrip.status == "delayed").count()

    open_exceptions = db.query(RoadException).filter(RoadException.status != "resolved").count()
    high_risk = db.query(RoadException).filter(RoadException.risk_level == "high").count()
    pending_approval = db.query(RoadException).filter(RoadException.status == "pending_approval").count()

    by_type = {}
    for exc_type in ["delay", "road_closure", "breakdown", "accident", "driver_hours", "temp_excursion", "ferry_delay", "overweight"]:
        count = db.query(RoadException).filter(RoadException.exception_type == exc_type).count()
        if count:
            by_type[exc_type] = count

    by_risk_level = {"low": 0, "medium": 0, "high": 0}
    for level in by_risk_level:
        by_risk_level[level] = db.query(RoadException).filter(RoadException.risk_level == level).count()

    temp_alerts = db.query(RoadConsignment).filter(RoadConsignment.temp_excursion_alert == True).count()

    return {
        "consignments": {
            "total": total_cons,
            "line_haul": line_haul,
            "regional": regional,
            "inter_island": inter_island
        },
        "trips": {
            "active": active_trips,
            "delayed": delayed_trips
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
        }
    }


@router.get("/road/kpi")
async def get_road_kpi(db: Session = Depends(get_db)):
    """Get road freight exception-management KPIs (Kratos Task 12)."""
    total = db.query(RoadException).count()
    if total == 0:
        return {"total": 0}
    diagnosed = db.query(RoadException).filter(RoadException.status == "diagnosed").count()
    pending = db.query(RoadException).filter(RoadException.status == "pending_approval").count()
    escalated = db.query(RoadException).filter(RoadException.status == "escalated").count()
    high_risk = db.query(RoadException).filter(RoadException.risk_level == "high").count()
    ood = db.query(RoadException).filter(RoadException.is_ood == True).count()

    by_category = {}
    by_root_cause = {}
    for e in db.query(RoadException).all():
        cat = e.exception_category or "Unknown"
        rc = e.root_cause_category or "Unknown"
        by_category[cat] = by_category.get(cat, 0) + 1
        by_root_cause[rc] = by_root_cause.get(rc, 0) + 1

    delivered = db.query(RoadConsignment).filter(RoadConsignment.delivered_at.isnot(None)).count()
    breached = db.query(RoadConsignment).filter(RoadConsignment.is_sla_breached == True).count()
    excused = db.query(RoadConsignment).filter(RoadConsignment.breach_type == "excused").count()
    otd_rate = round((delivered - breached - excused) / delivered, 3) if delivered else None
    sla_breach_rate = round(breached / delivered, 3) if delivered else None
    excused_rate = round(excused / delivered, 3) if delivered else None

    return {
        "total": total,
        "automation_rate": round(diagnosed / total, 3),
        "pending_approval_rate": round(pending / total, 3),
        "escalation_rate": round(escalated / total, 3),
        "high_risk_rate": round(high_risk / total, 3),
        "ood_rate": round(ood / total, 3),
        "sla_breach_rate": sla_breach_rate,
        "excused_rate": excused_rate,
        "otd_rate": otd_rate,
        "by_category": by_category,
        "by_root_cause": by_root_cause,
    }


@router.get("/road/notifications")
async def get_road_notifications(limit: int = 20, db: Session = Depends(get_db)):
    """Get proactive customer notifications for road freight exceptions."""
    from notification_models import ExceptionNotification
    notifs = db.query(ExceptionNotification).filter(
        ExceptionNotification.mode == "road"
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


@router.get("/road/live")
async def get_road_live(db: Session = Depends(get_db)):
    """Get live road freight simulation status and recent activity."""
    from road_freight_simulator import simulator

    trips_total = db.query(RoadTrip).count()
    status_counts = {}
    for t in db.query(RoadTrip).all():
        status_counts[t.status] = status_counts.get(t.status, 0) + 1

    recent_events = db.query(RoadTrackingEvent).order_by(
        RoadTrackingEvent.timestamp.desc()
    ).limit(20).all()

    upcoming = db.query(RoadTrip).filter(
        RoadTrip.scheduled_departure > simulator.sim_now,
        RoadTrip.status.in_(["scheduled", "loading", "delayed"])
    ).order_by(RoadTrip.scheduled_departure.asc()).limit(10).all()

    delayed_trips = db.query(RoadTrip).filter(
        RoadTrip.status == "delayed"
    ).order_by(RoadTrip.delay_minutes.desc()).limit(10).all()

    open_exceptions = db.query(RoadException).filter(
        RoadException.status != "resolved"
    ).order_by(RoadException.risk_score.desc()).limit(10).all()

    return {
        "simulator": {
            "running": simulator.running,
            "paused": simulator.paused,
            "speed": simulator.speed,
            "sim_now": simulator.sim_now.isoformat(),
            "trips_generated": simulator.trips_generated,
            "consignments_generated": simulator.consignments_generated,
            "exceptions_generated": simulator.exceptions_generated,
            "events_generated": simulator.events_generated
        },
        "trips": {
            "total_in_db": trips_total,
            "by_status": status_counts
        },
        "upcoming_departures": [
            {
                "trip_number": t.trip_number,
                "carrier": t.carrier,
                "origin": t.origin_depot,
                "destination": t.destination_depot,
                "scheduled_departure": t.scheduled_departure.isoformat(),
                "status": t.status,
                "delay_minutes": t.delay_minutes,
                "delay_reason_code": t.delay_reason_code
            }
            for t in upcoming
        ],
        "delayed_trips": [
            {
                "trip_number": t.trip_number,
                "origin": t.origin_depot,
                "destination": t.destination_depot,
                "delay_minutes": t.delay_minutes,
                "delay_reason_code": t.delay_reason_code
            }
            for t in delayed_trips
        ],
        "open_exceptions": [
            {
                "exception_id": x.exception_id,
                "consignment_number": x.consignment_number,
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
                "consignment_number": e.consignment_number,
                "location": e.location,
                "timestamp": e.timestamp.isoformat(),
                "reason_code": e.reason_code
            }
            for e in recent_events
        ]
    }


@router.post("/road/sim/control")
async def control_road_sim(body: dict, db: Session = Depends(get_db)):
    """Control the live road freight simulator."""
    from road_freight_simulator import simulator

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

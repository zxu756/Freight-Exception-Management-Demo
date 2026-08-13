"""
Sea freight API endpoints.
海运货物管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from sea_freight_models import (
    SeaPort, VesselVisit, SeaContainer, SeaTrackingEvent, SeaException
)

router = APIRouter()


@router.get("/sea/ports")
async def get_ports(db: Session = Depends(get_db)):
    """Get NZ port list."""
    ports = db.query(SeaPort).all()
    return {
        "count": len(ports),
        "ports": [
            {
                "port_code": p.port_code,
                "name": p.name,
                "city": p.city,
                "country": p.country,
                "is_nz_port": p.is_nz_port,
                "congestion_level": p.congestion_level
            }
            for p in ports
        ]
    }


@router.get("/sea/vessels")
async def get_vessels(
    port: Optional[str] = None,
    status: Optional[str] = None,
    vessel_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get vessel visits (real PortConnect schedules)."""
    query = db.query(VesselVisit)
    if port:
        query = query.filter(VesselVisit.port_code == port)
    if status:
        query = query.filter(VesselVisit.vessel_status == status)
    if vessel_type:
        query = query.filter(VesselVisit.vessel_type == vessel_type)
    visits = query.order_by(VesselVisit.arrival_datetime.asc()).all()
    return {
        "count": len(visits),
        "vessels": [
            {
                "vessel_visit_id": v.vessel_visit_id,
                "vessel_name": v.vessel_name,
                "imo_number": v.imo_number,
                "inbound_voyage": v.inbound_voyage,
                "outbound_voyage": v.outbound_voyage,
                "vessel_status": v.vessel_status,
                "vessel_type": v.vessel_type,
                "port_code": v.port_code,
                "wharf_name": v.wharf_name,
                "berth": v.berth,
                "previous_port": v.previous_port,
                "next_port": v.next_port,
                "vessel_operator": v.vessel_operator,
                "service_code": v.service_code,
                "arrival_datetime": v.arrival_datetime.isoformat() if v.arrival_datetime else None,
                "departure_datetime": v.departure_datetime.isoformat() if v.departure_datetime else None,
                "delay_minutes": v.delay_minutes,
                "delay_reason_code": v.delay_reason_code
            }
            for v in visits
        ]
    }


@router.get("/sea/containers")
async def get_containers(
    direction: Optional[str] = None,
    status: Optional[str] = None,
    customer_tier: Optional[str] = None,
    has_exception: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get sea containers."""
    query = db.query(SeaContainer)
    if direction:
        query = query.filter(SeaContainer.direction == direction)
    if status:
        query = query.filter(SeaContainer.current_status == status)
    if customer_tier:
        query = query.filter(SeaContainer.customer_tier == customer_tier)
    if has_exception is not None:
        query = query.join(SeaException, SeaException.container_number == SeaContainer.container_number)
    containers = query.all()
    return {
        "count": len(containers),
        "containers": [
            {
                "container_number": c.container_number,
                "direction": c.direction,
                "size": c.size,
                "container_type": c.container_type,
                "commodity_desc": c.commodity_desc,
                "commodity_code": c.commodity_code,
                "gross_weight_kg": c.gross_weight_kg,
                "declared_value_nzd": c.declared_value_nzd,
                "customer_name": c.customer_name,
                "customer_tier": c.customer_tier,
                "current_status": c.current_status,
                "customs_cleared": c.customs_cleared,
                "biosecurity_cleared": c.biosecurity_cleared,
                "is_dg": c.is_dg,
                "temp_excursion_alert": c.temp_excursion_alert,
                "scheduled_delivery": c.scheduled_delivery.isoformat() if c.scheduled_delivery else None,
                "sla_deadline": c.sla_deadline.isoformat() if c.sla_deadline else None
            }
            for c in containers
        ]
    }


@router.get("/sea/containers/{container_number}")
async def get_container_detail(container_number: str, db: Session = Depends(get_db)):
    """Get detailed container information including events and exceptions."""
    container = db.query(SeaContainer).filter(
        SeaContainer.container_number == container_number).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    events = db.query(SeaTrackingEvent).filter(
        SeaTrackingEvent.container_number == container_number
    ).order_by(SeaTrackingEvent.timestamp.asc()).all()

    exceptions = db.query(SeaException).filter(
        SeaException.container_number == container_number
    ).all()

    vessel = db.query(VesselVisit).filter(
        VesselVisit.vessel_visit_id == container.vessel_visit_id).first()

    return {
        "container_number": container.container_number,
        "direction": container.direction,
        "size": container.size,
        "container_type": container.container_type,
        "vessel": {
            "vessel_name": vessel.vessel_name if vessel else None,
            "vessel_operator": vessel.vessel_operator if vessel else None,
            "inbound_voyage": vessel.inbound_voyage if vessel else None,
            "outbound_voyage": vessel.outbound_voyage if vessel else None,
            "port_code": vessel.port_code if vessel else None
        },
        "commodity": {
            "desc": container.commodity_desc,
            "hs_code": container.commodity_code,
            "gross_weight_kg": container.gross_weight_kg,
            "is_dg": container.is_dg,
            "dg_class": container.dg_class,
            "un_number": container.un_number,
            "temp_min_c": container.temp_min_c,
            "temp_max_c": container.temp_max_c,
            "temp_excursion_alert": container.temp_excursion_alert
        },
        "parties": {
            "customer": container.customer_name,
            "customer_tier": container.customer_tier,
            "shipper": container.shipper_name,
            "consignee": container.consignee_name
        },
        "commercial": {
            "declared_value_nzd": container.declared_value_nzd
        },
        "status": {
            "current_status": container.current_status,
            "customs_cleared": container.customs_cleared,
            "biosecurity_cleared": container.biosecurity_cleared,
            "discharged_at": container.discharged_at.isoformat() if container.discharged_at else None,
            "available_at": container.available_at.isoformat() if container.available_at else None,
            "delivered_at": container.delivered_at.isoformat() if container.delivered_at else None,
            "scheduled_delivery": container.scheduled_delivery.isoformat() if container.scheduled_delivery else None,
            "sla_deadline": container.sla_deadline.isoformat() if container.sla_deadline else None
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
                "detected_at": x.detected_at.isoformat()
            }
            for x in exceptions
        ]
    }


@router.get("/sea/exceptions")
async def get_sea_exceptions(
    exception_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get sea freight exceptions."""
    query = db.query(SeaException)
    if exception_type:
        query = query.filter(SeaException.exception_type == exception_type)
    if risk_level:
        query = query.filter(SeaException.risk_level == risk_level)
    if status:
        query = query.filter(SeaException.status == status)
    exceptions = query.order_by(SeaException.risk_score.desc()).all()
    return {
        "count": len(exceptions),
        "exceptions": [
            {
                "exception_id": x.exception_id,
                "container_number": x.container_number,
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
                "detected_at": x.detected_at.isoformat()
            }
            for x in exceptions
        ]
    }


@router.get("/sea/dashboard")
async def get_sea_dashboard(db: Session = Depends(get_db)):
    """Get sea freight operations dashboard summary."""
    total_containers = db.query(SeaContainer).count()
    imports = db.query(SeaContainer).filter(SeaContainer.direction == "import").count()
    exports = db.query(SeaContainer).filter(SeaContainer.direction == "export").count()

    expected_vessels = db.query(VesselVisit).filter(VesselVisit.vessel_status == "EXPECTED").count()
    in_port = db.query(VesselVisit).filter(VesselVisit.vessel_status == "INPORT").count()

    open_exceptions = db.query(SeaException).filter(SeaException.status != "resolved").count()
    high_risk = db.query(SeaException).filter(SeaException.risk_level == "high").count()
    pending_approval = db.query(SeaException).filter(SeaException.status == "pending_approval").count()

    by_type = {}
    for exc_type in ["vessel_delay", "customs_hold", "biosecurity_hold", "port_congestion", "temp_excursion", "damage", "misroute", "dg_incident"]:
        count = db.query(SeaException).filter(SeaException.exception_type == exc_type).count()
        if count:
            by_type[exc_type] = count

    by_risk_level = {"low": 0, "medium": 0, "high": 0}
    for level in by_risk_level:
        by_risk_level[level] = db.query(SeaException).filter(SeaException.risk_level == level).count()

    temp_alerts = db.query(SeaContainer).filter(SeaContainer.temp_excursion_alert == True).count()
    dg_containers = db.query(SeaContainer).filter(SeaContainer.is_dg == True).count()

    return {
        "containers": {
            "total": total_containers,
            "imports": imports,
            "exports": exports,
            "dg": dg_containers
        },
        "vessels": {
            "expected": expected_vessels,
            "in_port": in_port
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


@router.get("/sea/live")
async def get_sea_live(db: Session = Depends(get_db)):
    """Get live sea freight simulation status and recent activity."""
    from sea_freight_simulator import simulator

    vessels_total = db.query(VesselVisit).count()
    status_counts = {}
    for v in db.query(VesselVisit).all():
        status_counts[v.vessel_status] = status_counts.get(v.vessel_status, 0) + 1

    recent_events = db.query(SeaTrackingEvent).order_by(
        SeaTrackingEvent.timestamp.desc()
    ).limit(20).all()

    open_exceptions = db.query(SeaException).filter(
        SeaException.status != "resolved"
    ).order_by(SeaException.risk_score.desc()).limit(10).all()

    return {
        "simulator": {
            "running": simulator.running,
            "paused": simulator.paused,
            "speed": simulator.speed,
            "sim_now": simulator.sim_now.isoformat(),
            "vessels_loaded": simulator.vessels_loaded,
            "containers_generated": simulator.containers_generated,
            "exceptions_generated": simulator.exceptions_generated,
            "events_generated": simulator.events_generated
        },
        "vessels": {
            "total_in_db": vessels_total,
            "by_status": status_counts
        },
        "open_exceptions": [
            {
                "exception_id": x.exception_id,
                "container_number": x.container_number,
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
                "container_number": e.container_number,
                "location": e.location,
                "timestamp": e.timestamp.isoformat(),
                "reason_code": e.reason_code
            }
            for e in recent_events
        ]
    }


@router.post("/sea/sim/control")
async def control_sea_sim(body: dict, db: Session = Depends(get_db)):
    """Control the live sea freight simulator."""
    from sea_freight_simulator import simulator

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

"""
Sea freight API endpoints.
海运货物管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from sea_freight_models import (
    SeaPort, VesselVisit, SeaContainer, SeaTrackingEvent, SeaException, CargoLine
)
from event_classifier import normalize_recovery_options_json
from customer_models import get_customer

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

    cargo_lines = db.query(CargoLine).filter(
        CargoLine.container_number == container_number
    ).order_by(CargoLine.line_number.asc()).all()

    return {
        "container_number": container.container_number,
        "direction": container.direction,
        "size": container.size,
        "container_type": container.container_type,
        "is_lcl": container.is_lcl,
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
                "exception_category": x.exception_category,
                "root_cause_category": x.root_cause_category,
                "predicted_downstream_impact": x.predicted_downstream_impact,
                "recovery_cost": x.recovery_cost,
                "recommended_action": x.recommended_action,
                "recommendation_reason": x.recommendation_reason,
                "detected_at": x.detected_at.isoformat()
            }
            for x in exceptions
        ],
        "cargo_lines": [
            {
                "line_number": l.line_number,
                "commodity_desc": l.commodity_desc,
                "commodity_code": l.commodity_code,
                "customer_name": l.customer_name,
                "customer_tier": l.customer_tier,
                "declared_value_nzd": l.declared_value_nzd,
                "gross_weight_kg": l.gross_weight_kg,
                "service_level": l.service_level,
                "scheduled_delivery": l.scheduled_delivery.isoformat() if l.scheduled_delivery else None,
                "sla_deadline": l.sla_deadline.isoformat() if l.sla_deadline else None,
                "is_sla_breached": l.is_sla_breached,
                "breach_type": l.breach_type,
                "sla_penalty_nzd": l.sla_penalty_nzd
            }
            for l in cargo_lines
        ]
    }


@router.get("/sea/containers/{container_number}/lines")
async def get_container_lines(container_number: str, db: Session = Depends(get_db)):
    """List the individual cargo lines (consignments) inside a container."""
    lines = db.query(CargoLine).filter(
        CargoLine.container_number == container_number
    ).order_by(CargoLine.line_number.asc()).all()
    return {
        "container_number": container_number,
        "count": len(lines),
        "lines": [
            {
                "line_number": l.line_number,
                "commodity_desc": l.commodity_desc,
                "commodity_code": l.commodity_code,
                "customer_name": l.customer_name,
                "customer_tier": l.customer_tier,
                "declared_value_nzd": l.declared_value_nzd,
                "gross_weight_kg": l.gross_weight_kg,
                "service_level": l.service_level,
                "sla_tier": l.sla_tier,
                "temp_min_c": l.temp_min_c,
                "temp_max_c": l.temp_max_c,
                "scheduled_delivery": l.scheduled_delivery.isoformat() if l.scheduled_delivery else None,
                "sla_deadline": l.sla_deadline.isoformat() if l.sla_deadline else None,
                "is_sla_breached": l.is_sla_breached,
                "breach_type": l.breach_type,
                "sla_penalty_nzd": l.sla_penalty_nzd
            }
            for l in lines
        ]
    }


@router.get("/sea/exceptions")
async def get_sea_exceptions(
    exception_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """Get sea freight exceptions (列表默认 limit=200，防止超大载荷拖垮前端；详情请用 detail 端点)。"""
    query = db.query(SeaException)
    if exception_type:
        query = query.filter(SeaException.exception_type == exception_type)
    if risk_level:
        query = query.filter(SeaException.risk_level == risk_level)
    if status:
        query = query.filter(SeaException.status == status)
    exceptions = query.order_by(SeaException.risk_score.desc()).limit(limit).all()
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


@router.get("/sea/exceptions/{exception_id}")
async def get_sea_exception_detail(exception_id: str, db: Session = Depends(get_db)):
    """Get a single exception with full detail for the four-step AI pipeline view."""
    exc = db.query(SeaException).filter(SeaException.exception_id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    container = db.query(SeaContainer).filter(
        SeaContainer.container_number == exc.container_number).first()

    from notification_models import ExceptionNotification
    notifications = db.query(ExceptionNotification).filter(
        ExceptionNotification.exception_id == exception_id,
        ExceptionNotification.mode == "sea").all()

    from decision_models import ExceptionDecision
    _decisions = [
        {
            "decision_id": d.decision_id, "decided_by": d.decided_by,
            "decision": d.decision, "chosen_action": d.chosen_action,
            "note": d.note, "decision_latency_minutes": d.decision_latency_minutes,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
        }
        for d in db.query(ExceptionDecision).filter(
            ExceptionDecision.mode == "sea",
            ExceptionDecision.exception_id == exception_id,
        ).order_by(ExceptionDecision.decided_at).all()
    ]

    _value = exc.cargo_line.declared_value_nzd if exc.cargo_line else (container.declared_value_nzd if container else None)
    _tier = exc.cargo_line.customer_tier if exc.cargo_line else (container.customer_tier if container else None)
    _cname = exc.cargo_line.customer_name if exc.cargo_line else (container.customer_name if container else None)
    _cust = get_customer(db, _cname) if _cname else None

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
        "recovery_options": normalize_recovery_options_json(
            exc.recovery_options, exc.exception_category, _value, _tier),
        "recommended_action": exc.recommended_action,
        "recommendation_reason": exc.recommendation_reason,
        "recovery_cost": exc.recovery_cost,
        "predicted_downstream_impact": exc.predicted_downstream_impact,
        "delay_hours": exc.delay_hours,
        "trigger_event_id": exc.trigger_event_id,
        "detection_latency_minutes": exc.detection_latency_minutes,
        "actual_action": exc.actual_action,
        "actual_cost": exc.actual_cost,
        "actual_recovery_hours": exc.actual_recovery_hours,
        "resolved_at": exc.resolved_at.isoformat() if exc.resolved_at else None,
        "decisions": _decisions,
        "disposition": exc.disposition,
        "disposition_note": exc.disposition_note,
        "disposition_by": exc.disposition_by,
        "disposition_at": exc.disposition_at.isoformat() if exc.disposition_at else None,
        "closed_at": exc.closed_at.isoformat() if exc.closed_at else None,
        "close_evidence": exc.close_evidence,
        "reopen_count": exc.reopen_count,
        "detected_at": exc.detected_at.isoformat(),
        "cargo": {
            "container_number": container.container_number if container else exc.container_number,
            "cargo_line_id": exc.cargo_line_id,
            "line_number": exc.cargo_line.line_number if exc.cargo_line else None,
            "commodity_desc": exc.cargo_line.commodity_desc if exc.cargo_line else (container.commodity_desc if container else None),
            "declared_value_nzd": exc.cargo_line.declared_value_nzd if exc.cargo_line else (container.declared_value_nzd if container else None),
            "customer_name": exc.cargo_line.customer_name if exc.cargo_line else (container.customer_name if container else None),
            "customer_tier": exc.cargo_line.customer_tier if exc.cargo_line else (container.customer_tier if container else None),
            "customer_contact": _cust.contact_name if _cust else None,
            "customer_email": _cust.email if _cust else None,
            "customer_phone": _cust.phone if _cust else None,
            "customer_channel": _cust.preferred_channel if _cust else None,
            "service_level": exc.cargo_line.service_level if exc.cargo_line else (container.service_level if container else None),
            "sla_tier": exc.cargo_line.sla_tier if exc.cargo_line else (container.sla_tier if container else None),
            "is_sla_breached": exc.cargo_line.is_sla_breached if exc.cargo_line else (container.is_sla_breached if container else False),
            "breach_type": exc.cargo_line.breach_type if exc.cargo_line else (container.breach_type if container else None),
            "sla_penalty_nzd": exc.cargo_line.sla_penalty_nzd if exc.cargo_line else (container.sla_penalty_nzd if container else None),
            "size": container.size if container else None,
            "direction": container.direction if container else None,
        },
        "notifications": [
            {
                "notification_id": n.notification_id,
                "recipient": n.recipient,
                "channel": n.channel,
                "recipient_email": n.recipient_email,
                "recipient_phone": n.recipient_phone,
                "sent_status": n.sent_status,
                "external_message_id": n.external_message_id,
                "message": n.message,
                "revised_eta": n.revised_eta.isoformat() if n.revised_eta else None,
                "confidence": n.confidence,
                "sent_at": n.sent_at.isoformat(),
            }
            for n in notifications
        ],
    }


@router.post("/sea/exceptions/{exception_id}/decision")
async def decide_sea_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    """协调员审批/驳回/修改 AI 建议（body: decided_by, decision, chosen_action, note, actual_cost, actual_recovery_hours）。"""
    from decision_models import record_decision
    from world.clock import world_clock
    try:
        row, exc = record_decision(db, "sea", exception_id, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "success": True,
        "decision": {
            "decision_id": row.decision_id, "decided_by": row.decided_by,
            "decision": row.decision, "chosen_action": row.chosen_action,
            "decision_latency_minutes": row.decision_latency_minutes,
            "decided_at": row.decided_at.isoformat(),
        },
        "exception": {
            "exception_id": exc.exception_id, "status": exc.status,
            "actual_action": exc.actual_action, "actual_cost": exc.actual_cost,
            "actual_recovery_hours": exc.actual_recovery_hours,
            "resolved_at": exc.resolved_at.isoformat() if exc.resolved_at else None,
        },
    }


@router.post("/sea/exceptions/{exception_id}/disposition")
async def disposition_sea_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    """人工确认/标记误报/重复/数据问题（EVT-006）：body={disposition: confirmed|false_positive|duplicate|data_issue, note, by}。"""
    from exception_ops import set_disposition
    from world.clock import world_clock
    try:
        exc = set_disposition(db, "sea", exception_id, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "exception_id": exc.exception_id, "status": exc.status,
            "disposition": exc.disposition}


@router.post("/sea/exceptions/{exception_id}/close")
async def close_sea_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    """人工结案（MON-005）：body={evidence, note}。"""
    from exception_ops import close_exception
    from world.clock import world_clock
    try:
        exc = close_exception(db, "sea", exception_id, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "exception_id": exc.exception_id, "status": exc.status,
            "closed_at": exc.closed_at.isoformat() if exc.closed_at else None}


@router.post("/sea/exceptions/{exception_id}/reopen")
async def reopen_sea_exception(exception_id: str, db: Session = Depends(get_db)):
    """重新打开案件（二次异常，MON-005）。"""
    from exception_ops import reopen_exception
    from world.clock import world_clock
    try:
        exc = reopen_exception(db, "sea", exception_id, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "exception_id": exc.exception_id, "status": exc.status,
            "reopen_count": exc.reopen_count}


@router.post("/sea/exceptions")
async def create_sea_exception(body: dict, db: Session = Depends(get_db)):
    """人工创建异常（EVT-006）：body={reference, exception_type, root_cause, diagnosis, note}。"""
    from exception_ops import create_manual_exception
    from world.clock import world_clock
    try:
        exc_type, reference = create_manual_exception(db, "sea", body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "exception_type": exc_type, "reference": reference,
            "message": "manual exception created and customer notified"}


@router.get("/sea/dashboard")
async def get_sea_dashboard(db: Session = Depends(get_db)):
    """Get sea freight operations dashboard summary."""
    total_containers = db.query(SeaContainer).count()
    imports = db.query(SeaContainer).filter(SeaContainer.direction == "import").count()
    exports = db.query(SeaContainer).filter(SeaContainer.direction == "export").count()

    expected_vessels = db.query(VesselVisit).filter(VesselVisit.vessel_status == "EXPECTED").count()
    in_port = db.query(VesselVisit).filter(VesselVisit.vessel_status == "INPORT").count()

    open_exceptions = db.query(SeaException).filter(SeaException.status.notin_(["resolved", "closed"])).count()
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


@router.get("/sea/kpi")
async def get_sea_kpi(db: Session = Depends(get_db)):
    """Get sea freight exception-management KPIs (Kratos Task 12)."""
    total = db.query(SeaException).count()
    if total == 0:
        return {"total": 0}
    diagnosed = db.query(SeaException).filter(SeaException.status == "diagnosed").count()
    pending = db.query(SeaException).filter(SeaException.status == "pending_approval").count()
    escalated = db.query(SeaException).filter(SeaException.status == "escalated").count()
    high_risk = db.query(SeaException).filter(SeaException.risk_level == "high").count()
    ood = db.query(SeaException).filter(SeaException.is_ood == True).count()

    by_category = {}
    by_root_cause = {}
    for e in db.query(SeaException).all():
        cat = e.exception_category or "Unknown"
        rc = e.root_cause_category or "Unknown"
        by_category[cat] = by_category.get(cat, 0) + 1
        by_root_cause[rc] = by_root_cause.get(rc, 0) + 1

    # SLA 指标（基于已交付集装箱）
    delivered = db.query(SeaContainer).filter(SeaContainer.delivered_at.isnot(None)).count()
    breached = db.query(SeaContainer).filter(SeaContainer.is_sla_breached == True).count()
    excused = db.query(SeaContainer).filter(SeaContainer.breach_type == "excused").count()
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


@router.get("/sea/notifications")
async def get_sea_notifications(limit: int = 20, db: Session = Depends(get_db)):
    """Get proactive customer notifications for sea freight exceptions."""
    from notification_models import ExceptionNotification
    notifs = db.query(ExceptionNotification).filter(
        ExceptionNotification.mode == "sea"
    ).order_by(ExceptionNotification.sent_at.desc()).limit(limit).all()
    return {
        "count": len(notifs),
        "notifications": [
            {
                "notification_id": n.notification_id,
                "exception_id": n.exception_id,
                "reference": n.reference,
                "recipient": n.recipient,
                "channel": n.channel,
                "recipient_email": n.recipient_email,
                "recipient_phone": n.recipient_phone,
                "sent_status": n.sent_status,
                "external_message_id": n.external_message_id,
                "message": n.message,
                "revised_eta": n.revised_eta.isoformat() if n.revised_eta else None,
                "confidence": n.confidence,
                "sent_at": n.sent_at.isoformat(),
            }
            for n in notifs
        ]
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
        SeaException.status.notin_(["resolved", "closed"])
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
                "cargo_line_id": x.cargo_line_id,
                "line_number": x.cargo_line.line_number if x.cargo_line else None,
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

@router.post("/sea/env/event")
async def trigger_sea_env_event(body: dict, db: Session = Depends(get_db)):
    """手动注入一个环境事件（用于演示特定场景，如"奥克兰港拥堵"）"""
    from datetime import timedelta
    from environment_events import EVENT_TEMPLATES, SEA_LOCATIONS
    from environment_models import EnvironmentEvent
    from sea_freight_simulator import simulator

    location = body.get("location", "NZAKL")
    if location not in SEA_LOCATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown location: {location}")
    event_type = body.get("event_type", "port_congestion")
    severity = body.get("severity", "severe")
    duration_hours = float(body.get("duration_hours", 12))

    templates = EVENT_TEMPLATES.get("sea", {})
    description = body.get("description") or templates.get(event_type, "{loc} 附近异常").format(loc=location)

    now = simulator.sim_now
    event = EnvironmentEvent(
        event_type=event_type, mode="sea", location=location,
        severity=severity, description=description,
        started_at=now, ends_at=now + timedelta(hours=duration_hours),
    )
    db.add(event)
    db.commit()
    simulator._active_events.setdefault(location, []).append({
        "event_type": event.event_type, "severity": event.severity,
        "description": event.description, "ends_at": event.ends_at,
    })
    return {
        "success": True,
        "event": {
            "event_type": event.event_type, "location": event.location,
            "severity": event.severity, "description": event.description,
            "started_at": event.started_at.isoformat(), "ends_at": event.ends_at.isoformat(),
        }
    }

@router.get("/sea/env/events")
async def get_sea_freight_env_events(db: Session = Depends(get_db)):
    """查活跃环境事件（实时路况通报）"""
    from environment_models import EnvironmentEvent
    from sea_freight_simulator import simulator
    now = simulator.sim_now
    events = db.query(EnvironmentEvent).filter(
        EnvironmentEvent.mode == "sea",
        EnvironmentEvent.started_at <= now,
        EnvironmentEvent.ends_at >= now,
    ).all()
    return {
        "count": len(events),
        "events": [
            {
                "event_type": e.event_type, "location": e.location,
                "severity": e.severity, "description": e.description,
                "ends_at": e.ends_at.isoformat(),
            }
            for e in events
        ]
    }


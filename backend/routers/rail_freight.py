"""
Rail freight API endpoints (KiwiRail-style simulation).
铁路货物管理 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from rail_freight_models import (
    RailStation, RailSegment, RailService, RailConsignment, RailConsignmentLine,
    RailTrackingEvent, RailException,
)
from event_classifier import normalize_recovery_options_json
from customer_models import get_customer

router = APIRouter()


@router.get("/rail/stations")
def get_rail_stations(island: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(RailStation)
    if island:
        query = query.filter(RailStation.island == island)
    rows = query.all()
    return {"count": len(rows), "stations": [
        {"station_code": s.station_code, "name": s.name, "city": s.city,
         "region": s.region, "island": s.island, "is_hub": s.is_hub} for s in rows]}


@router.get("/rail/segments")
def get_rail_segments(db: Session = Depends(get_db)):
    rows = db.query(RailSegment).all()
    return {"count": len(rows), "segments": [
        {"origin": s.origin, "destination": s.destination, "condition": s.condition,
         "speed_factor": s.speed_factor, "description": s.description,
         "updated_at": s.updated_at.isoformat() if s.updated_at else None} for s in rows]}


@router.get("/rail/services")
def get_rail_services(
    status: Optional[str] = None, origin: Optional[str] = None,
    destination: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(RailService)
    if status:
        query = query.filter(RailService.status == status)
    if origin:
        query = query.filter(RailService.origin == origin)
    if destination:
        query = query.filter(RailService.destination == destination)
    rows = query.all()
    return {"count": len(rows), "services": [
        {"train_number": t.train_number, "operator": t.operator, "origin": t.origin,
         "destination": t.destination, "is_inter_island": t.is_inter_island,
         "scheduled_departure": t.scheduled_departure.isoformat(),
         "scheduled_arrival": t.scheduled_arrival.isoformat(),
         "actual_departure": t.actual_departure.isoformat() if t.actual_departure else None,
         "actual_arrival": t.actual_arrival.isoformat() if t.actual_arrival else None,
         "status": t.status, "delay_minutes": t.delay_minutes,
         "delay_reason_code": t.delay_reason_code, "distance_km": t.distance_km,
         "capacity_t": t.capacity_t, "loaded_pct": t.loaded_pct} for t in rows]}


@router.get("/rail/consignments")
def get_rail_consignments(
    route_type: Optional[str] = None, status: Optional[str] = None,
    customer_tier: Optional[str] = None, has_exception: bool = False,
    db: Session = Depends(get_db)):
    query = db.query(RailConsignment)
    if route_type:
        query = query.filter(RailConsignment.route_type == route_type)
    if status:
        query = query.filter(RailConsignment.current_status == status)
    if customer_tier:
        query = query.filter(RailConsignment.customer_tier == customer_tier)
    if has_exception:
        query = query.join(RailException, RailException.consignment_number == RailConsignment.consignment_number)
    rows = query.all()
    return {"count": len(rows), "consignments": [
        {"consignment_number": c.consignment_number, "train_number": c.train_number,
         "route_type": c.route_type, "origin": c.origin, "destination": c.destination,
         "commodity_desc": c.commodity_desc, "commodity_code": c.commodity_code,
         "pieces": c.pieces, "gross_weight_kg": c.gross_weight_kg,
         "declared_value_nzd": c.declared_value_nzd, "customer_name": c.customer_name,
         "customer_tier": c.customer_tier, "service_level": c.service_level,
         "current_status": c.current_status, "current_location": c.current_location,
         "scheduled_delivery": c.scheduled_delivery.isoformat() if c.scheduled_delivery else None,
         "estimated_delivery": c.estimated_delivery.isoformat() if c.estimated_delivery else None,
         "sla_deadline": c.sla_deadline.isoformat() if c.sla_deadline else None} for c in rows]}


@router.get("/rail/consignments/{consignment_number}")
def get_rail_consignment_detail(consignment_number: str, db: Session = Depends(get_db)):
    cons = db.query(RailConsignment).filter(
        RailConsignment.consignment_number == consignment_number).first()
    if not cons:
        raise HTTPException(status_code=404, detail="Consignment not found")
    train = db.query(RailService).filter(RailService.train_number == cons.train_number).first()
    return {
        "consignment_number": cons.consignment_number, "train_number": cons.train_number,
        "route_type": cons.route_type, "is_ltl": cons.is_ltl,
        "origin": cons.origin, "destination": cons.destination,
        "train": {"operator": train.operator if train else None,
                  "scheduled_arrival": train.scheduled_arrival.isoformat() if train else None},
        "commodity": {"desc": cons.commodity_desc, "hs_code": cons.commodity_code,
                      "pieces": cons.pieces, "gross_weight_kg": cons.gross_weight_kg,
                      "temp_min_c": cons.temp_min_c, "temp_max_c": cons.temp_max_c,
                      "temp_excursion_alert": cons.temp_excursion_alert},
        "parties": {"customer": cons.customer_name, "customer_tier": cons.customer_tier},
        "commercial": {"declared_value_nzd": cons.declared_value_nzd,
                       "service_level": cons.service_level, "sla_tier": cons.sla_tier},
        "status": {"current_status": cons.current_status, "current_location": cons.current_location,
                   "scheduled_delivery": cons.scheduled_delivery.isoformat() if cons.scheduled_delivery else None,
                   "estimated_delivery": cons.estimated_delivery.isoformat() if cons.estimated_delivery else None,
                   "sla_deadline": cons.sla_deadline.isoformat() if cons.sla_deadline else None,
                   "delivered_at": cons.delivered_at.isoformat() if cons.delivered_at else None},
        "events": [{"event_code": e.event_code, "event_desc": e.event_desc,
                    "location": e.location, "timestamp": e.timestamp.isoformat(),
                    "reason_code": e.reason_code}
                   for e in db.query(RailTrackingEvent).filter(
                       RailTrackingEvent.consignment_number == consignment_number).all()],
        "exceptions": [{"exception_id": x.exception_id, "exception_type": x.exception_type,
                        "severity": x.severity, "risk_level": x.risk_level,
                        "status": x.status, "root_cause": x.root_cause}
                       for x in db.query(RailException).filter(
                           RailException.consignment_number == consignment_number).all()],
        "cargo_lines": [{"line_number": l.line_number, "commodity_desc": l.commodity_desc,
                         "commodity_code": l.commodity_code, "customer_name": l.customer_name,
                         "customer_tier": l.customer_tier, "declared_value_nzd": l.declared_value_nzd,
                         "service_level": l.service_level, "sla_deadline": l.sla_deadline.isoformat() if l.sla_deadline else None,
                         "is_sla_breached": l.is_sla_breached, "breach_type": l.breach_type,
                         "sla_penalty_nzd": l.sla_penalty_nzd} for l in cons.cargo_lines],
    }


@router.get("/rail/consignments/{consignment_number}/lines")
def get_rail_consignment_lines(consignment_number: str, db: Session = Depends(get_db)):
    lines = db.query(RailConsignmentLine).filter(
        RailConsignmentLine.consignment_number == consignment_number).all()
    return {"consignment_number": consignment_number, "count": len(lines), "lines": [
        {"line_number": l.line_number, "commodity_desc": l.commodity_desc,
         "commodity_code": l.commodity_code, "customer_name": l.customer_name,
         "customer_tier": l.customer_tier, "declared_value_nzd": l.declared_value_nzd,
         "pieces": l.pieces, "gross_weight_kg": l.gross_weight_kg,
         "service_level": l.service_level, "sla_tier": l.sla_tier,
         "temp_min_c": l.temp_min_c, "temp_max_c": l.temp_max_c,
         "sla_deadline": l.sla_deadline.isoformat() if l.sla_deadline else None,
         "is_sla_breached": l.is_sla_breached, "breach_type": l.breach_type,
         "sla_penalty_nzd": l.sla_penalty_nzd} for l in lines]}


@router.get("/rail/exceptions")
def get_rail_exceptions(
    exception_type: Optional[str] = None, risk_level: Optional[str] = None,
    status: Optional[str] = None, limit: int = 200, db: Session = Depends(get_db)):
    query = db.query(RailException)
    if exception_type:
        query = query.filter(RailException.exception_type == exception_type)
    if risk_level:
        query = query.filter(RailException.risk_level == risk_level)
    if status:
        query = query.filter(RailException.status == status)
    rows = query.order_by(RailException.risk_score.desc()).limit(limit).all()
    return {"count": len(rows), "exceptions": [
        {"exception_id": x.exception_id, "consignment_number": x.consignment_number,
         "exception_type": x.exception_type, "severity": x.severity,
         "risk_level": x.risk_level, "risk_score": x.risk_score, "status": x.status,
         "requires_human_approval": x.requires_human_approval, "root_cause": x.root_cause,
         "ai_diagnosis": x.ai_diagnosis, "ai_confidence": x.ai_confidence,
         "recovery_options": x.recovery_options, "delay_hours": x.delay_hours,
         "business_section": x.business_section, "classification_decision": x.classification_decision,
         "is_ood": x.is_ood, "exception_category": x.exception_category,
         "root_cause_category": x.root_cause_category,
         "predicted_downstream_impact": x.predicted_downstream_impact,
         "recovery_cost": x.recovery_cost, "recommended_action": x.recommended_action,
         "recommendation_reason": x.recommendation_reason,
         "detected_at": x.detected_at.isoformat()} for x in rows]}


@router.get("/rail/exceptions/{exception_id}")
def get_rail_exception_detail(exception_id: str, db: Session = Depends(get_db)):
    exc = db.query(RailException).filter(RailException.exception_id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    cons = db.query(RailConsignment).filter(
        RailConsignment.consignment_number == exc.consignment_number).first()
    line = db.query(RailConsignmentLine).filter(
        RailConsignmentLine.id == exc.consignment_line_id).first() if exc.consignment_line_id else None

    from notification_models import ExceptionNotification
    notifications = db.query(ExceptionNotification).filter(
        ExceptionNotification.exception_id == exception_id,
        ExceptionNotification.mode == "rail").all()
    from decision_models import ExceptionDecision
    _decisions = [{"decision_id": d.decision_id, "decided_by": d.decided_by,
                   "decision": d.decision, "chosen_action": d.chosen_action,
                   "note": d.note, "decision_latency_minutes": d.decision_latency_minutes,
                   "decided_at": d.decided_at.isoformat() if d.decided_at else None}
                  for d in db.query(ExceptionDecision).filter(
                      ExceptionDecision.mode == "rail",
                      ExceptionDecision.exception_id == exception_id).all()]
    _value = line.declared_value_nzd if line else (cons.declared_value_nzd if cons else None)
    _tier = line.customer_tier if line else (cons.customer_tier if cons else None)
    _cname = line.customer_name if line else (cons.customer_name if cons else None)
    _cust = get_customer(db, _cname) if _cname else None

    return {
        "exception_id": exc.exception_id, "exception_type": exc.exception_type,
        "exception_category": exc.exception_category,
        "root_cause_category": exc.root_cause_category,
        "severity": exc.severity, "risk_level": exc.risk_level, "risk_score": exc.risk_score,
        "status": exc.status, "requires_human_approval": exc.requires_human_approval,
        "root_cause": exc.root_cause, "ai_diagnosis": exc.ai_diagnosis,
        "ai_confidence": exc.ai_confidence, "business_section": exc.business_section,
        "classification_confidence": exc.classification_confidence,
        "classification_decision": exc.classification_decision,
        "ood_score": exc.ood_score, "is_ood": exc.is_ood,
        "anomaly_score": exc.anomaly_score, "anomaly_reason": exc.anomaly_reason,
        "recovery_options": normalize_recovery_options_json(
            exc.recovery_options, exc.exception_category, _value, _tier),
        "recommended_action": exc.recommended_action,
        "recommendation_reason": exc.recommendation_reason,
        "recovery_cost": exc.recovery_cost,
        "predicted_downstream_impact": exc.predicted_downstream_impact,
        "delay_hours": exc.delay_hours,
        "trigger_event_id": exc.trigger_event_id,
        "detection_latency_minutes": exc.detection_latency_minutes,
        "actual_action": exc.actual_action, "actual_cost": exc.actual_cost,
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
        "escalation_reason": exc.escalation_reason,
        "assignee": exc.assignee,
        "detected_at": exc.detected_at.isoformat(),
        "cargo": {
            "consignment_number": cons.consignment_number if cons else exc.consignment_number,
            "consignment_line_id": exc.consignment_line_id,
            "line_number": line.line_number if line else None,
            "commodity_desc": line.commodity_desc if line else (cons.commodity_desc if cons else None),
            "declared_value_nzd": _value, "customer_name": _cname, "customer_tier": _tier,
            "customer_contact": _cust.contact_name if _cust else None,
            "customer_email": _cust.email if _cust else None,
            "customer_phone": _cust.phone if _cust else None,
            "customer_channel": _cust.preferred_channel if _cust else None,
            "service_level": line.service_level if line else (cons.service_level if cons else None),
            "sla_tier": line.sla_tier if line else (cons.sla_tier if cons else None),
            "is_sla_breached": line.is_sla_breached if line else (cons.is_sla_breached if cons else False),
            "breach_type": line.breach_type if line else (cons.breach_type if cons else None),
            "sla_penalty_nzd": line.sla_penalty_nzd if line else (cons.sla_penalty_nzd if cons else None),
            "route_type": cons.route_type if cons else None,
        },
        "notifications": [{
            "notification_id": n.notification_id, "recipient": n.recipient,
            "channel": n.channel, "recipient_email": n.recipient_email,
            "recipient_phone": n.recipient_phone, "sent_status": n.sent_status,
            "external_message_id": n.external_message_id, "message": n.message,
            "revised_eta": n.revised_eta.isoformat() if n.revised_eta else None,
            "confidence": n.confidence, "sent_at": n.sent_at.isoformat(),
        } for n in notifications],
    }


@router.post("/rail/exceptions/{exception_id}/decision")
def decide_rail_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    """协调员审批/驳回/修改 AI 建议。"""
    from decision_models import record_decision
    from world.clock import world_clock
    try:
        row, exc = record_decision(db, "rail", exception_id, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True,
            "decision": {"decision_id": row.decision_id, "decided_by": row.decided_by,
                         "decision": row.decision, "chosen_action": row.chosen_action,
                         "decision_latency_minutes": row.decision_latency_minutes,
                         "decided_at": row.decided_at.isoformat()},
            "exception": {"exception_id": exc.exception_id, "status": exc.status,
                          "actual_action": exc.actual_action, "actual_cost": exc.actual_cost,
                          "actual_recovery_hours": exc.actual_recovery_hours,
                          "resolved_at": exc.resolved_at.isoformat() if exc.resolved_at else None}}


@router.post("/rail/exceptions/{exception_id}/disposition")
def disposition_rail_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    """人工确认/标记误报/重复/数据问题（EVT-006）。"""
    from exception_ops import set_disposition
    from world.clock import world_clock
    try:
        exc = set_disposition(db, "rail", exception_id, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "exception_id": exc.exception_id, "status": exc.status,
            "disposition": exc.disposition}


@router.post("/rail/exceptions/{exception_id}/close")
def close_rail_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    """人工结案（MON-005）。"""
    from exception_ops import close_exception
    from world.clock import world_clock
    try:
        exc = close_exception(db, "rail", exception_id, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "exception_id": exc.exception_id, "status": exc.status,
            "closed_at": exc.closed_at.isoformat() if exc.closed_at else None}


@router.post("/rail/exceptions/{exception_id}/reopen")
def reopen_rail_exception(exception_id: str, db: Session = Depends(get_db)):
    """重新打开案件。"""
    from exception_ops import reopen_exception
    from world.clock import world_clock
    try:
        exc = reopen_exception(db, "rail", exception_id, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "exception_id": exc.exception_id, "status": exc.status,
            "reopen_count": exc.reopen_count}


@router.post("/rail/exceptions")
def create_rail_exception(body: dict, db: Session = Depends(get_db)):
    """人工创建异常（EVT-006）。"""
    from exception_ops import create_manual_exception
    from world.clock import world_clock
    try:
        exc_type, reference = create_manual_exception(db, "rail", body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "exception_type": exc_type, "reference": reference,
            "message": "manual exception created and customer notified"}



@router.post("/rail/exceptions/{exception_id}/assign")
def assign_rail_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    """责任分配（EXC-004）：body={assignee, by}。"""
    from exception_ops import assign_exception
    from world.clock import world_clock
    try:
        exc = assign_exception(db, "rail", exception_id, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "exception_id": exc.exception_id, "assignee": exc.assignee}

@router.get("/rail/dashboard")
def get_rail_dashboard(db: Session = Depends(get_db)):
    total = db.query(RailConsignment).count()
    intermodal = db.query(RailConsignment).filter(RailConsignment.route_type == "intermodal").count()
    bulk = db.query(RailConsignment).filter(RailConsignment.route_type == "bulk").count()
    active = db.query(RailService).filter(RailService.status.in_(["in_transit", "delayed", "loading"])).count()
    delayed = db.query(RailService).filter(RailService.status == "delayed").count()
    open_exc = db.query(RailException).filter(RailException.status.notin_(["resolved", "closed"])).count()
    high_risk = db.query(RailException).filter(RailException.risk_level == "high", RailException.status.notin_(["resolved", "closed"])).count()
    pending = db.query(RailException).filter(RailException.status == "pending_approval").count()
    by_type = {}
    by_risk = {}
    for x in db.query(RailException).filter(RailException.status.notin_(["resolved", "closed"])).all():
        by_type[x.exception_type] = by_type.get(x.exception_type, 0) + 1
        by_risk[x.risk_level] = by_risk.get(x.risk_level, 0) + 1
    return {"consignments": {"total": total, "intermodal": intermodal, "bulk": bulk, "general": total - intermodal - bulk},
            "services": {"active": active, "delayed": delayed},
            "exceptions": {"open": open_exc, "high_risk": high_risk, "pending_approval": pending,
                           "by_type": by_type, "by_risk_level": by_risk},
            "segments": {"restricted_or_closed": db.query(RailSegment).filter(RailSegment.condition.in_(["restricted", "closed"])).count()}}


@router.get("/rail/kpi")
def get_rail_kpi(db: Session = Depends(get_db)):
    total = db.query(RailException).count()
    if total == 0:
        return {"total": 0}
    diagnosed = db.query(RailException).filter(RailException.status == "diagnosed").count()
    pending = db.query(RailException).filter(RailException.status == "pending_approval").count()
    escalated = db.query(RailException).filter(RailException.status == "escalated").count()
    high = db.query(RailException).filter(RailException.risk_level == "high").count()
    delivered = db.query(RailConsignment).filter(RailConsignment.delivered_at.isnot(None)).count()
    breached = db.query(RailConsignment).filter(RailConsignment.is_sla_breached == True).count()
    excused = db.query(RailConsignment).filter(RailConsignment.breach_type == "excused").count()
    return {"total": total, "automation_rate": round(diagnosed / total, 3),
            "pending_approval_rate": round(pending / total, 3),
            "escalation_rate": round(escalated / total, 3),
            "high_risk_rate": round(high / total, 3),
            "sla_breach_rate": round(breached / delivered, 3) if delivered else None,
            "excused_rate": round(excused / delivered, 3) if delivered else None,
            "otd_rate": round((delivered - breached - excused) / delivered, 3) if delivered else None}


@router.get("/rail/notifications")
def get_rail_notifications(limit: int = 20, db: Session = Depends(get_db)):
    from notification_models import ExceptionNotification
    rows = db.query(ExceptionNotification).filter(
        ExceptionNotification.mode == "rail"
    ).order_by(ExceptionNotification.sent_at.desc()).limit(limit).all()
    return {"count": len(rows), "notifications": [{
        "notification_id": n.notification_id, "exception_id": n.exception_id,
        "reference": n.reference, "recipient": n.recipient, "channel": n.channel,
        "recipient_email": n.recipient_email, "recipient_phone": n.recipient_phone,
        "sent_status": n.sent_status, "message": n.message,
        "revised_eta": n.revised_eta.isoformat() if n.revised_eta else None,
        "confidence": n.confidence, "sent_at": n.sent_at.isoformat()} for n in rows]}


@router.get("/rail/live")
def get_rail_live(db: Session = Depends(get_db)):
    from rail_freight_simulator import simulator
    return {"simulator": {"running": simulator.running, "paused": simulator.paused,
                          "speed": simulator.speed, "sim_now": simulator.sim_now.isoformat(),
                          "trains_generated": simulator.trains_generated,
                          "consignments_generated": simulator.consignments_generated,
                          "exceptions_generated": simulator.exceptions_generated,
                          "events_generated": simulator.events_generated},
            "services": {"total_in_db": db.query(RailService).count(),
                         "by_status": {s: db.query(RailService).filter(RailService.status == s).count()
                                       for s in TRAIN_STATUSES}},
            "upcoming_departures": [{"train_number": t.train_number, "operator": t.operator,
                                     "origin": t.origin, "destination": t.destination,
                                     "scheduled_departure": t.scheduled_departure.isoformat(),
                                     "status": t.status, "delay_minutes": t.delay_minutes,
                                     "delay_reason_code": t.delay_reason_code}
                                    for t in db.query(RailService).filter(
                                        RailService.status.in_(["scheduled", "loading"])).limit(20).all()],
            "delayed_services": [{"train_number": t.train_number, "origin": t.origin,
                                  "destination": t.destination, "delay_minutes": t.delay_minutes,
                                  "delay_reason_code": t.delay_reason_code}
                                 for t in db.query(RailService).filter(RailService.status == "delayed").limit(20).all()],
            "open_exceptions": [{"exception_id": x.exception_id, "consignment_number": x.consignment_number,
                                 "consignment_line_id": x.consignment_line_id,
                                 "line_number": x.consignment_line.line_number if x.consignment_line else None,
                                 "exception_type": x.exception_type, "risk_level": x.risk_level,
                                 "risk_score": x.risk_score, "status": x.status,
                                 "root_cause": x.root_cause, "business_section": x.business_section,
                                 "classification_decision": x.classification_decision,
                                 "is_ood": x.is_ood}
                                for x in db.query(RailException).filter(
                                    RailException.status.notin_(["resolved", "closed"])).order_by(
                                    RailException.risk_score.desc()).limit(50).all()],
            "recent_events": [{"event_code": e.event_code, "event_desc": e.event_desc,
                               "consignment_number": e.consignment_number,
                               "location": e.location,
                               "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                               "reason_code": e.reason_code}
                              for e in db.query(RailTrackingEvent).order_by(
                                  RailTrackingEvent.timestamp.desc()).limit(20).all()]}


@router.post("/rail/sim/control")
def control_rail_sim(body: dict, db: Session = Depends(get_db)):
    from rail_freight_simulator import simulator
    action = body.get("action")
    if action == "pause":
        simulator.paused = True
    elif action == "resume":
        simulator.paused = False
    elif action == "set_speed":
        simulator.set_speed(body.get("speed", 60.0))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    return {"success": True, "running": simulator.running, "paused": simulator.paused,
            "speed": simulator.speed, "sim_now": simulator.sim_now.isoformat()}


@router.post("/rail/env/event")
def trigger_rail_env_event(body: dict, db: Session = Depends(get_db)):
    """手动注入铁路环境事件（track_closure/signal/mechanical/weather）。"""
    from datetime import timedelta
    from rail_freight_simulator import simulator
    from rail_freight_seed import RAIL_STATIONS
    loc = body.get("location", "AKL")
    codes = [s[0] for s in RAIL_STATIONS]
    if loc not in codes:
        raise HTTPException(status_code=400, detail=f"Unknown location: {loc}")
    ev_type = body.get("event_type", "track_closure")
    if ev_type not in ("track_closure", "signal", "mechanical", "weather"):
        raise HTTPException(status_code=400, detail="event_type must be track_closure/signal/mechanical/weather")
    severity = body.get("severity", "moderate")
    hours = float(body.get("duration_hours", 12))
    now = simulator.sim_now
    ends = now + timedelta(hours=hours)
    simulator._active_events.setdefault(loc, []).append({
        "event_type": ev_type, "severity": severity,
        "description": body.get("description") or f"{loc} 铁路线路事件",
        "ends_at": ends, "impact_at": now})
    simulator._update_track_conditions(db)
    return {"success": True, "event": {"event_type": ev_type, "location": loc,
            "severity": severity, "ends_at": ends.isoformat()}}


@router.get("/rail/env/events")
def get_rail_env_events(db: Session = Depends(get_db)):
    rows = db.query(RailSegment).filter(RailSegment.condition != "clear").all()
    return {"count": len(rows), "events": [{"event_type": s.condition, "location": s.origin,
            "severity": "moderate", "description": s.description,
            "ends_at": s.updated_at.isoformat() if s.updated_at else None} for s in rows]}


# 状态常量导出（live 用）
TRAIN_STATUSES = ["scheduled", "loading", "in_transit", "delayed", "arrived", "cancelled"]

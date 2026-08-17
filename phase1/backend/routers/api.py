"""API endpoints for Phase 1."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import Port, Vessel, Container, TrackingEvent, Exception, Notification, Decision, Employee
from detector import detect_exceptions, generate_diagnosis, calculate_risk_score, determine_severity
from advisor import generate_advice, generate_quick_response, estimate_recovery_cost

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    total = db.query(Container).count()
    exceptions = db.query(Exception).count()
    open_exc = db.query(Exception).filter(Exception.status.notin_(["resolved", "closed"])).count()
    high_risk = db.query(Exception).filter(Exception.risk_score >= 60).count()
    
    by_type = {}
    for t in ["delay", "damage", "customs_hold", "misroute"]:
        c = db.query(Exception).filter(Exception.exception_type == t).count()
        if c:
            by_type[t] = c
    
    return {
        "summary": {
            "total_containers": total,
            "total_exceptions": exceptions,
            "open_exceptions": open_exc,
            "high_risk": high_risk,
        },
        "by_type": by_type,
    }


@router.get("/containers")
async def get_containers(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Container)
    if status:
        q = q.filter(Container.status == status)
    if tier:
        q = q.filter(Container.customer_tier == tier)
    
    items = q.all()
    return {
        "count": len(items),
        "containers": [
            {
                "container_number": c.container_number,
                "vessel_id": c.vessel_id,
                "port_code": c.port_code,
                "status": c.status,
                "customer_name": c.customer_name,
                "customer_tier": c.customer_tier,
                "commodity_desc": c.commodity_desc,
                "declared_value_nzd": c.declared_value_nzd,
            }
            for c in items
        ],
    }


@router.get("/containers/{container_number}")
async def get_container_detail(container_number: str, db: Session = Depends(get_db)):
    c = db.query(Container).filter(Container.container_number == container_number).first()
    if not c:
        raise HTTPException(status_code=404, detail="Container not found")
    
    events = db.query(TrackingEvent).filter(
        TrackingEvent.container_number == container_number
    ).order_by(TrackingEvent.timestamp).all()
    
    exceptions = db.query(Exception).filter(
        Exception.container_number == container_number
    ).all()
    
    return {
        "container": {
            "container_number": c.container_number,
            "vessel_id": c.vessel_id,
            "port_code": c.port_code,
            "status": c.status,
            "customer_name": c.customer_name,
            "customer_tier": c.customer_tier,
            "commodity_desc": c.commodity_desc,
            "declared_value_nzd": c.declared_value_nzd,
        },
        "events": [
            {"event_id": e.event_id, "event_code": e.event_code, "event_desc": e.event_desc,
             "location": e.location, "timestamp": e.timestamp.isoformat()}
            for e in events
        ],
        "exceptions": [
            {"exception_id": x.exception_id, "exception_type": x.exception_type,
             "severity": x.severity, "risk_score": x.risk_score, "status": x.status}
            for x in exceptions
        ],
    }


@router.get("/exceptions")
async def get_exceptions(
    exception_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Exception)
    if exception_type:
        q = q.filter(Exception.exception_type == exception_type)
    if severity:
        q = q.filter(Exception.severity == severity)
    if status:
        q = q.filter(Exception.status == status)
    
    items = q.order_by(Exception.risk_score.desc()).all()
    return {
        "count": len(items),
        "exceptions": [
            {
                "exception_id": x.exception_id,
                "container_number": x.container_number,
                "exception_type": x.exception_type,
                "severity": x.severity,
                "risk_score": x.risk_score,
                "status": x.status,
                "root_cause": x.root_cause,
                "ai_diagnosis": x.ai_diagnosis,
                "ai_confidence": x.ai_confidence,
                "recommended_action": x.recommended_action,
                "assigned_to": x.assigned_to,
                "detected_at": x.detected_at.isoformat() if x.detected_at else None,
            }
            for x in items
        ],
    }


@router.get("/exceptions/{exception_id}")
async def get_exception_detail(exception_id: str, db: Session = Depends(get_db)):
    exc = db.query(Exception).filter(Exception.exception_id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    container = db.query(Container).filter(Container.container_number == exc.container_number).first()
    events = db.query(TrackingEvent).filter(
        TrackingEvent.container_number == exc.container_number
    ).order_by(TrackingEvent.timestamp).all()
    
    return {
        "exception": {
            "exception_id": exc.exception_id,
            "container_number": exc.container_number,
            "exception_type": exc.exception_type,
            "severity": exc.severity,
            "risk_score": exc.risk_score,
            "status": exc.status,
            "root_cause": exc.root_cause,
            "ai_diagnosis": exc.ai_diagnosis,
            "ai_confidence": exc.ai_confidence,
            "recommended_action": exc.recommended_action,
            "assigned_to": exc.assigned_to,
            "detected_at": exc.detected_at.isoformat() if exc.detected_at else None,
        },
        "container": {
            "container_number": container.container_number if container else None,
            "status": container.status if container else None,
            "customer_name": container.customer_name if container else None,
            "customer_tier": container.customer_tier if container else None,
            "declared_value_nzd": container.declared_value_nzd if container else None,
        } if container else None,
        "events": [
            {"event_id": e.event_id, "event_code": e.event_code, "location": e.location,
             "timestamp": e.timestamp.isoformat()}
            for e in events
        ],
    }


@router.post("/exceptions/{exception_id}/assign")
async def assign_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    exc = db.query(Exception).filter(Exception.exception_id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    exc.assigned_to = body.get("assigned_to", "Coordinator")
    db.commit()
    return {"success": True, "assigned_to": exc.assigned_to}


@router.post("/exceptions/{exception_id}/resolve")
async def resolve_exception(exception_id: str, body: dict, db: Session = Depends(get_db)):
    exc = db.query(Exception).filter(Exception.exception_id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    exc.status = "resolved"
    exc.resolved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "status": exc.status}


@router.get("/notifications")
async def get_notifications(db: Session = Depends(get_db)):
    items = db.query(Notification).order_by(Notification.created_at.desc()).limit(50).all()
    return {
        "count": len(items),
        "notifications": [
            {"notification_id": n.notification_id, "exception_id": n.exception_id,
             "customer_name": n.customer_name, "message": n.message, "status": n.status,
             "phase": n.phase, "created_at": n.created_at.isoformat()}
            for n in items
        ],
    }


@router.post("/notifications/{notification_id}/send")
async def send_notification(notification_id: str, db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.notification_id == notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.status = "sent"
    n.sent_at = datetime.utcnow()
    db.commit()
    return {"success": True, "status": n.status}


@router.get("/decisions")
async def get_decisions(db: Session = Depends(get_db)):
    items = db.query(Decision).order_by(Decision.decided_at.desc()).limit(50).all()
    return {
        "count": len(items),
        "decisions": [
            {"decision_id": d.decision_id, "exception_id": d.exception_id,
             "decided_by": d.decided_by, "decision": d.decision, "note": d.note,
             "decided_at": d.decided_at.isoformat()}
            for d in items
        ],
    }


@router.post("/decisions")
async def create_decision(body: dict, db: Session = Depends(get_db)):
    import uuid
    decision = Decision(
        decision_id=f"DEC-{uuid.uuid4().hex[:10]}",
        exception_id=body.get("exception_id"),
        decided_by=body.get("decided_by", "Coordinator"),
        decision=body.get("decision", "approve"),
        chosen_action=body.get("chosen_action"),
        note=body.get("note"),
    )
    db.add(decision)
    
    # Update exception status
    exc = db.query(Exception).filter(Exception.exception_id == body.get("exception_id")).first()
    if exc:
        exc.status = "resolved" if body.get("decision") == "approve" else "closed"
        exc.resolved_at = datetime.utcnow()
    
    db.commit()
    return {"success": True, "decision_id": decision.decision_id}


@router.post("/detect")
async def run_detection(db: Session = Depends(get_db)):
    import uuid
    containers = db.query(Container).all()
    new_exceptions = 0
    
    for container in containers:
        events = db.query(TrackingEvent).filter(
            TrackingEvent.container_number == container.container_number
        ).all()
        
        detected = detect_exceptions(container, events)
        for d in detected:
            existing = db.query(Exception).filter(
                Exception.container_number == container.container_number,
                Exception.exception_type == d["type"],
                Exception.status.notin_(["resolved", "closed"])
            ).first()
            
            if not existing:
                risk_score = calculate_risk_score(d["type"], container.customer_tier, container.declared_value_nzd)
                severity = determine_severity(risk_score)
                diag = generate_diagnosis(d["type"], d["reason"])
                
                db.add(Exception(
                    exception_id=f"EXC-{uuid.uuid4().hex[:10]}",
                    container_number=container.container_number,
                    exception_type=d["type"],
                    severity=severity,
                    risk_score=risk_score,
                    status="detected",
                    root_cause=diag["root_cause"],
                    ai_diagnosis=diag["explanation"],
                    ai_confidence=diag["confidence"],
                    recommended_action=diag["recommended_action"],
                ))
                new_exceptions += 1
    
    db.commit()
    return {"success": True, "containers_scanned": len(containers), "new_exceptions": new_exceptions}


@router.get("/advice/{exception_id}")
async def get_advice(exception_id: str, db: Session = Depends(get_db)):
    """获取异常处理建议"""
    exc = db.query(Exception).filter(Exception.exception_id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    container = db.query(Container).filter(Container.container_number == exc.container_number).first()
    
    container_info = {
        "container_number": exc.container_number,
        "customer_name": container.customer_name if container else "Unknown",
        "customer_tier": container.customer_tier if container else "medium",
        "declared_value_nzd": container.declared_value_nzd if container else 0,
    }
    
    exception_info = {
        "exception_type": exc.exception_type,
        "severity": exc.severity,
        "risk_score": exc.risk_score,
        "root_cause": exc.root_cause,
    }
    
    advice = generate_advice(exc.exception_type, container_info, exception_info)
    quick_response = generate_quick_response(exc.exception_type, exc.severity, exc.risk_score)
    estimated_cost = estimate_recovery_cost(exc.exception_type, container_info["declared_value_nzd"])
    
    return {
        "exception_id": exception_id,
        "advice": advice,
        "quick_response": quick_response,
        "estimated_recovery_cost": estimated_cost,
    }


@router.get("/advice/quick/{exception_type}")
async def get_quick_advice(exception_type: str, severity: str = "medium", risk_score: int = 50):
    """快速获取某类异常的建议模板"""
    quick_response = generate_quick_response(exception_type, severity, risk_score)
    templates = {
        "delay": [
            {"title": "联系客户更新ETA", "action": "立即联系客户告知延误", "priority": "high", "estimated_cost": 0},
            {"title": "改订船期", "action": "联系船公司改订", "priority": "medium", "estimated_cost": 500},
        ],
        "customs_hold": [
            {"title": "补充单证", "action": "联系发货人提供完整单证", "priority": "high", "estimated_cost": 0},
            {"title": "联系报关行", "action": "加急处理清关", "priority": "high", "estimated_cost": 200},
        ],
        "damage": [
            {"title": "安排检验", "action": "联系保险公司安排检验", "priority": "high", "estimated_cost": 400},
            {"title": "拍照取证", "action": "对损坏货物拍照", "priority": "high", "estimated_cost": 0},
        ],
        "misroute": [
            {"title": "纠正路由", "action": "联系承运人纠正路由", "priority": "high", "estimated_cost": 300},
            {"title": "拦截货物", "action": "在下一节点拦截", "priority": "high", "estimated_cost": 200},
        ],
    }
    
    return {
        "exception_type": exception_type,
        "quick_response": quick_response,
        "advice_templates": templates.get(exception_type, templates["delay"]),
    }


@router.get("/employees")
async def get_employees(db: Session = Depends(get_db)):
    """获取员工列表"""
    items = db.query(Employee).all()
    return {
        "count": len(items),
        "employees": [
            {
                "employee_id": e.employee_id,
                "name": e.name,
                "role": e.role,
                "email": e.email,
                "department": e.department,
            }
            for e in items
        ],
    }


@router.get("/employees/{employee_id}")
async def get_employee(employee_id: str, db: Session = Depends(get_db)):
    """获取员工详情"""
    e = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {
        "employee_id": e.employee_id,
        "name": e.name,
        "role": e.role,
        "email": e.email,
        "department": e.department,
    }

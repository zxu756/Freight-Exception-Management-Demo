"""
Exception management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import Exception, Shipment, Event, Decision, Notification
from schemas import ExceptionResponse, ApprovalRequest, APIResponse

router = APIRouter()


@router.get("/exceptions", response_model=List[ExceptionResponse])
async def get_all_exceptions(db: Session = Depends(get_db)):
    """
    Get all exceptions.

    Returns list of all freight exceptions in the system.
    """
    exceptions = db.query(Exception).all()
    return exceptions


@router.get("/exceptions/{exception_id}", response_model=ExceptionResponse)
async def get_exception(exception_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific exception.

    Args:
        exception_id: Exception ID (e.g., EXC-2024-00156)

    Returns:
        Exception details including diagnosis, status, and resolution info
    """
    exception = db.query(Exception).filter(
        Exception.exception_id == exception_id
    ).first()

    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")

    return exception


@router.get("/exceptions/{exception_id}/timeline")
async def get_exception_timeline(exception_id: str, db: Session = Depends(get_db)):
    """
    Get event timeline for an exception.

    Args:
        exception_id: Exception ID

    Returns:
        List of events in chronological order
    """
    exception = db.query(Exception).filter(
        Exception.exception_id == exception_id
    ).first()

    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Get all related events
    events = db.query(Event).filter(
        Event.exception_id == exception_id
    ).order_by(Event.timestamp.asc()).all()

    # Get shipment events too
    shipment_events = db.query(Event).filter(
        Event.shipment_id == exception.shipment_id
    ).order_by(Event.timestamp.asc()).all()

    # Combine and format timeline
    timeline = []

    # Add detection event
    timeline.append({
        "timestamp": exception.detected_at.isoformat(),
        "event_type": "exception_detected",
        "title": "Exception Detected",
        "description": f"{exception.exception_type.capitalize()} detected",
        "status": "completed"
    })

    # Add diagnosis event
    if exception.ai_diagnosis:
        timeline.append({
            "timestamp": exception.detected_at.isoformat(),
            "event_type": "ai_diagnosis",
            "title": "AI Diagnosis Complete",
            "description": exception.ai_diagnosis[:100] + "...",
            "confidence": exception.ai_confidence,
            "status": "completed"
        })

    # Add decision events
    decisions = db.query(Decision).filter(
        Decision.exception_id == exception_id
    ).all()

    for decision in decisions:
        timeline.append({
            "timestamp": decision.created_at.isoformat(),
            "event_type": "decision_generated",
            "title": "Solution Options Generated",
            "description": f"{decision.decision_type}: {len(decision.options)} options",
            "status": "completed"
        })

        if decision.human_decision_at:
            timeline.append({
                "timestamp": decision.human_decision_at.isoformat(),
                "event_type": "human_approval",
                "title": "Human Decision Made",
                "description": f"Approved by {decision.human_decision_by}",
                "status": "completed"
            })

    # Add notification events
    notifications = db.query(Notification).filter(
        Notification.exception_id == exception_id
    ).all()

    for notif in notifications:
        timeline.append({
            "timestamp": notif.sent_at.isoformat(),
            "event_type": "notification_sent",
            "title": f"Notification Sent ({notif.channel})",
            "description": f"To: {notif.recipient}",
            "status": "completed"
        })

    # Add resolution event
    if exception.resolved_at:
        timeline.append({
            "timestamp": exception.resolved_at.isoformat(),
            "event_type": "resolved",
            "title": "Exception Resolved",
            "description": f"Resolution time: {exception.resolution_time_minutes} minutes",
            "status": "completed"
        })

    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])

    return {"timeline": timeline}


@router.post("/exceptions/{exception_id}/approve")
async def approve_decision(
    exception_id: str,
    approval: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    Approve a decision for an exception.

    Args:
        exception_id: Exception ID
        approval: Approval request with decision and notes

    Returns:
        Updated exception and decision
    """
    exception = db.query(Exception).filter(
        Exception.exception_id == exception_id
    ).first()

    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Get the decision
    decision = db.query(Decision).filter(
        Decision.exception_id == exception_id
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Update decision with human approval
    decision.human_decision = approval.decision
    decision.human_decision_by = approval.approved_by
    decision.human_decision_at = datetime.utcnow()
    decision.decision_outcome = "accepted"

    # Update exception status
    exception.status = "approved"

    db.commit()
    db.refresh(exception)
    db.refresh(decision)

    return APIResponse(
        success=True,
        data={
            "exception": {
                "exception_id": exception.exception_id,
                "status": exception.status
            },
            "decision": {
                "decision_id": decision.decision_id,
                "human_decision": decision.human_decision,
                "approved_by": decision.human_decision_by
            }
        }
    )


@router.get("/exceptions/{exception_id}/notifications")
async def get_exception_notifications(
    exception_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all notifications sent for an exception.

    Args:
        exception_id: Exception ID

    Returns:
        List of notifications
    """
    notifications = db.query(Notification).filter(
        Notification.exception_id == exception_id
    ).order_by(Notification.sent_at.desc()).all()

    return {
        "notifications": [
            {
                "notification_id": n.notification_id,
                "recipient_type": n.recipient_type,
                "recipient": n.recipient,
                "channel": n.channel,
                "subject": n.subject,
                "message": n.message,
                "sent_at": n.sent_at.isoformat(),
                "status": n.status
            }
            for n in notifications
        ]
    }


@router.get("/exceptions/summary/stats")
async def get_exception_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics for all exceptions.

    Returns:
        Statistics including counts by status, risk level, average resolution time
    """
    exceptions = db.query(Exception).all()

    total = len(exceptions)
    resolved = len([e for e in exceptions if e.status == "resolved"])
    pending_approval = len([e for e in exceptions if e.status == "pending_approval"])
    escalated = len([e for e in exceptions if e.status == "escalated"])

    # Risk level breakdown
    low_risk = len([e for e in exceptions if e.risk_level == "low"])
    medium_risk = len([e for e in exceptions if e.risk_level == "medium"])
    high_risk = len([e for e in exceptions if e.risk_level == "high"])

    # Average resolution time (only for resolved cases)
    resolved_cases = [e for e in exceptions if e.resolution_time_minutes is not None]
    avg_resolution_time = (
        sum(e.resolution_time_minutes for e in resolved_cases) / len(resolved_cases)
        if resolved_cases else 0
    )

    # Auto-resolved count
    auto_resolved = len([
        e for e in exceptions
        if e.status == "resolved" and not e.requires_human_approval
    ])

    return {
        "total_exceptions": total,
        "by_status": {
            "resolved": resolved,
            "pending_approval": pending_approval,
            "escalated": escalated
        },
        "by_risk_level": {
            "low": low_risk,
            "medium": medium_risk,
            "high": high_risk
        },
        "metrics": {
            "avg_resolution_time_minutes": round(avg_resolution_time, 1),
            "auto_resolved_count": auto_resolved,
            "auto_resolved_percentage": round(auto_resolved / total * 100, 1) if total > 0 else 0
        }
    }

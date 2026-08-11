"""
Shipment management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Shipment, Exception, Event
from schemas import ShipmentResponse

router = APIRouter()


@router.get("/shipments", response_model=List[ShipmentResponse])
async def get_all_shipments(db: Session = Depends(get_db)):
    """
    Get all shipments.

    Returns list of all freight shipments in the system.
    """
    shipments = db.query(Shipment).all()
    return shipments


@router.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(shipment_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific shipment.

    Args:
        shipment_id: Shipment ID (e.g., SF-2024-09001)

    Returns:
        Shipment details including cargo, route, and status
    """
    shipment = db.query(Shipment).filter(
        Shipment.shipment_id == shipment_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return shipment


@router.get("/shipments/{shipment_id}/exceptions")
async def get_shipment_exceptions(shipment_id: str, db: Session = Depends(get_db)):
    """
    Get all exceptions for a specific shipment.

    Args:
        shipment_id: Shipment ID

    Returns:
        List of exceptions related to this shipment
    """
    shipment = db.query(Shipment).filter(
        Shipment.shipment_id == shipment_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    exceptions = db.query(Exception).filter(
        Exception.shipment_id == shipment_id
    ).order_by(Exception.detected_at.desc()).all()

    return {
        "shipment_id": shipment_id,
        "exceptions": [
            {
                "exception_id": e.exception_id,
                "exception_type": e.exception_type,
                "severity": e.severity,
                "risk_level": e.risk_level,
                "status": e.status,
                "detected_at": e.detected_at.isoformat(),
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None
            }
            for e in exceptions
        ]
    }


@router.get("/shipments/{shipment_id}/timeline")
async def get_shipment_timeline(shipment_id: str, db: Session = Depends(get_db)):
    """
    Get event timeline for a shipment.

    Args:
        shipment_id: Shipment ID

    Returns:
        List of events in chronological order
    """
    shipment = db.query(Shipment).filter(
        Shipment.shipment_id == shipment_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    events = db.query(Event).filter(
        Event.shipment_id == shipment_id
    ).order_by(Event.timestamp.asc()).all()

    timeline = []

    # Add shipment creation
    timeline.append({
        "timestamp": shipment.created_at.isoformat(),
        "event_type": "shipment_created",
        "title": "Shipment Created",
        "description": f"From {shipment.origin} to {shipment.destination}",
        "status": "completed"
    })

    # Add pickup
    if shipment.scheduled_pickup:
        timeline.append({
            "timestamp": shipment.scheduled_pickup.isoformat(),
            "event_type": "pickup_scheduled",
            "title": "Pickup Scheduled",
            "description": f"Location: {shipment.origin}",
            "status": "completed"
        })

    # Add all events
    for event in events:
        timeline.append({
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "title": event.event_type.replace('_', ' ').title(),
            "description": event.event_source,
            "status": "completed"
        })

    # Add exceptions
    exceptions = db.query(Exception).filter(
        Exception.shipment_id == shipment_id
    ).all()

    for exc in exceptions:
        timeline.append({
            "timestamp": exc.detected_at.isoformat(),
            "event_type": "exception",
            "title": f"Exception: {exc.exception_type}",
            "description": exc.root_cause or "Under investigation",
            "status": "alert",
            "severity": exc.severity
        })

    # Add delivery
    timeline.append({
        "timestamp": shipment.scheduled_delivery.isoformat(),
        "event_type": "delivery_scheduled",
        "title": "Delivery Scheduled",
        "description": f"Location: {shipment.destination}",
        "status": "pending" if shipment.current_status != "delivered" else "completed"
    })

    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])

    return {"timeline": timeline}


@router.get("/shipments/{shipment_id}/status")
async def get_shipment_status(shipment_id: str, db: Session = Depends(get_db)):
    """
    Get current status and location of a shipment.

    Args:
        shipment_id: Shipment ID

    Returns:
        Current status, location, and ETA information
    """
    shipment = db.query(Shipment).filter(
        Shipment.shipment_id == shipment_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Check for active exceptions
    active_exceptions = db.query(Exception).filter(
        Exception.shipment_id == shipment_id,
        Exception.status != "resolved"
    ).all()

    # Calculate SLA status
    from datetime import datetime
    now = datetime.utcnow()
    sla_status = "on_track"
    if shipment.current_eta and shipment.current_eta > shipment.sla_deadline:
        sla_status = "at_risk"

    hours_to_sla = (shipment.sla_deadline - now).total_seconds() / 3600
    if hours_to_sla < 0:
        sla_status = "breached"

    return {
        "shipment_id": shipment_id,
        "current_status": shipment.current_status,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "transport_mode": shipment.transport_mode,
        "current_eta": shipment.current_eta.isoformat() if shipment.current_eta else None,
        "sla_deadline": shipment.sla_deadline.isoformat(),
        "sla_status": sla_status,
        "hours_to_sla": round(hours_to_sla, 1),
        "active_exceptions": len(active_exceptions),
        "container_id": shipment.container_id,
        "vehicle_id": shipment.vehicle_id
    }

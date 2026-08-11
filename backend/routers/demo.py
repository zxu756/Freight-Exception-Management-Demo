"""
Demo control API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from schemas import DemoStartRequest, DemoControlResponse
from models import Shipment, Exception, Event, Decision, Notification

router = APIRouter()


# Demo state
demo_state = {
    "mode": None,
    "is_running": False,
    "current_step": 0
}


@router.post("/demo/start", response_model=DemoControlResponse)
async def start_demo(request: DemoStartRequest, db: Session = Depends(get_db)):
    """
    Start the demo simulation.

    Args:
        request: Demo start request with mode (auto/step/interactive)

    Returns:
        Demo control response
    """
    demo_state["mode"] = request.mode
    demo_state["is_running"] = True
    demo_state["current_step"] = 0

    return DemoControlResponse(
        success=True,
        message=f"Demo started in {request.mode} mode",
        mode=request.mode
    )


@router.post("/demo/pause", response_model=DemoControlResponse)
async def pause_demo():
    """
    Pause the demo simulation.

    Returns:
        Demo control response
    """
    if not demo_state["is_running"]:
        return DemoControlResponse(
            success=False,
            message="Demo is not running"
        )

    demo_state["is_running"] = False

    return DemoControlResponse(
        success=True,
        message="Demo paused",
        mode=demo_state["mode"]
    )


@router.post("/demo/resume", response_model=DemoControlResponse)
async def resume_demo():
    """
    Resume the demo simulation.

    Returns:
        Demo control response
    """
    if demo_state["mode"] is None:
        return DemoControlResponse(
            success=False,
            message="Demo not started yet"
        )

    demo_state["is_running"] = True

    return DemoControlResponse(
        success=True,
        message="Demo resumed",
        mode=demo_state["mode"]
    )


@router.post("/demo/reset", response_model=DemoControlResponse)
async def reset_demo(db: Session = Depends(get_db)):
    """
    Reset demo to initial state.

    Clears all data and reinitializes with seed data.

    Returns:
        Demo control response
    """
    try:
        # Clear all data
        db.query(Notification).delete()
        db.query(Decision).delete()
        db.query(Event).delete()
        db.query(Exception).delete()
        db.query(Shipment).delete()
        db.commit()

        # Reset demo state
        demo_state["mode"] = None
        demo_state["is_running"] = False
        demo_state["current_step"] = 0

        # Re-run seed data
        from init_db import seed_demo_data
        seed_demo_data()

        return DemoControlResponse(
            success=True,
            message="Demo reset to initial state"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset demo: {str(e)}")


@router.post("/demo/next-step", response_model=DemoControlResponse)
async def next_step():
    """
    Advance to next step in step-by-step mode.

    Returns:
        Demo control response with current step
    """
    if demo_state["mode"] != "step":
        return DemoControlResponse(
            success=False,
            message="Demo is not in step-by-step mode"
        )

    demo_state["current_step"] += 1

    return DemoControlResponse(
        success=True,
        message=f"Advanced to step {demo_state['current_step']}",
        mode=demo_state["mode"]
    )


@router.get("/demo/status")
async def get_demo_status():
    """
    Get current demo status.

    Returns:
        Current demo state including mode, running status, and current step
    """
    return {
        "mode": demo_state["mode"],
        "is_running": demo_state["is_running"],
        "current_step": demo_state["current_step"],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/demo/cases")
async def get_demo_cases(db: Session = Depends(get_db)):
    """
    Get all three demo cases with their current status.

    Returns:
        Summary of Case 1, 2, and 3
    """
    cases = []

    # Case 1: SF-2024-09001
    case1_shipment = db.query(Shipment).filter(
        Shipment.shipment_id == "SF-2024-09001"
    ).first()

    case1_exception = db.query(Exception).filter(
        Exception.shipment_id == "SF-2024-09001"
    ).first()

    if case1_shipment and case1_exception:
        cases.append({
            "case_number": 1,
            "risk_level": "low",
            "shipment_id": case1_shipment.shipment_id,
            "customer": case1_shipment.customer_name,
            "cargo_value": case1_shipment.cargo_value,
            "exception_id": case1_exception.exception_id,
            "exception_type": case1_exception.exception_type,
            "status": case1_exception.status,
            "severity": case1_exception.severity,
            "requires_approval": case1_exception.requires_human_approval,
            "resolution_time_minutes": case1_exception.resolution_time_minutes
        })

    # Case 2: SF-2024-09002
    case2_shipment = db.query(Shipment).filter(
        Shipment.shipment_id == "SF-2024-09002"
    ).first()

    case2_exception = db.query(Exception).filter(
        Exception.shipment_id == "SF-2024-09002"
    ).first()

    if case2_shipment and case2_exception:
        cases.append({
            "case_number": 2,
            "risk_level": "medium",
            "shipment_id": case2_shipment.shipment_id,
            "customer": case2_shipment.customer_name,
            "cargo_value": case2_shipment.cargo_value,
            "exception_id": case2_exception.exception_id,
            "exception_type": case2_exception.exception_type,
            "status": case2_exception.status,
            "severity": case2_exception.severity,
            "requires_approval": case2_exception.requires_human_approval,
            "assigned_to": case2_exception.assigned_to
        })

    # Case 3: SF-2024-09003
    case3_shipment = db.query(Shipment).filter(
        Shipment.shipment_id == "SF-2024-09003"
    ).first()

    case3_exception = db.query(Exception).filter(
        Exception.shipment_id == "SF-2024-09003"
    ).first()

    if case3_shipment and case3_exception:
        cases.append({
            "case_number": 3,
            "risk_level": "high",
            "shipment_id": case3_shipment.shipment_id,
            "customer": case3_shipment.customer_name,
            "cargo_value": case3_shipment.cargo_value,
            "exception_id": case3_exception.exception_id,
            "exception_type": case3_exception.exception_type,
            "status": case3_exception.status,
            "severity": case3_exception.severity,
            "requires_approval": case3_exception.requires_human_approval,
            "assigned_to": case3_exception.assigned_to
        })

    return {
        "total_cases": len(cases),
        "cases": cases
    }

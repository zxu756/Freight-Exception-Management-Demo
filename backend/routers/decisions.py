"""
Decision management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json

from database import get_db
from models import Decision, Exception, Shipment
from schemas import DecisionResponse, DecisionOption
from decision_engine import decision_engine
from risk_calculator import calculate_risk_score, categorize_risk, calculate_sla_breach_hours

router = APIRouter()


@router.get("/decisions/{exception_id}")
async def get_decision(exception_id: str, db: Session = Depends(get_db)):
    """
    Get AI recommendations for an exception.

    Args:
        exception_id: Exception ID

    Returns:
        Decision with all options, recommended option, and reasoning
    """
    # Get exception
    exception = db.query(Exception).filter(
        Exception.exception_id == exception_id
    ).first()

    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Get shipment
    shipment = db.query(Shipment).filter(
        Shipment.shipment_id == exception.shipment_id
    ).first()

    # Check if decision already exists
    decision = db.query(Decision).filter(
        Decision.exception_id == exception_id
    ).first()

    if decision:
        # Return existing decision
        options = json.loads(decision.options) if isinstance(decision.options, str) else decision.options
        return {
            "decision_id": decision.decision_id,
            "exception_id": decision.exception_id,
            "decision_type": decision.decision_type,
            "options": options,
            "recommended_option": decision.recommended_option,
            "recommendation_reasoning": decision.recommendation_reasoning,
            "human_decision": decision.human_decision,
            "human_decision_by": decision.human_decision_by,
            "human_decision_at": decision.human_decision_at.isoformat() if decision.human_decision_at else None,
            "decision_outcome": decision.decision_outcome
        }

    # Generate new decision
    exception_data = {
        "delayed_eta": exception.detected_at,  # Simplified for demo
        "delay_hours": 2
    }

    shipment_dict = {
        "cargo_value": shipment.cargo_value,
        "customer_tier": shipment.customer_tier,
        "transport_mode": shipment.transport_mode,
        "sla_deadline": shipment.sla_deadline,
        "current_eta": shipment.current_eta
    }

    # Generate solution options
    options = decision_engine.generate_solutions(
        exception.exception_type,
        shipment_dict,
        exception_data
    )

    # Calculate risk score
    sla_breach = calculate_sla_breach_hours(
        shipment.current_eta if shipment.current_eta else datetime.utcnow(),
        shipment.sla_deadline
    )

    risk_score = calculate_risk_score(
        cargo_value=shipment.cargo_value,
        customer_tier=shipment.customer_tier,
        sla_breach_hours=sla_breach,
        exception_type=exception.exception_type
    )

    risk_level = categorize_risk(risk_score)

    # Rank and get recommendation
    recommended = decision_engine.rank_solutions(
        options,
        shipment_dict,
        risk_score
    )

    # Generate reasoning
    reasoning = decision_engine.generate_reasoning(
        recommended,
        options,
        shipment_dict,
        risk_level
    )

    # Create decision record
    new_decision = Decision(
        decision_id=f"DEC-{datetime.utcnow().strftime('%Y-%m-%d-%H%M%S')}",
        exception_id=exception_id,
        decision_type="recommend",
        options=json.dumps([opt.model_dump() for opt in options]),
        recommended_option=recommended,
        recommendation_reasoning=reasoning,
        created_at=datetime.utcnow()
    )

    db.add(new_decision)
    db.commit()
    db.refresh(new_decision)

    return {
        "decision_id": new_decision.decision_id,
        "exception_id": new_decision.exception_id,
        "decision_type": new_decision.decision_type,
        "options": [opt.model_dump() for opt in options],
        "recommended_option": new_decision.recommended_option,
        "recommendation_reasoning": new_decision.recommendation_reasoning
    }


@router.post("/decisions/{exception_id}/generate")
async def generate_decision(exception_id: str, db: Session = Depends(get_db)):
    """
    Force regeneration of decision options for an exception.

    Args:
        exception_id: Exception ID

    Returns:
        Newly generated decision
    """
    # Delete existing decision if any
    db.query(Decision).filter(Decision.exception_id == exception_id).delete()
    db.commit()

    # Call get_decision which will generate a new one
    return await get_decision(exception_id, db)


@router.get("/decisions/{exception_id}/history")
async def get_decision_history(exception_id: str, db: Session = Depends(get_db)):
    """
    Get decision history for an exception.

    Args:
        exception_id: Exception ID

    Returns:
        All decisions made for this exception
    """
    decisions = db.query(Decision).filter(
        Decision.exception_id == exception_id
    ).order_by(Decision.created_at.desc()).all()

    return {
        "exception_id": exception_id,
        "decisions": [
            {
                "decision_id": d.decision_id,
                "decision_type": d.decision_type,
                "recommended_option": d.recommended_option,
                "human_decision": d.human_decision,
                "created_at": d.created_at.isoformat(),
                "decided_at": d.human_decision_at.isoformat() if d.human_decision_at else None
            }
            for d in decisions
        ]
    }

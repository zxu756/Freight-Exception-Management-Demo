"""
World-level endpoints - the God Panel's control surface over the shared world.

- /world/clock        : the single world clock (time/speed/pause + god jump)
- /world/weather      : regional weather (deterministic + god overrides)
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from world.clock import world_clock
from world.weather import weather_engine, CONDITIONS, CONDITION_LABELS

router = APIRouter()


# ---------------------------------------------------------------------------
# World clock
# ---------------------------------------------------------------------------
@router.get("/world/clock")
async def get_world_clock():
    """Current world clock status (single time authority for all modes)."""
    return {
        "now": world_clock.now.isoformat(),
        "speed": world_clock.speed,
        "paused": world_clock.paused,
    }


@router.post("/world/clock/control")
async def control_world_clock(body: dict):
    """God-mode controls for the world clock.

    Body: {"action": "pause"|"resume"|"set_speed"|"set_time",
           "speed": 60, "time": "2026-08-15T12:00:00"}
    """
    action = body.get("action")
    if action == "pause":
        world_clock.paused = True
        message = "World clock paused"
    elif action == "resume":
        world_clock.paused = False
        message = "World clock resumed"
    elif action == "set_speed":
        world_clock.set_speed(body.get("speed", 60.0))
        message = f"World speed set to {world_clock.speed}x"
    elif action == "set_time":
        raw = body.get("time")
        if not raw:
            raise HTTPException(status_code=400, detail="'time' is required for set_time")
        world_clock.set_now(datetime.fromisoformat(raw))
        message = f"World time set to {world_clock.now.isoformat()}"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    return {
        "success": True,
        "message": message,
        "now": world_clock.now.isoformat(),
        "speed": world_clock.speed,
        "paused": world_clock.paused,
    }


# ---------------------------------------------------------------------------
# World weather
# NOTE: static sub-paths MUST be declared before the dynamic /{code} route.
# ---------------------------------------------------------------------------
@router.get("/world/weather")
async def get_world_weather(db: Session = Depends(get_db)):
    """Full weather snapshot: every region + every location."""
    return weather_engine.overview(db, world_clock.now)


@router.get("/world/weather/overrides")
async def get_weather_overrides(db: Session = Depends(get_db)):
    """List active god overrides."""
    return {"overrides": weather_engine.list_overrides(db, world_clock.now)}


@router.get("/world/weather/{code}")
async def get_location_weather(code: str, db: Session = Depends(get_db)):
    """Resolved weather for one location code (city/airport/depot/port)."""
    w = weather_engine.weather_at(db, code.upper(), world_clock.now)
    w["impact"] = {
        "air": weather_engine.impact_for_mode("air", w),
        "road": weather_engine.impact_for_mode("road", w),
        "sea": weather_engine.impact_for_mode("sea", w),
    }
    return w


@router.post("/world/weather/override")
async def set_weather_override(body: dict, db: Session = Depends(get_db)):
    """God-mode: force weather for a region or location.

    Body: {"target": "ZQN" | "central_otago", "condition": "fog",
           "intensity": 1.0, "hours": 12}
    """
    target = (body.get("target") or "").strip()
    condition = body.get("condition")
    intensity = float(body.get("intensity", 1.0))
    hours = float(body.get("hours", 12))

    if not target:
        raise HTTPException(status_code=400, detail="'target' is required")
    if condition not in CONDITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown condition: {condition} (valid: {CONDITIONS})")

    try:
        ov = weather_engine.set_override(db, target, condition, intensity, hours, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "override": {
            "target": ov.target,
            "target_type": ov.target_type,
            "condition": ov.condition,
            "condition_label": CONDITION_LABELS.get(ov.condition, ov.condition),
            "intensity": ov.intensity,
            "ends_at": ov.ends_at.isoformat(),
        }
    }


@router.post("/world/weather/clear")
async def clear_weather_overrides(body: dict = None, db: Session = Depends(get_db)):
    """Clear god overrides (optionally for one target)."""
    target = (body or {}).get("target")
    n = weather_engine.clear_overrides(db, target)
    return {"success": True, "cleared": n}


# ---------------------------------------------------------------------------
# World state (single snapshot for the God Panel)
# ---------------------------------------------------------------------------
@router.get("/world/state")
async def get_world_state(db: Session = Depends(get_db)):
    """Consolidated world snapshot: clock + weather + active environmental events."""
    from environment_models import EnvironmentEvent

    now = world_clock.now
    weather = weather_engine.overview(db, now)
    active_events = db.query(EnvironmentEvent).filter(
        EnvironmentEvent.started_at <= now,
        EnvironmentEvent.ends_at >= now,
    ).all()

    return {
        "clock": {"now": now.isoformat(), "speed": world_clock.speed, "paused": world_clock.paused},
        "regions": [
            {
                "region": r["region"], "name": r["region_name"],
                "condition": r["condition"], "condition_label": r["condition_label"],
                "temperature_c": r["temperature_c"], "wind_knots": r["wind_knots"],
                "visibility_km": r["visibility_km"],
            }
            for r in weather["regions"]
        ],
        "active_events": [
            {
                "mode": e.mode, "location": e.location, "event_type": e.event_type,
                "severity": e.severity, "description": e.description,
                "ends_at": e.ends_at.isoformat(),
            }
            for e in active_events
        ],
    }


@router.get("/world/shipments")
async def get_world_shipments(db: Session = Depends(get_db)):
    """List through-shipment chains (multi-modal, e.g. sea -> road)."""
    from world.shipments import get_shipments
    shipments = get_shipments(db)
    return {"count": len(shipments), "shipments": shipments}


@router.get("/world/predictions")
async def get_world_predictions(db: Session = Depends(get_db)):
    """List forecast impacts for movements in a weather event's buffer period."""
    from world.predict import PredictedImpact
    rows = db.query(PredictedImpact).order_by(PredictedImpact.predicted_at.desc()).limit(100).all()
    return {
        "count": len(rows),
        "predictions": [
            {
                "mode": r.mode, "reference": r.reference, "location": r.location,
                "predicted_delay_minutes": r.predicted_delay_minutes,
                "impact_at": r.impact_at.isoformat() if r.impact_at else None,
                "status": r.status, "description": r.description,
            }
            for r in rows
        ],
    }


@router.get("/world/customers")
async def get_world_customers(q: Optional[str] = None, db: Session = Depends(get_db)):
    """客户目录：所有客户的基本信息 + 联系方式（通知去向）。"""
    from customer_models import Customer
    query = db.query(Customer)
    if q:
        query = query.filter(Customer.name.ilike(f"%{q}%"))
    rows = query.order_by(Customer.name).all()
    return {
        "count": len(rows),
        "customers": [
            {
                "customer_code": c.customer_code,
                "name": c.name,
                "tier": c.tier,
                "contact_name": c.contact_name,
                "contact_title": c.contact_title,
                "email": c.email,
                "phone": c.phone,
                "mobile": c.mobile,
                "address_line": c.address_line,
                "city": c.city,
                "region": c.region,
                "preferred_channel": c.preferred_channel,
            }
            for c in rows
        ],
    }

"""
World-level endpoints - the God Panel's control surface over the shared world.

- /world/clock        : the single world clock (time/speed/pause + god jump)
- /world/weather      : regional weather (deterministic + god overrides)
"""
from datetime import datetime, timedelta
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


# ---------------------------------------------------------------------------
# Scenario 4 P0/P1/P2: 决策闭环 / 外发回写 / 客户联系 / 绩效 / 指标 / 票视图
# ---------------------------------------------------------------------------
@router.get("/world/carrier-performance")
async def get_carrier_performance(
    mode: Optional[str] = None,
    risky_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """承运人/线路历史准点率（预测特征层，"这条船 60% 会晚点"）。"""
    from world.maintenance import CarrierPerformance
    query = db.query(CarrierPerformance)
    if mode:
        query = query.filter(CarrierPerformance.mode == mode)
    if risky_only:
        query = query.filter(
            CarrierPerformance.on_time_rate <= 0.7,
            CarrierPerformance.total_runs >= 3,
        )
    rows = query.order_by(CarrierPerformance.on_time_rate).limit(limit).all()
    return {
        "count": len(rows),
        "carriers": [
            {
                "mode": c.mode, "carrier_key": c.carrier_key,
                "origin": c.origin, "destination": c.destination,
                "total_runs": c.total_runs, "delayed_runs": c.delayed_runs,
                "cancelled_runs": c.cancelled_runs,
                "avg_delay_minutes": c.avg_delay_minutes,
                "on_time_rate": c.on_time_rate, "top_reason": c.top_reason,
                "refreshed_at": c.refreshed_at.isoformat() if c.refreshed_at else None,
            }
            for c in rows
        ],
    }


@router.get("/world/metrics")
async def get_world_metrics(
    hours: int = 72,
    mode: Optional[str] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """时序指标快照（KPI/检测延迟/外发积压/决策量/主动通知率/违约金）。"""
    from world.maintenance import MetricSnapshot
    from world.clock import world_clock
    start = world_clock.now - timedelta(hours=hours)
    query = db.query(MetricSnapshot).filter(MetricSnapshot.ts >= start)
    if mode:
        query = query.filter(MetricSnapshot.mode == mode)
    if name:
        query = query.filter(MetricSnapshot.name == name)
    rows = query.order_by(MetricSnapshot.ts.asc()).all()
    return {
        "count": len(rows),
        "from": start.isoformat(),
        "metrics": [
            {"ts": m.ts.isoformat(), "mode": m.mode, "name": m.name, "value": m.value}
            for m in rows
        ],
    }


@router.get("/world/tickets")
async def get_world_tickets(limit: int = 500, db: Session = Depends(get_db)):
    """统一票视图：三种方式的票级数据合并（供 ETL / 报表 / 门户）。"""
    from sea_freight_models import CargoLine, SeaContainer
    from air_cargo_models import HouseWaybill, AirWaybill
    from road_freight_models import ConsignmentLine, RoadConsignment
    from customer_models import Customer

    tickets = []

    for line in db.query(CargoLine).order_by(CargoLine.id.desc()).limit(limit).all():
        parent = db.query(SeaContainer).filter(
            SeaContainer.container_number == line.container_number).first()
        cust = db.query(Customer).filter(Customer.name == line.customer_name).first()
        tickets.append({
            "mode": "sea", "parent_reference": line.container_number,
            "ticket_number": str(line.line_number),
            "commodity_desc": line.commodity_desc, "commodity_code": line.commodity_code,
            "customer_name": line.customer_name, "customer_tier": line.customer_tier,
            "declared_value_nzd": line.declared_value_nzd,
            "service_level": line.service_level, "sla_tier": line.sla_tier,
            "sla_deadline": line.sla_deadline.isoformat() if line.sla_deadline else None,
            "is_sla_breached": line.is_sla_breached, "breach_type": line.breach_type,
            "sla_penalty_nzd": line.sla_penalty_nzd,
            "parent_status": parent.current_status if parent else None,
            "customer_email": cust.email if cust else None,
        })

    for hb in db.query(HouseWaybill).order_by(HouseWaybill.id.desc()).limit(limit).all():
        parent = db.query(AirWaybill).filter(AirWaybill.awb_number == hb.awb_number).first()
        cust = db.query(Customer).filter(Customer.name == hb.customer_name).first()
        tickets.append({
            "mode": "air", "parent_reference": hb.awb_number,
            "ticket_number": hb.hawb_number,
            "commodity_desc": hb.commodity_desc, "commodity_code": hb.commodity_code,
            "customer_name": hb.customer_name, "customer_tier": hb.customer_tier,
            "declared_value_nzd": hb.declared_value_nzd,
            "service_level": hb.service_level, "sla_tier": hb.sla_tier,
            "sla_deadline": hb.sla_deadline.isoformat() if hb.sla_deadline else None,
            "is_sla_breached": hb.is_sla_breached, "breach_type": hb.breach_type,
            "sla_penalty_nzd": hb.sla_penalty_nzd,
            "parent_status": parent.current_status if parent else None,
            "customer_email": cust.email if cust else None,
        })

    for line in db.query(ConsignmentLine).order_by(ConsignmentLine.id.desc()).limit(limit).all():
        parent = db.query(RoadConsignment).filter(
            RoadConsignment.consignment_number == line.consignment_number).first()
        cust = db.query(Customer).filter(Customer.name == line.customer_name).first()
        tickets.append({
            "mode": "road", "parent_reference": line.consignment_number,
            "ticket_number": str(line.line_number),
            "commodity_desc": line.commodity_desc, "commodity_code": line.commodity_code,
            "customer_name": line.customer_name, "customer_tier": line.customer_tier,
            "declared_value_nzd": line.declared_value_nzd,
            "service_level": line.service_level, "sla_tier": line.sla_tier,
            "sla_deadline": line.sla_deadline.isoformat() if line.sla_deadline else None,
            "is_sla_breached": line.is_sla_breached, "breach_type": line.breach_type,
            "sla_penalty_nzd": line.sla_penalty_nzd,
            "parent_status": parent.current_status if parent else None,
            "customer_email": cust.email if cust else None,
        })

    tickets.sort(key=lambda t: t["sla_deadline"] or "", reverse=True)
    tickets = tickets[:limit]
    return {"count": len(tickets), "tickets": tickets}


@router.get("/world/customer-contacts")
async def get_customer_contacts(limit: int = 50, db: Session = Depends(get_db)):
    """客户来电/投诉记录（度量"通知是否先于客户来电"）。"""
    from customer_models import CustomerContact
    rows = db.query(CustomerContact).order_by(CustomerContact.contacted_at.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "contacts": [
            {
                "contact_id": c.contact_id, "mode": c.mode, "exception_id": c.exception_id,
                "customer_name": c.customer_name, "contact_type": c.contact_type,
                "channel": c.channel, "note": c.note, "proactive": c.proactive,
                "contacted_at": c.contacted_at.isoformat() if c.contacted_at else None,
            }
            for c in rows
        ],
    }


@router.post("/world/customer-contacts")
async def record_customer_contact(body: dict, db: Session = Depends(get_db)):
    """记录一次客户来电/投诉（body: customer_name 必填；exception_id/mode/contact_type/channel/note 可选）。"""
    from customer_models import record_customer_contact as _rec
    try:
        row = _rec(db, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "success": True,
        "contact": {
            "contact_id": row.contact_id, "customer_name": row.customer_name,
            "contact_type": row.contact_type, "proactive": row.proactive,
            "contacted_at": row.contacted_at.isoformat(),
        },
    }


@router.post("/notifications/{notification_id}/delivery")
async def mark_notification_delivery(notification_id: str, body: dict, db: Session = Depends(get_db)):
    """外发 worker 回写真实送达状态（body: status=sent|failed|delivered, external_message_id?）。"""
    from datetime import datetime as _dt
    from notification_models import ExceptionNotification
    n = db.query(ExceptionNotification).filter(
        ExceptionNotification.notification_id == notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="notification not found")
    status = body.get("status")
    if status not in ("sent", "failed", "delivered"):
        raise HTTPException(status_code=400, detail="status must be sent / failed / delivered")
    n.sent_status = status
    n.external_message_id = body.get("external_message_id")
    n.sent_real_at = _dt.utcnow()
    db.commit()
    return {
        "success": True,
        "notification_id": n.notification_id,
        "sent_status": n.sent_status,
        "external_message_id": n.external_message_id,
    }

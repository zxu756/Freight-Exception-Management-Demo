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
def get_world_clock():
    """Current world clock status (single time authority for all modes)."""
    return {
        "now": world_clock.now.isoformat(),
        "speed": world_clock.speed,
        "paused": world_clock.paused,
    }


@router.post("/world/clock/control")
def control_world_clock(body: dict):
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
def get_world_weather(db: Session = Depends(get_db)):
    """Full weather snapshot: every region + every location."""
    return weather_engine.overview(db, world_clock.now)


@router.get("/world/weather/overrides")
def get_weather_overrides(db: Session = Depends(get_db)):
    """List active god overrides."""
    return {"overrides": weather_engine.list_overrides(db, world_clock.now)}


@router.get("/world/weather/{code}")
def get_location_weather(code: str, db: Session = Depends(get_db)):
    """Resolved weather for one location code (city/airport/depot/port)."""
    w = weather_engine.weather_at(db, code.upper(), world_clock.now)
    w["impact"] = {
        "air": weather_engine.impact_for_mode("air", w),
        "road": weather_engine.impact_for_mode("road", w),
        "sea": weather_engine.impact_for_mode("sea", w),
    }
    return w


@router.post("/world/weather/override")
def set_weather_override(body: dict, db: Session = Depends(get_db)):
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
def clear_weather_overrides(body: dict = None, db: Session = Depends(get_db)):
    """Clear god overrides (optionally for one target)."""
    target = (body or {}).get("target")
    n = weather_engine.clear_overrides(db, target)
    return {"success": True, "cleared": n}


# ---------------------------------------------------------------------------
# World state (single snapshot for the God Panel)
# ---------------------------------------------------------------------------
@router.get("/world/state")
def get_world_state(db: Session = Depends(get_db)):
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
def get_world_shipments(db: Session = Depends(get_db)):
    """List through-shipment chains (multi-modal, e.g. sea -> road)."""
    from world.shipments import get_shipments
    shipments = get_shipments(db)
    return {"count": len(shipments), "shipments": shipments}


@router.get("/world/predictions")
def get_world_predictions(db: Session = Depends(get_db)):
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
def get_world_customers(q: Optional[str] = None, db: Session = Depends(get_db)):
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
def get_carrier_performance(
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
def get_world_metrics(
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
def get_world_tickets(limit: int = 500, db: Session = Depends(get_db)):
    """统一票视图：三种方式的票级数据合并（供 ETL / 报表 / 门户）。"""
    from sea_freight_models import CargoLine, SeaContainer
    from air_cargo_models import HouseWaybill, AirWaybill
    from road_freight_models import ConsignmentLine, RoadConsignment
    from rail_freight_models import RailConsignmentLine, RailConsignment
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

    for line in db.query(RailConsignmentLine).order_by(RailConsignmentLine.id.desc()).limit(limit).all():
        parent = db.query(RailConsignment).filter(
            RailConsignment.consignment_number == line.consignment_number).first()
        cust = db.query(Customer).filter(Customer.name == line.customer_name).first()
        tickets.append({
            "mode": "rail", "parent_reference": line.consignment_number,
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
def get_customer_contacts(limit: int = 50, db: Session = Depends(get_db)):
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
def record_customer_contact(body: dict, db: Session = Depends(get_db)):
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


@router.get("/world/tms-updates")
def get_tms_updates(limit: int = 50, db: Session = Depends(get_db)):
    """TMS/门户回写审计（Scenario 4: update the TMS and customer portal automatically）。"""
    from decision_models import TmsUpdate
    rows = db.query(TmsUpdate).order_by(TmsUpdate.id.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "updates": [
            {
                "update_id": u.update_id, "mode": u.mode, "exception_id": u.exception_id,
                "reference": u.reference, "target": u.target, "field": u.field,
                "old_value": u.old_value, "new_value": u.new_value, "status": u.status,
                "applied_at": u.applied_at.isoformat() if u.applied_at else None,
            }
            for u in rows
        ],
    }


@router.post("/world/tms-updates")
def record_tms_update(body: dict, db: Session = Depends(get_db)):
    """手动登记一次 TMS/门户回写（body: mode, exception_id, field, new_value, reference?, target?, old_value?, status?）。"""
    import uuid as _uuid
    from decision_models import TmsUpdate
    mode = body.get("mode")
    exception_id = body.get("exception_id")
    field = body.get("field")
    new_value = body.get("new_value")
    if not mode or not exception_id or not field or new_value is None:
        raise HTTPException(status_code=400, detail="mode, exception_id, field, new_value are required")
    row = TmsUpdate(
        update_id=f"TMS-{_uuid.uuid4().hex[:10]}",
        mode=mode, exception_id=exception_id,
        reference=body.get("reference"),
        target=body.get("target") or "tms",
        field=field, old_value=body.get("old_value"), new_value=str(new_value),
        status=body.get("status") or "applied",
        applied_at=world_clock.now,
    )
    db.add(row)
    db.commit()
    return {"success": True, "update": {
        "update_id": row.update_id, "mode": row.mode, "exception_id": row.exception_id,
        "field": row.field, "new_value": row.new_value, "status": row.status}}


@router.get("/world/notifications")
def get_world_notifications(
    review_status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """跨模式通知队列（COM-003 人工审核：review_status=pending_review 待审通知）。"""
    from notification_models import ExceptionNotification
    query = db.query(ExceptionNotification)
    if review_status:
        query = query.filter(ExceptionNotification.review_status == review_status)
    rows = query.order_by(ExceptionNotification.sent_at.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "notifications": [
            {
                "notification_id": n.notification_id, "mode": n.mode,
                "exception_id": n.exception_id, "reference": n.reference,
                "recipient": n.recipient, "channel": n.channel,
                "recipient_email": n.recipient_email, "recipient_phone": n.recipient_phone,
                "sent_status": n.sent_status, "review_status": n.review_status,
                "message": n.message, "edited_message": n.edited_message,
                "revised_eta": n.revised_eta.isoformat() if n.revised_eta else None,
                "sent_at": n.sent_at.isoformat(),
            }
            for n in rows
        ],
    }


@router.post("/notifications/{notification_id}/review")
def review_notification(notification_id: str, body: dict, db: Session = Depends(get_db)):
    """通知人工审核（COM-003）：body={action: approve|edit|reject, message?, reviewed_by}。"""
    from datetime import datetime as _dt
    from notification_models import ExceptionNotification
    n = db.query(ExceptionNotification).filter(
        ExceptionNotification.notification_id == notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="notification not found")
    from admin_models import require_role
    require_role(db, "review", body)
    action = body.get("action")
    if action not in ("approve", "edit", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve / edit / reject")
    n.reviewed_by = (body.get("reviewed_by") or "Coordinator").strip() or "Coordinator"
    n.reviewed_at = _dt.utcnow()
    if action == "approve":
        n.review_status = "approved"
    elif action == "edit":
        msg = body.get("message")
        if not msg:
            raise HTTPException(status_code=400, detail="message is required for edit")
        n.edited_message = msg
        n.review_status = "approved"
    elif action == "reject":
        n.review_status = "rejected"
    db.commit()
    return {
        "success": True,
        "notification_id": n.notification_id,
        "review_status": n.review_status,
        "edited_message": n.edited_message,
    }


@router.get("/world/quotes")
def get_world_quotes(
    exception_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """承运商报价列表（QTE-001/002：按异常查看并比较报价）。"""
    from quote_models import CarrierQuote
    query = db.query(CarrierQuote)
    if exception_id:
        query = query.filter(CarrierQuote.exception_id == exception_id)
    rows = query.order_by(CarrierQuote.quote_at.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "quotes": [
            {
                "quote_id": q.quote_id, "mode": q.mode, "exception_id": q.exception_id,
                "carrier": q.carrier, "service": q.service,
                "price_nzd": q.price_nzd, "currency": q.currency,
                "surcharges_nzd": q.surcharges_nzd, "capacity_note": q.capacity_note,
                "new_eta": q.new_eta.isoformat() if q.new_eta else None,
                "valid_until": q.valid_until.isoformat() if q.valid_until else None,
                "status": q.status, "version": q.version, "note": q.note,
                "quote_at": q.quote_at.isoformat() if q.quote_at else None,
            }
            for q in rows
        ],
    }


@router.post("/world/quotes")
def create_world_quote(body: dict, db: Session = Depends(get_db)):
    """人工录入承运商报价（QTE-001）：body={mode, exception_id, carrier, price_nzd, service, new_eta, note, ...}。"""
    from quote_models import create_quote
    from admin_models import require_role
    require_role(db, "quotes", body)
    try:
        row = create_quote(db, body, world_clock.now)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "quote_id": row.quote_id, "version": row.version,
            "status": row.status, "carrier": row.carrier, "price_nzd": row.price_nzd}


@router.post("/world/quotes/{quote_id}/select")
def select_world_quote(quote_id: str, db: Session = Depends(get_db)):
    """选择报价（QTE-002：其余报价置为 rejected）。"""
    from quote_models import select_quote
    from admin_models import require_role
    require_role(db, "quotes", {"by": "Coordinator"})
    try:
        q = select_quote(db, quote_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "quote_id": q.quote_id, "status": q.status,
            "exception_id": q.exception_id}


@router.get("/world/users")
def get_world_users(db: Session = Depends(get_db)):
    """用户与角色（ADM-001 简化 RBAC）。"""
    from admin_models import User, ROLE_LABEL
    rows = db.query(User).order_by(User.name).all()
    return {
        "count": len(rows),
        "users": [
            {"user_id": u.user_id, "name": u.name, "role": u.role,
             "role_label": ROLE_LABEL.get(u.role, u.role), "team": u.team, "active": u.active}
            for u in rows
        ],
    }


@router.get("/world/network-events")
def get_world_network_events(db: Session = Depends(get_db)):
    """网络事件编组（EVT-008）：活跃天气/港口/线路事件 → 受影响班次、货物与客户。"""
    from environment_models import EnvironmentEvent
    from world.predict import PredictedImpact
    from rail_freight_models import RailConsignment
    from road_freight_models import RoadConsignment
    from air_cargo_models import AirWaybill
    from sea_freight_models import SeaContainer

    active = db.query(EnvironmentEvent).filter(
        EnvironmentEvent.ends_at >= world_clock.now).all()
    events = []
    for ev in active:
        preds = db.query(PredictedImpact).filter(
            PredictedImpact.event_id == ev.id).all()
        customers = set()
        references = []
        for p in preds:
            references.append(p.reference)
            if p.mode == "air":
                for w in db.query(AirWaybill).filter(AirWaybill.flight_number == p.reference).limit(200).all():
                    customers.add(w.customer_name)
            elif p.mode == "road":
                for c in db.query(RoadConsignment).filter(RoadConsignment.trip_number == p.reference).limit(200).all():
                    customers.add(c.customer_name)
            elif p.mode == "sea":
                for c in db.query(SeaContainer).filter(SeaContainer.vessel_visit_id == p.reference).limit(200).all():
                    customers.add(c.customer_name)
            elif p.mode == "rail":
                for c in db.query(RailConsignment).filter(RailConsignment.train_number == p.reference).limit(200).all():
                    customers.add(c.customer_name)
        events.append({
            "event_id": ev.id, "mode": ev.mode, "event_type": ev.event_type,
            "location": ev.location, "severity": ev.severity,
            "description": ev.description,
            "impact_at": ev.impact_at.isoformat() if ev.impact_at else None,
            "ends_at": ev.ends_at.isoformat(),
            "affected_movements": len(preds),
            "affected_customers": len(customers),
            "customers": sorted(customers)[:20],
            "references": references[:20],
        })
    return {"count": len(events), "events": events}


@router.post("/world/network-events/{event_id}/notify")
def batch_notify_network_event(event_id: int, body: dict, db: Session = Depends(get_db)):
    """批量处置（EVT-008）：把一个网络事件关联的待审通知批量批准外发。"""
    from admin_models import require_role
    require_role(db, "review", body)
    from world.predict import PredictedImpact
    from notification_models import ExceptionNotification
    from rail_freight_models import RailConsignment, RailException
    from road_freight_models import RoadConsignment, RoadException
    from air_cargo_models import AirWaybill, AirException
    from sea_freight_models import SeaContainer, SeaException

    preds = db.query(PredictedImpact).filter(
        PredictedImpact.event_id == event_id).all()
    exception_ids = []
    customers = set()
    for p in preds:
        ref = p.reference
        if p.mode == "air":
            awbs = [w.awb_number for w in db.query(AirWaybill).filter(AirWaybill.flight_number == ref).limit(300).all()]
            for a in awbs:
                customers.add(a)
            for chunk in [awbs[i:i + 300] for i in range(0, len(awbs), 300)]:
                if chunk:
                    exception_ids += [x.exception_id for x in db.query(AirException).filter(
                        AirException.awb_number.in_(chunk)).all()]
        elif p.mode == "road":
            cons = [c.consignment_number for c in db.query(RoadConsignment).filter(RoadConsignment.trip_number == ref).limit(300).all()]
            for c in cons:
                customers.add(c)
            for chunk in [cons[i:i + 300] for i in range(0, len(cons), 300)]:
                if chunk:
                    exception_ids += [x.exception_id for x in db.query(RoadException).filter(
                        RoadException.consignment_number.in_(chunk)).all()]
        elif p.mode == "sea":
            cns = [c.container_number for c in db.query(SeaContainer).filter(SeaContainer.vessel_visit_id == ref).limit(300).all()]
            for c in cns:
                customers.add(c)
            for chunk in [cns[i:i + 300] for i in range(0, len(cns), 300)]:
                if chunk:
                    exception_ids += [x.exception_id for x in db.query(SeaException).filter(
                        SeaException.container_number.in_(chunk)).all()]
        elif p.mode == "rail":
            cons = [c.consignment_number for c in db.query(RailConsignment).filter(RailConsignment.train_number == ref).limit(300).all()]
            for c in cons:
                customers.add(c)
            for chunk in [cons[i:i + 300] for i in range(0, len(cons), 300)]:
                if chunk:
                    exception_ids += [x.exception_id for x in db.query(RailException).filter(
                        RailException.consignment_number.in_(chunk)).all()]

    approved = 0
    for chunk in [exception_ids[i:i + 300] for i in range(0, len(exception_ids), 300)]:
        if not chunk:
            continue
        n = db.query(ExceptionNotification).filter(
            ExceptionNotification.exception_id.in_(chunk),
            ExceptionNotification.review_status == "pending_review",
        ).update(
            {"review_status": "approved",
             "reviewed_by": (body.get("by") or "System"),
             "edited_message": "批量处置：网络事件影响范围内通知已统一批准外发"},
            synchronize_session=False,
        )
        approved += n
    db.commit()
    return {"success": True, "event_id": event_id,
            "affected_movements": len(preds),
            "affected_customers": len(customers),
            "notifications_approved": approved}


@router.post("/notifications/{notification_id}/delivery")
def mark_notification_delivery(notification_id: str, body: dict, db: Session = Depends(get_db)):
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

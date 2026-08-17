"""
Exception disposition ops - manual confirm / false-positive / close / reopen (EVT-006, MON-005).
异常处置操作：人工确认、误报/重复标记、关闭与重新打开、人工创建异常。
"""
from datetime import datetime

from event_classifier import RECOVERY_PLAYBOOK

DISPOSITIONS = ("confirmed", "false_positive", "duplicate", "data_issue")


def _locked(fn):
    """API 路径与模拟器线程共用写锁，避免 sqlite database is locked。"""
    from database import WRITE_LOCK
    def wrapper(*args, **kwargs):
        with WRITE_LOCK:
            return fn(*args, **kwargs)
    return wrapper


def _exception_model(mode):
    if mode == "sea":
        from sea_freight_models import SeaException
        return SeaException
    if mode == "air":
        from air_cargo_models import AirException
        return AirException
    if mode == "road":
        from road_freight_models import RoadException
        return RoadException
    if mode == "rail":
        from rail_freight_models import RailException
        return RailException
    raise ValueError(f"unknown mode: {mode}")


def _parent_by_reference(db, mode, reference):
    if mode == "sea":
        from sea_freight_models import SeaContainer
        return db.query(SeaContainer).filter(SeaContainer.container_number == reference).first()
    if mode == "air":
        from air_cargo_models import AirWaybill
        return db.query(AirWaybill).filter(AirWaybill.awb_number == reference).first()
    if mode == "road":
        from road_freight_models import RoadConsignment
        return db.query(RoadConsignment).filter(RoadConsignment.consignment_number == reference).first()
    if mode == "rail":
        from rail_freight_models import RailConsignment
        return db.query(RailConsignment).filter(RailConsignment.consignment_number == reference).first()
    return None


@_locked
def set_disposition(db, mode, exception_id, body, now):
    """标记异常为 confirmed / false_positive / duplicate / data_issue 并关闭案件。"""
    cls = _exception_model(mode)
    exc = db.query(cls).filter(cls.exception_id == exception_id).first()
    if not exc:
        raise ValueError("exception not found")
    disposition = body.get("disposition")
    if disposition not in DISPOSITIONS:
        raise ValueError(f"disposition must be one of {DISPOSITIONS}")
    from admin_models import require_role, is_high_risk_action
    name, _role = require_role(db, "disposition", body,
                               high_risk=is_high_risk_action(db, exc))
    exc.disposition = disposition
    exc.disposition_note = body.get("note")
    exc.disposition_by = name
    exc.disposition_at = now
    exc.status = "closed"
    exc.closed_at = now
    db.commit()
    return exc


@_locked
def close_exception(db, mode, exception_id, body, now):
    """人工结案（正常关闭）：需提供客观证据。"""
    cls = _exception_model(mode)
    exc = db.query(cls).filter(cls.exception_id == exception_id).first()
    if not exc:
        raise ValueError("exception not found")
    from admin_models import require_role
    name, _role = require_role(db, "close", body)
    exc.status = "closed"
    exc.closed_at = now
    exc.close_evidence = body.get("evidence") or body.get("note")
    exc.disposition = exc.disposition or "confirmed"
    exc.disposition_by = exc.disposition_by or name
    db.commit()
    return exc


@_locked
def reopen_exception(db, mode, exception_id, now):
    """二次异常：重新打开案件并保留原时间线。"""
    cls = _exception_model(mode)
    exc = db.query(cls).filter(cls.exception_id == exception_id).first()
    if not exc:
        raise ValueError("exception not found")
    from admin_models import require_role
    require_role(db, "reopen", {"by": "Coordinator"})
    exc.status = "reopened"
    exc.reopen_count = (exc.reopen_count or 0) + 1
    exc.closed_at = None
    db.commit()
    return exc


def reopen_if_closed(db, mode, reference, now):
    """MON-002 二次偏差重评估：该装载单元已有 closed 案件时自动重新打开（保留原时间线）。"""
    cls = _exception_model(mode)
    if mode == "sea":
        closed = db.query(cls).filter(cls.container_number == reference, cls.status == "closed").all()
    elif mode == "air":
        closed = db.query(cls).filter(cls.awb_number == reference, cls.status == "closed").all()
    else:
        closed = db.query(cls).filter(cls.consignment_number == reference, cls.status == "closed").all()
    for exc in closed:
        exc.status = "reopened"
        exc.reopen_count = (exc.reopen_count or 0) + 1
        exc.escalation_reason = (exc.escalation_reason or "") + f"；{now:%m-%d %H:%M} 二次偏差自动重开"
        db.add(exc)
    return len(closed)


@_locked
def create_manual_exception(db, mode, body, now):
    """人工创建异常：绑定现有装载单元，走完整风险/分类/方案/通知流程。"""
    reference = (body.get("reference") or "").strip()
    if not reference:
        raise ValueError("reference is required")
    parent = _parent_by_reference(db, mode, reference)
    if not parent:
        raise ValueError(f"parent unit not found: {reference}")
    from admin_models import require_role
    require_role(db, "create_exception", body)
    exc_type = body.get("exception_type") or "delay"
    root_cause = (body.get("root_cause") or f"Manual exception created for {reference}").strip()
    diagnosis = body.get("diagnosis") or body.get("note") or root_cause
    recovery = ["monitor"]

    if mode == "sea":
        from sea_freight_simulator import simulator
        sim = simulator
        parent_cls = _parent_by_reference(db, "sea", reference)
        sim._create_exception(db, parent_cls, exc_type, root_cause, 0.0, diagnosis, recovery)
    elif mode == "air":
        from air_cargo_simulator import simulator
        sim = simulator
        sim._create_exception(db, parent, exc_type, root_cause, 0.0, diagnosis, recovery)
    elif mode == "road":
        from road_freight_simulator import simulator
        sim = simulator
        sim._create_exception(db, parent, exc_type, root_cause, 0.0, diagnosis, recovery)
    elif mode == "rail":
        from rail_freight_simulator import simulator
        sim = simulator
        sim._create_exception(db, parent, exc_type, root_cause, 0.0, diagnosis, recovery)
    else:
        raise ValueError(f"unknown mode: {mode}")
    db.commit()
    return exc_type, reference

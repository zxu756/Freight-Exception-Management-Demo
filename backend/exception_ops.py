"""
Exception disposition ops - manual confirm / false-positive / close / reopen (EVT-006, MON-005).
异常处置操作：人工确认、误报/重复标记、关闭与重新打开、人工创建异常。
"""
from datetime import datetime

from event_classifier import RECOVERY_PLAYBOOK

DISPOSITIONS = ("confirmed", "false_positive", "duplicate", "data_issue")


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


def set_disposition(db, mode, exception_id, body, now):
    """标记异常为 confirmed / false_positive / duplicate / data_issue 并关闭案件。"""
    cls = _exception_model(mode)
    exc = db.query(cls).filter(cls.exception_id == exception_id).first()
    if not exc:
        raise ValueError("exception not found")
    disposition = body.get("disposition")
    if disposition not in DISPOSITIONS:
        raise ValueError(f"disposition must be one of {DISPOSITIONS}")
    exc.disposition = disposition
    exc.disposition_note = body.get("note")
    exc.disposition_by = (body.get("by") or "Coordinator").strip() or "Coordinator"
    exc.disposition_at = now
    exc.status = "closed"
    exc.closed_at = now
    db.commit()
    return exc


def close_exception(db, mode, exception_id, body, now):
    """人工结案（正常关闭）：需提供客观证据。"""
    cls = _exception_model(mode)
    exc = db.query(cls).filter(cls.exception_id == exception_id).first()
    if not exc:
        raise ValueError("exception not found")
    exc.status = "closed"
    exc.closed_at = now
    exc.close_evidence = body.get("evidence") or body.get("note")
    exc.disposition = exc.disposition or "confirmed"
    db.commit()
    return exc


def reopen_exception(db, mode, exception_id, now):
    """二次异常：重新打开案件并保留原时间线。"""
    cls = _exception_model(mode)
    exc = db.query(cls).filter(cls.exception_id == exception_id).first()
    if not exc:
        raise ValueError("exception not found")
    exc.status = "reopened"
    exc.reopen_count = (exc.reopen_count or 0) + 1
    exc.closed_at = None
    db.commit()
    return exc


def create_manual_exception(db, mode, body, now):
    """人工创建异常：绑定现有装载单元，走完整风险/分类/方案/通知流程。"""
    reference = (body.get("reference") or "").strip()
    if not reference:
        raise ValueError("reference is required")
    parent = _parent_by_reference(db, mode, reference)
    if not parent:
        raise ValueError(f"parent unit not found: {reference}")
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

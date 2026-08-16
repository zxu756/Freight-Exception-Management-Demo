"""
Carrier quote model (QTE-001/002/003) - manual quote entry for recovery plans.
承运商报价模型：人工录入报价、版本与选择状态。
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from database import Base


class CarrierQuote(Base):
    """One carrier quote attached to an exception (manual entry)."""
    __tablename__ = "carrier_quotes"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(String(50), unique=True, nullable=False, index=True)
    mode = Column(String(10), nullable=False, index=True)  # sea/air/road/rail
    exception_id = Column(String(50), nullable=False, index=True)
    carrier = Column(String(100), nullable=False)
    service = Column(String(100), nullable=True)  # 服务描述，如 "Air express - next flight"
    price_nzd = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="NZD")
    surcharges_nzd = Column(Float, nullable=True)  # 附加费
    capacity_note = Column(String(200), nullable=True)  # 容量/可用性说明
    new_eta = Column(DateTime, nullable=True)  # 模拟世界时间
    valid_until = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="received")  # received/selected/expired/rejected
    version = Column(Integer, nullable=False, default=1)  # 版本（重新询价时 +1）
    note = Column(Text, nullable=True)
    quote_at = Column(DateTime, nullable=False)  # 模拟世界时间
    created_at = Column(DateTime, default=datetime.utcnow)


def _parse_dt(v):
    """ISO 字符串 → naive datetime（SQLite DateTime 只收 datetime 对象）。"""
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return v


def create_quote(db, body, now):
    """人工录入报价；同一异常重复询价时版本 +1。"""
    mode = body.get("mode")
    exception_id = body.get("exception_id")
    carrier = (body.get("carrier") or "").strip()
    price = body.get("price_nzd")
    if not mode or not exception_id or not carrier or price is None:
        raise ValueError("mode, exception_id, carrier, price_nzd are required")
    latest = db.query(CarrierQuote).filter(
        CarrierQuote.mode == mode,
        CarrierQuote.exception_id == exception_id,
    ).order_by(CarrierQuote.version.desc()).first()
    version = (latest.version + 1) if latest else 1
    row = CarrierQuote(
        quote_id=f"QTE-{uuid.uuid4().hex[:10]}",
        mode=mode, exception_id=exception_id, carrier=carrier,
        service=body.get("service"), price_nzd=float(price),
        currency=body.get("currency") or "NZD",
        surcharges_nzd=body.get("surcharges_nzd"),
        capacity_note=body.get("capacity_note"),
        new_eta=_parse_dt(body.get("new_eta")), valid_until=_parse_dt(body.get("valid_until")),
        version=version, note=body.get("note"), quote_at=now,
    )
    db.add(row)
    db.commit()
    return row


def select_quote(db, quote_id):
    """选择报价（其它报价置为 rejected，选中报价置为 selected）。"""
    q = db.query(CarrierQuote).filter(CarrierQuote.quote_id == quote_id).first()
    if not q:
        raise ValueError("quote not found")
    db.query(CarrierQuote).filter(
        CarrierQuote.mode == q.mode,
        CarrierQuote.exception_id == q.exception_id,
    ).update({"status": "rejected"}, synchronize_session=False)
    q.status = "selected"
    db.commit()
    return q

"""
Workflow models - audit log (ADM-006) and carrier instructions (EXE-002/003).
工作流模型：审计日志 + 承运商执行指令。
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from database import Base


class AuditLog(Base):
    """完整审计日志（谁在何时对什么做了什么，含修改前后值）。"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String(50), unique=True, nullable=False, index=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # decision/disposition/close/reopen/review/quote/tms/sync
    mode = Column(String(10), nullable=True)
    exception_id = Column(String(50), nullable=True, index=True)
    reference = Column(String(50), nullable=True)
    field = Column(String(50), nullable=True)
    old_value = Column(String(200), nullable=True)
    new_value = Column(String(200), nullable=True)
    note = Column(Text, nullable=True)
    happened_at = Column(DateTime, nullable=False)  # 模拟世界时间
    created_at = Column(DateTime, default=datetime.utcnow)


def log_audit(db, actor, action, happened_at, mode=None, exception_id=None,
               reference=None, field=None, old_value=None, new_value=None, note=None):
    """写一条审计记录（幂等友好：直接插入）。"""
    db.add(AuditLog(
        audit_id=f"AUD-{uuid.uuid4().hex[:10]}",
        actor=actor, action=action, mode=mode, exception_id=exception_id,
        reference=reference, field=field, old_value=old_value, new_value=new_value,
        note=note, happened_at=happened_at,
    ))


class CarrierInstruction(Base):
    """承运商执行指令（EXE-002/003）：批准方案 → 指令 → 发送 → 确认/失败/重试。"""
    __tablename__ = "carrier_instructions"

    id = Column(Integer, primary_key=True, index=True)
    instruction_id = Column(String(50), unique=True, nullable=False, index=True)
    mode = Column(String(10), nullable=False)
    exception_id = Column(String(50), nullable=False, index=True)
    reference = Column(String(50), nullable=True)
    carrier = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # 批准/修改后执行的恢复行动
    instruction_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="drafted")  # drafted/sent/confirmed/failed
    external_ref = Column(String(100), nullable=True)  # 订舱号/确认号
    final_cost_nzd = Column(Float, nullable=True)  # 承运商确认的最终费用
    confirmed_eta = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def create_instruction(db, mode, exception_id, reference, carrier, action, now):
    """审批通过时自动生成承运商指令（drafted）。"""
    from event_classifier import ACTION_META
    label = ACTION_META.get(action, (action, "", 1.0))[0]
    row = CarrierInstruction(
        instruction_id=f"INS-{uuid.uuid4().hex[:10]}",
        mode=mode, exception_id=exception_id, reference=reference, carrier=carrier,
        action=action,
        instruction_text=f"按已批准方案执行 {label}（{action}），请确认费用与新的 ETA。",
        status="drafted", created_at=datetime.utcnow(),
    )
    db.add(row)
    return row

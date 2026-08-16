"""
Coordinator decision records + learned action preferences (Scenario 4 P0).
协调员决策记录 + 从历史决策学习恢复行动偏好。

- ExceptionDecision: 每次人工审批/驳回/修改都留档（谁、何时、怎么批、耗时）。
- DecisionStat: 按 (异常分类, 行动) 聚合的采纳/驳回次数，供 AI 排序加分。
- record_decision: 决策入口 —— 更新异常状态为 resolved 并写实际执行结果。
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from database import Base
from event_classifier import ACTION_COST, ACTION_META


class ExceptionDecision(Base):
    """One human decision on one exception (approve / reject / modify)."""
    __tablename__ = "exception_decisions"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(String(50), unique=True, nullable=False, index=True)
    mode = Column(String(10), nullable=False, index=True)  # sea / air / road
    exception_id = Column(String(50), nullable=False, index=True)
    decided_by = Column(String(100), nullable=False, default="Coordinator")
    decision = Column(String(20), nullable=False)  # approve / reject / modify
    chosen_action = Column(String(50), nullable=True)  # 最终执行的行动（reject 时为空）
    note = Column(Text, nullable=True)
    decision_latency_minutes = Column(Float, nullable=True)  # 检测 → 决策 的耗时
    decided_at = Column(DateTime, nullable=False)  # 模拟世界时间
    created_at = Column(DateTime, default=datetime.utcnow)  # 真实时间


class DecisionStat(Base):
    """Aggregated (category, action) acceptance counts for preference learning."""
    __tablename__ = "decision_stats"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    chosen_count = Column(Integer, default=0)  # 采纳（approve 或 modify 选它）
    rejected_count = Column(Integer, default=0)  # 驳回/被改掉
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def apply_learned_preferences(db, category):
    """把历史协调员偏好转成排序加分：{action: bonus}

    采纳率 >= 2 次样本且采纳率越高加分越多（上限 +1.5 分），
    这样 AI 推荐会逐渐向协调员实际偏好收敛。
    """
    if not category:
        return {}
    bonus = {}
    for s in db.query(DecisionStat).filter(DecisionStat.category == category).all():
        total = s.chosen_count + s.rejected_count
        if total >= 2 and s.chosen_count > 0:
            bonus[s.action] = round(min(1.5, 1.5 * s.chosen_count / total), 2)
    return bonus


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
    raise ValueError(f"unknown mode: {mode}")


def record_decision(db, mode, exception_id, body, now):
    """记录一次协调员决策，更新异常为已解决并写入实际执行结果。

    body: {decided_by, decision: approve|reject|modify, chosen_action, note,
           actual_cost, actual_recovery_hours}
    返回 (decision_row, exception_row) 或抛 ValueError/KeyError。
    """
    cls = _exception_model(mode)
    exc = db.query(cls).filter(cls.exception_id == exception_id).first()
    if not exc:
        raise ValueError(f"exception not found: {mode}/{exception_id}")

    decision = body.get("decision")
    if decision not in ("approve", "reject", "modify"):
        raise ValueError("decision must be approve / reject / modify")

    decided_by = (body.get("decided_by") or "Coordinator").strip() or "Coordinator"
    chosen = body.get("chosen_action")
    if decision == "reject":
        chosen = None
    if decision in ("approve", "modify") and not chosen:
        chosen = exc.recommended_action

    latency = None
    if exc.detected_at:
        latency = round((now - exc.detected_at).total_seconds() / 60.0, 1)

    row = ExceptionDecision(
        decision_id=f"DEC-{uuid.uuid4().hex[:10]}",
        mode=mode, exception_id=exception_id, decided_by=decided_by,
        decision=decision, chosen_action=chosen, note=body.get("note"),
        decision_latency_minutes=latency, decided_at=now,
    )
    db.add(row)

    # 更新异常：已解决 + 实际执行结果（Scenario 4: 行动执行留痕）
    exc.status = "resolved"
    exc.resolved_at = now
    if chosen:
        exc.actual_action = chosen
        exc.actual_cost = body.get("actual_cost") or ACTION_COST.get(chosen, exc.recovery_cost or 200)
        if body.get("actual_recovery_hours") is not None:
            exc.actual_recovery_hours = body["actual_recovery_hours"]
        else:
            _, _, impact_h = ACTION_META.get(chosen, (chosen, "", 1.0))
            exc.actual_recovery_hours = impact_h

    # 学习：采纳/驳回计数
    category = exc.exception_category or "Delay"
    recommended = exc.recommended_action
    stats = {}
    for s in db.query(DecisionStat).filter(DecisionStat.category == category).all():
        stats[s.action] = s
    def bump(action, chosen_delta, rejected_delta):
        if not action:
            return
        s = stats.get(action)
        if not s:
            s = DecisionStat(category=category, action=action, chosen_count=0, rejected_count=0)
            db.add(s)
            stats[action] = s
        s.chosen_count += chosen_delta
        s.rejected_count += rejected_delta
    if decision == "approve" and chosen == recommended:
        bump(chosen, 1, 0)
    elif decision == "approve" and chosen != recommended:
        bump(chosen, 1, 0)
        bump(recommended, 0, 1)
    elif decision == "modify" and chosen != recommended:
        bump(chosen, 1, 0)
        bump(recommended, 0, 1)
    elif decision == "modify":
        bump(chosen, 1, 0)
    elif decision == "reject":
        bump(recommended, 0, 1)

    db.commit()
    return row, exc


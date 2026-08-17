"""
SLA policy model and breach determination logic.
SLA 策略模型与违约判定逻辑

基于 Kratos SLA 基准文档：SLA 由「服务等级 × 运输方式」决定交付时限承诺，
违约分为 excused（排除项，不计 OTD 但不免通知）与 unexcused（正式违约）。
异常响应时限按严重度 P1-P4 分级，VIP/high 客户自动提升一级。
"""
from datetime import timedelta
from sqlalchemy import Column, Integer, String, Float
from database import Base


class SlaPolicy(Base):
    """SLA delivery commitment: mode × service_level → transit/grace/OTD target/penalty."""
    __tablename__ = "sla_policies"

    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String(10), nullable=False, index=True)  # 'sea', 'road', 'air'
    service_level = Column(String(20), nullable=False)  # 'priority', 'standard', 'economy'
    transit_hours = Column(Float, nullable=False)  # 交付时限承诺（小时）
    grace_hours = Column(Float, nullable=False)  # 宽限期（小时）
    on_time_target = Column(Float, nullable=False)  # OTD 目标（0.98 = 98%）
    penalty_pct = Column(Float, nullable=False)  # 违约金比例（0.05 = 5%）


# 默认策略（与 sla_seed 一致；模拟器生成货物时直接引用，避免高频查 DB）
DEFAULT_POLICIES = {
    ("air", "priority"): {"transit_hours": 8, "grace_hours": 1, "on_time_target": 0.98, "penalty_pct": 0.05},
    ("air", "standard"): {"transit_hours": 24, "grace_hours": 2, "on_time_target": 0.95, "penalty_pct": 0.03},
    ("air", "economy"): {"transit_hours": 48, "grace_hours": 4, "on_time_target": 0.90, "penalty_pct": 0.01},
    ("road", "priority"): {"transit_hours": 6, "grace_hours": 1, "on_time_target": 0.98, "penalty_pct": 0.05},
    ("road", "standard"): {"transit_hours": 18, "grace_hours": 2, "on_time_target": 0.95, "penalty_pct": 0.03},
    ("road", "economy"): {"transit_hours": 36, "grace_hours": 4, "on_time_target": 0.90, "penalty_pct": 0.01},
    ("sea", "priority"): {"transit_hours": 60, "grace_hours": 1, "on_time_target": 0.98, "penalty_pct": 0.05},
    ("sea", "standard"): {"transit_hours": 120, "grace_hours": 2, "on_time_target": 0.95, "penalty_pct": 0.03},
    ("sea", "economy"): {"transit_hours": 180, "grace_hours": 4, "on_time_target": 0.90, "penalty_pct": 0.01},
}


def get_policy(mode, service_level):
    """Return the SLA policy dict for a mode + service_level (with a standard fallback)."""
    return DEFAULT_POLICIES.get((mode, service_level), DEFAULT_POLICIES.get((mode, "standard"), {"transit_hours": 24, "grace_hours": 2, "on_time_target": 0.95, "penalty_pct": 0.03}))


# 排除项（excused）：不计 OTD 违约，但不免除检测/通知/更新义务
EXCLUDED_REASON_CODES = {"weather", "road_closure", "ferry"}
EXCLUDED_EXCEPTION_TYPES = {"customs_hold", "biosecurity_hold", "dg_incident", "overweight"}

# 异常严重度 → P 级别
SEVERITY_TO_PRIORITY = {
    "critical": "P1",
    "high": "P2",
    "medium": "P3",
    "low": "P4",
}

# P 级别响应时限（检测分钟 / 通知分钟 / 更新小时；None = 按需）
PRIORITY_RESPONSE = {
    "P1": {"detect_minutes": 15, "notify_minutes": 30, "update_hours": 2},
    "P2": {"detect_minutes": 15, "notify_minutes": 60, "update_hours": 4},
    "P3": {"detect_minutes": 30, "notify_minutes": 240, "update_hours": 24},
    "P4": {"detect_minutes": 120, "notify_minutes": None, "update_hours": None},
}

# 客户等级 → 响应级别提升（VIP/high 的异常按更高级别响应）
TIER_PROMOTION = {"VIP": 1, "high": 1, "medium": 0, "low": 0}

# service_level 原始值 → 统一 tier 名
_SERVICE_LEVEL_MAP = {
    "express": "priority", "same_day": "priority",
    "standard": "standard", "charter": "economy", "economy": "economy",
}


def map_service_level_to_tier(service_level):
    """Map a raw service_level value to a unified SLA tier (priority/standard/economy)."""
    return _SERVICE_LEVEL_MAP.get(service_level or "", "standard")


def is_excused(exception_type, reason_code):
    """Return True if the breach reason is an excused exclusion (weather/customs/closure)."""
    return reason_code in EXCLUDED_REASON_CODES or exception_type in EXCLUDED_EXCEPTION_TYPES


def determine_breach(delivered_at, sla_deadline, grace_hours, exception_type=None, reason_code=None):
    """
    Determine SLA breach status for a delivered shipment.

    Returns:
        (is_breached: bool, breach_type: 'excused' | 'unexcused' | None)
    """
    if delivered_at is None or sla_deadline is None:
        return False, None
    if delivered_at <= sla_deadline:
        return False, None
    if is_excused(exception_type, reason_code):
        return False, "excused"
    if delivered_at <= sla_deadline + timedelta(hours=grace_hours):
        return False, None  # within grace period, not a formal breach
    return True, "unexcused"


def get_priority(severity, customer_tier):
    """Map severity + customer_tier to a P1-P4 response level (VIP/high promote one level)."""
    base = SEVERITY_TO_PRIORITY.get(severity, "P4")
    order = ["P4", "P3", "P2", "P1"]  # low → high
    idx = order.index(base) + TIER_PROMOTION.get(customer_tier, 0)
    return order[min(idx, len(order) - 1)]


def estimate_penalty(cargo_value, penalty_pct):
    """Estimate service credit / penalty = cargo value × penalty_pct."""
    return round((cargo_value or 0) * penalty_pct, 2)


def evaluate_breach(delivered_at, sla_deadline, grace_hours, penalty_pct, cargo_value, excused=False):
    """
    Evaluate SLA breach on delivery.

    Returns:
        (is_breached: bool, breach_type: 'excused' | 'unexcused' | None, penalty: float | None)
    """
    if delivered_at is None or sla_deadline is None:
        return False, None, None
    if delivered_at <= sla_deadline:
        return False, None, None
    if excused:
        return False, "excused", None
    if delivered_at <= sla_deadline + timedelta(hours=grace_hours):
        return False, None, None  # within grace period
    return True, "unexcused", estimate_penalty(cargo_value, penalty_pct)

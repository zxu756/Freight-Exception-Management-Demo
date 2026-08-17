"""
Minimal RBAC (ADM-001 simplified) - users, roles and permission checks.
简化 RBAC：用户/角色 + 敏感操作权限校验。
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base


class User(Base):
    """One operator account (demo RBAC)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # planner / manager / admin / cs / analyst
    team = Column(String(50), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


DEFAULT_USERS = [
    ("U-ALICE", "Coordinator Alice", "planner", "Sea Team"),
    ("U-BOB", "Manager Bob", "manager", "Ops Management"),
    ("U-CAROL", "CS Manager Carol", "cs", "Customer Service"),
    ("U-DAVE", "Admin Dave", "admin", "Platform"),
    ("U-EVE", "Analyst Eve", "analyst", "BI"),
]

ROLE_LABEL = {"planner": "协调员", "manager": "经理", "cs": "客服", "admin": "管理员", "analyst": "分析师"}

_ALLOWED = {
    "decision": ("planner", "manager"),
    "disposition": ("planner", "manager"),
    "close": ("planner", "manager"),
    "reopen": ("planner", "manager"),
    "review": ("cs", "manager"),
    "quotes": ("planner", "manager"),
    "create_exception": ("planner", "manager"),
}

_MANAGER_ONLY_HIGH = ("manager", "admin")  # 高风险/高成本动作需经理及以上


def seed_users(db):
    for uid, name, role, team in DEFAULT_USERS:
        if not db.query(User).filter(User.user_id == uid).first():
            db.add(User(user_id=uid, name=name, role=role, team=team))
    db.commit()


def get_user(db, user_key):
    """按 user_id 或姓名找用户（找不到返回 None）。"""
    if not user_key:
        return None
    return (db.query(User).filter(User.user_id == user_key).first()
           or db.query(User).filter(User.name == user_key).first())


def resolve_actor(db, body, default_name="Coordinator"):
    """从请求体/请求头解析操作人：返回 (display_name, role 或 None)。

    传入 user/user_id/decided_by/by/reviewed_by 任一字段均可；找不到则用默认名、角色 None（宽松兼容）。
    """
    key = (body.get("user") or body.get("user_id") or body.get("decided_by")
           or body.get("by") or body.get("reviewed_by") or body.get("actor"))
    u = get_user(db, key) if key else None
    if u:
        return u.name, u.role
    return (key or default_name).strip() or default_name, None


def require_role(db, action, body, high_risk=False, default_name="Coordinator"):
    """校验操作人角色；无角色信息时放行（旧客户端兼容），有角色则按矩阵校验。
    返回 (display_name, role)。权限不足抛 PermissionError。
    """
    name, role = resolve_actor(db, body, default_name)
    if role is None:
        return name, role
    allowed = _ALLOWED.get(action, ())
    if role not in allowed:
        raise PermissionError(f"role {role} cannot perform {action}")
    if high_risk and role not in _MANAGER_ONLY_HIGH:
        raise PermissionError(f"{action} on high-risk/high-value case requires manager or admin")
    return name, role


def is_high_risk_action(db, exc):
    """APR-001/002 简化审批矩阵：高风险或高成本动作需经理审批。"""
    if exc and getattr(exc, "risk_level", None) == "high":
        return True
    cost = getattr(exc, "recovery_cost", None) or 0
    return cost >= 2000

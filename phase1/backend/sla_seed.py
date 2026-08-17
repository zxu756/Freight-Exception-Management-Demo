"""
SLA policy seed data - initial transit commitments per mode × service level.
SLA 策略初始数据 - 按运输方式 × 服务等级的交付时限承诺

Values are based on the Kratos SLA benchmark report (NZ + global benchmarks).
"""
from database import engine, Base, SessionLocal
from sla_models import SlaPolicy

# (mode, service_level, transit_hours, grace_hours, on_time_target, penalty_pct)
POLICIES = [
    # 空运
    ("air", "priority", 8, 1, 0.98, 0.05),
    ("air", "standard", 24, 2, 0.95, 0.03),
    ("air", "economy", 48, 4, 0.90, 0.01),
    # 陆运
    ("road", "priority", 6, 1, 0.98, 0.05),
    ("road", "standard", 18, 2, 0.95, 0.03),
    ("road", "economy", 36, 4, 0.90, 0.01),
    # 海运
    ("sea", "priority", 60, 1, 0.98, 0.05),
    ("sea", "standard", 120, 2, 0.95, 0.03),
    ("sea", "economy", 180, 4, 0.90, 0.01),
]


def seed_sla_policies(db):
    """Seed initial SLA policies (idempotent)."""
    for mode, level, transit, grace, ot, penalty in POLICIES:
        exists = db.query(SlaPolicy).filter(
            SlaPolicy.mode == mode, SlaPolicy.service_level == level).first()
        if not exists:
            db.add(SlaPolicy(
                mode=mode, service_level=level, transit_hours=transit,
                grace_hours=grace, on_time_target=ot, penalty_pct=penalty,
            ))
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_sla_policies(db)
        n = db.query(SlaPolicy).count()
        print(f"SLA policies seeded: {n}")
    finally:
        db.close()

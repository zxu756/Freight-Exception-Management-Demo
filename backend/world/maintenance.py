"""
Periodic world maintenance (Scenario 4 P1/P2):
定期世界维护任务（Scenario 4 P1/P2）：

- refresh_carrier_performance: 按船/航班线路/车次承运人聚合历史准点率与平均延误，
  并给高风险承运人生成 historical_risk 预测（"这条船 60% 会晚点"）。
- snapshot_metrics: 把 KPI/检测延迟/外发/决策/财务等指标按世界时间打快照，
  形成时序数据，供趋势报表。
- maintenance: 由世界协调器每 12 模拟小时调用一次。
"""
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy import func, case
from database import Base


class CarrierPerformance(Base):
    """Historical on-time performance per carrier / lane (prediction features)."""
    __tablename__ = "carrier_performance"

    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String(10), nullable=False, index=True)
    carrier_key = Column(String(100), nullable=False)  # 船名 / 航司 / 承运人
    origin = Column(String(3), nullable=True)
    destination = Column(String(3), nullable=True)
    total_runs = Column(Integer, default=0)
    delayed_runs = Column(Integer, default=0)
    cancelled_runs = Column(Integer, default=0)
    avg_delay_minutes = Column(Float, default=0.0)
    on_time_rate = Column(Float, default=1.0)  # 1 - delayed/total
    top_reason = Column(String(50), nullable=True)
    refreshed_at = Column(DateTime, nullable=False)


class MetricSnapshot(Base):
    """Time-series KPI snapshot keyed by world time."""
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, nullable=False, index=True)  # 模拟世界时间
    mode = Column(String(10), nullable=False, index=True)  # sea/air/road/all
    name = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)

def _top_reasons(rows):
    """(key, reason_code, count) -> {key: reason_code}"""
    best = {}
    for key, reason, cnt in rows:
        if not reason:
            continue
        if key not in best or cnt > best[key][1]:
            best[key] = (reason, cnt)
    return {k: v[0] for k, v in best.items()}


def refresh_carrier_performance(db, now):
    """Rebuild historical performance per mode (top 200 carriers/lanes by volume)."""
    from sea_freight_models import VesselVisit
    from air_cargo_models import AirFlight
    from road_freight_models import RoadTrip

    # ---- sea: per vessel ----------------
    sea_rows = (
        db.query(
            VesselVisit.vessel_name, func.count(VesselVisit.vessel_visit_id),
            func.sum(case((VesselVisit.delay_minutes > 0, 1), else_=0)),
            func.avg(VesselVisit.delay_minutes),
        )
        .filter(VesselVisit.vessel_type != "CRUISE", VesselVisit.arrival_datetime <= now)
        .group_by(VesselVisit.vessel_name)
        .all()
    )
    sea_reasons = _top_reasons(
        db.query(
            VesselVisit.vessel_name, VesselVisit.delay_reason_code,
            func.count(VesselVisit.vessel_visit_id),
        )
        .filter(VesselVisit.delay_reason_code.isnot(None), VesselVisit.arrival_datetime <= now)
        .group_by(VesselVisit.vessel_name, VesselVisit.delay_reason_code)
        .all()
    )

    # ---- air: per airline + lane ----------------
    air_rows = (
        db.query(
            AirFlight.airline, AirFlight.origin_airport, AirFlight.destination_airport,
            func.count(AirFlight.flight_number),
            func.sum(case((AirFlight.delay_minutes > 0, 1), else_=0)),
            func.sum(case((AirFlight.status == "cancelled", 1), else_=0)),
            func.avg(AirFlight.delay_minutes),
        )
        .filter(AirFlight.scheduled_departure <= now)
        .group_by(AirFlight.airline, AirFlight.origin_airport, AirFlight.destination_airport)
        .all()
    )
    air_reasons = _top_reasons(
        db.query(
            AirFlight.airline, AirFlight.delay_reason_code, func.count(AirFlight.flight_number),
        )
        .filter(AirFlight.delay_reason_code.isnot(None), AirFlight.scheduled_departure <= now)
        .group_by(AirFlight.airline, AirFlight.delay_reason_code)
        .all()
    )

    # ---- road: per carrier + lane ----------------
    road_rows = (
        db.query(
            RoadTrip.carrier, RoadTrip.origin_depot, RoadTrip.destination_depot,
            func.count(RoadTrip.trip_number),
            func.sum(case((RoadTrip.delay_minutes > 0, 1), else_=0)),
            func.sum(case((RoadTrip.status == "cancelled", 1), else_=0)),
            func.avg(RoadTrip.delay_minutes),
        )
        .filter(RoadTrip.scheduled_departure <= now)
        .group_by(RoadTrip.carrier, RoadTrip.origin_depot, RoadTrip.destination_depot)
        .all()
    )
    road_reasons = _top_reasons(
        db.query(
            RoadTrip.carrier, RoadTrip.delay_reason_code, func.count(RoadTrip.trip_number),
        )
        .filter(RoadTrip.delay_reason_code.isnot(None), RoadTrip.scheduled_departure <= now)
        .group_by(RoadTrip.carrier, RoadTrip.delay_reason_code)
        .all()
    )

    # 统一成 (carrier_key, origin, destination, total, delayed, cancelled, avg)
    sea_norm = [(r[0], None, None, int(r[1] or 0), int(r[2] or 0), 0, float(r[3] or 0))
                for r in sea_rows]
    air_norm = [(f"{r[0]}|{r[1]}|{r[2]}", r[1], r[2], int(r[3] or 0), int(r[4] or 0),
                 int(r[5] or 0), float(r[6] or 0)) for r in air_rows]
    road_norm = [(f"{r[0]}|{r[1]}|{r[2]}", r[1], r[2], int(r[3] or 0), int(r[4] or 0),
                  int(r[5] or 0), float(r[6] or 0)) for r in road_rows]

    # upsert（每个模式先清后插，保留量最大的 200 条）
    def rebuild(mode, rows, reasons):
        db.query(CarrierPerformance).filter(CarrierPerformance.mode == mode).delete()
        top = sorted(rows, key=lambda r: -r[3])[:200]
        for key, origin, destination, total, delayed, cancelled, avg in top:
            db.add(CarrierPerformance(
                mode=mode, carrier_key=key, origin=origin, destination=destination,
                total_runs=total, delayed_runs=delayed, cancelled_runs=cancelled,
                avg_delay_minutes=round(avg, 1),
                on_time_rate=round(1 - delayed / total, 3) if total else 1.0,
                top_reason=reasons.get(key.split("|")[0] if "|" in key else key),
                refreshed_at=now,
            ))

    rebuild("sea", sea_norm, sea_reasons)
    rebuild("air", air_norm, air_reasons)
    rebuild("road", road_norm, road_reasons)
    db.commit()

    # 历史风险预测（Scenario 4: "this sailing runs late 60% of the time"）
    refresh_historical_risks(db, now)


def refresh_historical_risks(db, now):
    """给高风险承运人（准点率 <= 70%、样本 >= 3）生成 historical_risk 预测行。"""
    from world.predict import PredictedImpact
    db.query(PredictedImpact).filter(PredictedImpact.status == "historical_risk").delete()
    risky = db.query(CarrierPerformance).filter(
        CarrierPerformance.on_time_rate <= 0.7,
        CarrierPerformance.total_runs >= 3,
    ).order_by(CarrierPerformance.on_time_rate).limit(30).all()
    for c in risky:
        desc = (
            f"{c.carrier_key} 历史准点率 {c.on_time_rate:.0%}、平均延误 {c.avg_delay_minutes:.0f} 分钟"
            f"（{c.total_runs} 个航次/车次样本，主要延误原因 {c.top_reason or 'unknown'}）—— 预测高风险"
        )
        db.add(PredictedImpact(
            event_id=0, mode=c.mode, reference=c.carrier_key, location=c.origin,
            predicted_delay_minutes=int(c.avg_delay_minutes or 0),
            impact_at=now + timedelta(hours=24), predicted_at=now,
            status="historical_risk", description=desc,
        ))
    db.commit()


def snapshot_metrics(db, now):
    """按世界时间打 KPI 快照（检测延迟/外发/决策/财务等）。"""
    from sea_freight_models import SeaException
    from air_cargo_models import AirException
    from road_freight_models import RoadException
    from notification_models import ExceptionNotification
    from decision_models import ExceptionDecision
    from customer_models import CustomerContact

    snap = []

    excs = {"sea": SeaException, "air": AirException, "road": RoadException}
    for mode, cls in excs.items():
        total = db.query(cls).count()
        if total == 0:
            continue
        diagnosed = db.query(cls).filter(cls.status == "diagnosed").count()
        pending = db.query(cls).filter(cls.status == "pending_approval").count()
        escalated = db.query(cls).filter(cls.status == "escalated").count()
        high_risk = db.query(cls).filter(cls.risk_level == "high").count()
        resolved = db.query(cls).filter(cls.status == "resolved").count()
        avg_latency = db.query(func.avg(cls.detection_latency_minutes)).filter(
            cls.detection_latency_minutes.isnot(None),
            cls.detection_latency_minutes >= 0,
            cls.detection_latency_minutes <= 1440,  # 只看 24h 内的事件→检测延迟（剔除快进/补账伪影）
        ).scalar()

        def add(name, value):
            if value is not None:
                snap.append((mode, name, float(value)))

        add("open_exceptions", total)
        add("pending_approval", pending)
        add("high_risk", high_risk)
        add("resolved", resolved)
        add("automation_rate", diagnosed / total)
        add("escalation_rate", escalated / total)
        add("avg_detection_latency_min", avg_latency)

    # 通知外发积压（全部模式）
    pending_send = db.query(ExceptionNotification).filter(
        ExceptionNotification.sent_status == "pending").count()
    sent = db.query(ExceptionNotification).filter(
        ExceptionNotification.sent_status.in_(["sent", "delivered"])).count()
    snap.append(("all", "notifications_pending_send", float(pending_send)))
    snap.append(("all", "notifications_sent", float(sent)))

    # 决策量
    decisions = db.query(ExceptionDecision).count()
    snap.append(("all", "decisions_total", float(decisions)))

    # 主动通知率（通知先于客户来电的比例）
    contacts = db.query(CustomerContact).count()
    proactive = db.query(CustomerContact).filter(CustomerContact.proactive == True).count()
    if contacts:
        snap.append(("all", "proactive_notification_rate", proactive / contacts))

    # 财务：本月 SLA 违约金合计（模拟月，按票级违约截止日归属月份）
    from sea_freight_models import CargoLine
    from air_cargo_models import HouseWaybill
    from road_freight_models import ConsignmentLine
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    penalty = 0.0
    for cls in (CargoLine, HouseWaybill, ConsignmentLine):
        rows = db.query(cls).filter(
            cls.is_sla_breached == True,
            cls.sla_deadline >= month_start,
            cls.sla_deadline <= now,
        ).all()
        for line in rows:
            penalty += line.sla_penalty_nzd or 0
    snap.append(("all", "sla_penalty_month_nzd", round(penalty, 2)))

    for mode, name, value in snap:
        db.add(MetricSnapshot(ts=now, mode=mode, name=name, value=value))
    db.commit()
    return len(snap)


def maintenance(db, now):
    """由世界协调器定期调用：刷新绩效 + 历史风险 + 指标快照 + 清理旧快照。"""
    refresh_carrier_performance(db, now)
    n = snapshot_metrics(db, now)
    cutoff = now - timedelta(days=60)
    db.query(MetricSnapshot).filter(MetricSnapshot.ts < cutoff).delete()
    db.commit()
    print(f"[world] maintenance @ {now:%m-%d %H:%M}: carrier perf refreshed, {n} metric snapshots")
    return n




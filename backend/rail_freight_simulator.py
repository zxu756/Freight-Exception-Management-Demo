"""
Rail freight live simulator - KiwiRail-style freight trains on the NZ network.

铁路货运实时模拟器：固定走廊上的班列 + 托运单/票级 + 追踪事件 + 异常 + 通知，
与世界时钟、天气因果、预测、维护任务、决策闭环完全对齐（P0-P2 特性齐备）。
"""
import heapq
import random
import threading
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm.exc import NoResultFound

from database import SessionLocal, WRITE_LOCK
from rail_freight_models import (
    RailStation, RailSegment, RailService, RailConsignment, RailConsignmentLine,
    RailTrackingEvent, RailException,
)
from rail_freight_seed import (
    generate_rail_stations, generate_rail_segments, RAIL_ROUTES, RAIL_COMMODITIES,
    CUSTOMERS, get_rail_delay_reasons,
)
from risk_calculator import calculate_risk_score, categorize_risk, calculate_severity
from config import settings
from event_classifier import (
    classifier, map_exception_to_categories, DOWNSTREAM_IMPACT,
    estimate_recovery_cost, select_best_recovery, recovery_options_json,
)
from notification_models import ExceptionNotification, build_customer_notification
from customer_models import get_customer_contact
from decision_models import apply_learned_preferences
from sla_models import map_service_level_to_tier
from environment_models import EnvironmentEvent
from world.clock import world_clock

# 状态常量
TRAIN_STATUSES = ["scheduled", "loading", "in_transit", "delayed", "arrived", "cancelled"]
CONS_STATUSES = ["booked", "loaded", "departed", "in_transit", "arrived", "delivered"]

# 延误原因 -> 异常类型
REASON_TO_EXCEPTION = {
    "track_closure": "track_closure",
    "mechanical": "mechanical_failure",
    "signal": "signal_failure",
    "weather": "weather_delay",
    "ferry": "rail_delay",
    "congestion": "rail_delay",
    "crew": "rail_delay",
}

# 延误分钟数范围（按原因）
REASON_DELAY_MINUTES = {
    "track_closure": (180, 720), "mechanical": (90, 480), "signal": (45, 240),
    "weather": (60, 360), "ferry": (120, 600), "congestion": (30, 180), "crew": (60, 300),
}

CONDITION_TIME_FACTOR = {"clear": 1.0, "slow": 1.3, "restricted": 1.6, "closed": 3.0}
EVENT_TO_CONDITION = {"weather": "slow", "track_closure": "closed", "signal": "restricted", "mechanical": "slow"}
CONDITION_DESCRIPTION = {
    "clear": "线路畅通",
    "slow": "天气影响，限速运行",
    "restricted": "信号故障，限速运行",
    "closed": "线路封闭，需停运绕行",
}

RAIL_SPEED_KMH = 55.0  # 平均旅行速度（含站停）


class RailFreightSimulator:
    """Rail freight operations simulator driven by the shared world clock."""

    def __init__(self, speed=None):
        self.sim_now = datetime.utcnow().replace(microsecond=0)
        if speed is not None:
            world_clock.set_speed(speed)
        self.running = False
        self.started_at = None
        self._stop_event = threading.Event()
        self._thread = None
        self._route_next_dep = {}
        self._pending = []
        self._pending_seq = 0
        self._last_cleanup_sim = self.sim_now
        self._last_env_event_sim = self.sim_now
        self._active_events = {}  # location -> [event dict]
        self._track_conditions = {}  # (org, dst) -> {"condition", "description"}
        self.trains_generated = 0
        self.consignments_generated = 0
        self.exceptions_generated = 0
        self.events_generated = 0

    # ---------------- lifecycle ----------------
    def start(self, backfill=True):
        if self.running:
            return
        self.running = True
        self.started_at = datetime.utcnow()
        self._init_counters()
        with WRITE_LOCK:
            db = SessionLocal()
            try:
                generate_rail_stations(db)
                generate_rail_segments(db)
                self._init_route_schedule()
                self._rebuild_pending_from_db()
                if backfill:
                    self._backfill(db)
            finally:
                db.close()
        print(f"[rail-sim] ready speed={self.speed}x sim_now={self.sim_now.isoformat()}")

    def stop(self):
        self.running = False
        print("[rail-sim] stopped")

    def set_speed(self, speed):
        world_clock.set_speed(speed)

    @property
    def speed(self):
        return world_clock.speed

    @property
    def paused(self):
        return world_clock.paused

    @paused.setter
    def paused(self, value):
        world_clock.paused = value

    # ---------------- init ----------------
    def _init_counters(self):
        db = SessionLocal()
        try:
            tn = db.query(RailService.train_number).order_by(RailService.train_number.desc()).first()
            self._train_counter = (int(tn[0].split("-")[1]) + 1) if tn else 1
            cn = db.query(RailConsignment.consignment_number).order_by(
                RailConsignment.consignment_number.desc()).first()
            self._cn_counter = (int(cn[0].split("-")[1]) + 1) if cn else 1
            ev = db.query(RailTrackingEvent.event_id).filter(
                RailTrackingEvent.event_id.like("EVT-RSIM-%")
            ).order_by(RailTrackingEvent.event_id.desc()).first()
            self._event_counter = (int(ev[0].split("-")[2]) + 1) if ev else 1
            ex = db.query(RailException.exception_id).filter(
                RailException.exception_id.like("EXC-RSIM-%")
            ).order_by(RailException.exception_id.desc()).first()
            self._exc_counter = (int(ex[0].split("-")[2]) + 1) if ex else 1

            # 通知号也按同计数前缀（NTF-RAIL-xxxxx）：保留期清理可能删掉异常行，
            # 但通知行还在 —— 用两者最大值续号，避免 notification_id 撞唯一约束
            from notification_models import ExceptionNotification as _EN
            ntf_row = db.query(_EN.notification_id).filter(
                _EN.mode == "rail",
                _EN.notification_id.like("NTF-RAIL-%"),
            ).order_by(_EN.notification_id.desc()).first()
            if ntf_row:
                self._exc_counter = max(self._exc_counter, int(ntf_row[0].split("-")[2]) + 1)
            del ex
        finally:
            db.close()

    def _init_route_schedule(self):
        for org, dst, freq, km, op, ferry in RAIL_ROUTES:
            key = (org, dst, op)
            interval = 1440.0 / max(0.05, freq * settings.order_scale * settings.rail_scale)
            self._route_next_dep[key] = self.sim_now + timedelta(minutes=random.uniform(0, interval))

    def _backfill(self, db):
        """Create trains for [sim_now - 6h, sim_now + 12h) so the dashboard has data."""
        for key in list(self._route_next_dep.keys()):
            org, dst, op = key
            freq, km, ferry = next((r[2], r[3], r[5]) for r in RAIL_ROUTES if r[0] == org and r[1] == dst and r[4] == op)
            interval = 1440.0 / max(0.05, freq * settings.order_scale * settings.rail_scale)
            while self._route_next_dep[key] < self.sim_now + timedelta(hours=12):
                dep = self._route_next_dep[key]
                self._create_train(db, org, dst, km, op, ferry, dep)
                self._route_next_dep[key] += timedelta(minutes=interval * random.uniform(0.8, 1.2))
        db.commit()

    def _rebuild_pending_from_db(self):
        """Rebuild the in-memory pending heap after a restart."""
        db = SessionLocal()
        try:
            trains = db.query(RailService).filter(
                RailService.status.in_(["scheduled", "in_transit", "delayed"]),
                RailService.scheduled_departure >= self.sim_now - timedelta(hours=48),
            ).all()
            for t in trains:
                eff_dep = t.scheduled_departure + timedelta(minutes=t.delay_minutes or 0)
                arr = t.scheduled_arrival + timedelta(minutes=t.delay_minutes or 0)
                self._push(eff_dep, "DPT", (t.train_number,))
                self._push(arr, "ARR", (t.train_number,))
        finally:
            db.close()

    def _push(self, ts, kind, payload):
        self._pending_seq += 1
        heapq.heappush(self._pending, (ts, self._pending_seq, kind, payload))

    # ---------------- tick ----------------
    def tick(self):
        with WRITE_LOCK:
            db = SessionLocal()
            try:
                self._spawn_due_trains(db)
                self._process_pending(db)
                self._derive_train_statuses(db)
                if (self.sim_now - self._last_env_event_sim) > timedelta(hours=2):
                    self._generate_env_events(db)
                    self._cleanup_env_events(db)
                    self._update_track_conditions(db)
                    self._last_env_event_sim = self.sim_now
                if (self.sim_now - self._last_cleanup_sim) > timedelta(hours=1):
                    self._cleanup(db)
                    self._last_cleanup_sim = self.sim_now
                db.commit()
            finally:
                db.close()

    def _spawn_due_trains(self, db):
        for key in list(self._route_next_dep.keys()):
            org, dst, op = key
            freq, km, ferry = next((r[2], r[3], r[5]) for r in RAIL_ROUTES if r[0] == org and r[1] == dst and r[4] == op)
            interval = 1440.0 / max(0.05, freq * settings.order_scale * settings.rail_scale)
            if self._route_next_dep[key] < self.sim_now - timedelta(hours=6):
                self._route_next_dep[key] = self.sim_now - timedelta(minutes=30)
            while self._route_next_dep[key] < self.sim_now + timedelta(minutes=30):
                dep = self._route_next_dep[key]
                self._create_train(db, org, dst, km, op, ferry, dep)
                self._route_next_dep[key] += timedelta(minutes=interval * random.uniform(0.8, 1.2))

    def _create_train(self, db, org, dst, km, op, ferry, dep):
        # 重启幂等：同走廊同运营方 2 小时内已有班列则跳过
        dup = db.query(RailService.train_number).filter(
            RailService.operator == op,
            RailService.origin == org,
            RailService.destination == dst,
            RailService.scheduled_departure >= dep - timedelta(hours=2),
            RailService.scheduled_departure <= dep + timedelta(hours=2),
        ).first()
        if dup:
            return
        dur_h = (km / RAIL_SPEED_KMH) + (4.0 if ferry else 1.5)  # 渡轮含装卸
        delay_min, reason = 0, None
        profile = get_rail_delay_reasons(org, dst)
        if random.random() < 0.03 * settings.exception_scale:
            reason = random.choices([r[0] for r in profile], weights=[r[1] for r in profile])[0]
            lo, hi = REASON_DELAY_MINUTES[reason]
            delay_min = random.randint(lo, hi)
        arr = dep + timedelta(hours=dur_h) + timedelta(minutes=delay_min)
        train = RailService(
            train_number=f"KR-{self._train_counter:05d}",
            operator=op, origin=org, destination=dst, is_inter_island=ferry,
            scheduled_departure=dep, scheduled_arrival=arr - timedelta(minutes=delay_min),
            status="scheduled", delay_minutes=delay_min, delay_reason_code=reason,
            distance_km=km, capacity_t=random.choice([900, 1200, 1600]),
            loaded_pct=round(random.uniform(55, 98), 1),
        )
        self._train_counter += 1
        db.add(train)
        db.flush()

        # 每班列挂 1-3 票托运单
        n_cons = random.choices([1, 2, 3], weights=[0.25, 0.55, 0.20])[0]
        for _ in range(n_cons):
            self._create_consignment(db, train, dep, arr, delay_min, reason)

        self.trains_generated += 1
        # 发车/到达事件
        self._push(dep, "DPT", (train.train_number,))
        self._push(arr, "ARR", (train.train_number,))

    def _create_consignment(self, db, train, dep, arr, delay_min, reason):
        route_type = random.choices(["intermodal", "bulk", "general"], weights=[0.5, 0.3, 0.2])[0]
        hs, desc = random.choice(RAIL_COMMODITIES)
        customer, tier = random.choice(CUSTOMERS)
        is_ltl = random.random() < 0.45
        n_lines = random.randint(2, 4) if is_ltl else 1
        service = random.choices(["priority", "standard", "economy"], weights=[0.2, 0.5, 0.3])[0]
        sla_tier = map_service_level_to_tier(service)
        weight = round(random.uniform(8000, 60000), 1)
        value = round(random.uniform(4000, 220000), 2)
        dur = (arr - dep).total_seconds() / 3600.0
        delivery = arr + timedelta(hours=2)
        deadline = delivery + timedelta(hours=dur * random.uniform(0.6, 1.2) + random.uniform(4, 12))

        cons = RailConsignment(
            consignment_number=f"RL-{self._cn_counter:06d}",
            train_number=train.train_number,
            route_type=route_type, is_ltl=is_ltl,
            origin=train.origin, destination=train.destination,
            commodity_code=hs, commodity_desc=desc,
            pieces=random.randint(2, 60), gross_weight_kg=weight,
            declared_value_nzd=value, customer_name=customer, customer_tier=tier,
            service_level=service, priority="normal", sla_tier=sla_tier,
            current_status="booked", current_location=train.origin,
            scheduled_delivery=delivery, estimated_delivery=delivery,
            sla_deadline=deadline,
        )
        self._cn_counter += 1
        db.add(cons)
        db.flush()

        lines = []
        for i in range(n_lines):
            # 多票时：主票镜像货值，其余票随机生成（各自独立 SLA）
            if i == 0:
                l_hs, l_desc = hs, desc
                l_customer, l_tier = customer, tier
                l_value, l_weight = value, weight
                l_service = service
            else:
                l_hs, l_desc = random.choice(RAIL_COMMODITIES)
                l_customer, l_tier = random.choice(CUSTOMERS)
                l_value = round(random.uniform(2000, 120000), 2)
                l_weight = round(random.uniform(1500, 20000), 1)
                l_service = random.choices(["priority", "standard", "economy"], weights=[0.2, 0.5, 0.3])[0]
            l_dur = (arr - dep).total_seconds() / 3600.0
            l_delivery = arr + timedelta(hours=2)
            l_deadline = l_delivery + timedelta(hours=l_dur * random.uniform(0.6, 1.2) + random.uniform(4, 12))
            lines.append(dict(
                line_number=i + 1, commodity_code=l_hs, commodity_desc=l_desc,
                customer_name=l_customer, customer_tier=l_tier,
                declared_value_nzd=l_value, pieces=random.randint(1, 30),
                gross_weight_kg=l_weight, service_level=l_service,
                sla_tier=map_service_level_to_tier(l_service),
                scheduled_delivery=l_delivery, sla_deadline=l_deadline,
            ))

        # 收货人名称
        shipper = customer
        consignee = f"{customer} Rail DC"

        for lm in lines:
            db.add(RailConsignmentLine(
                consignment_number=cons.consignment_number,
                shipper_name=shipper, consignee_name=consignee, **lm,
            ))
        self.consignments_generated += 1

        # 收运事件（提前 1 小时）
        self._push(dep - timedelta(hours=1), "RCL", (cons.consignment_number,))
        # 途中检查点
        mid = dep + (arr - dep) / 2
        self._push(mid, "INT", (cons.consignment_number,))
        # 交付事件
        self._push(arr + timedelta(hours=2), "POD", (cons.consignment_number,))
        # 若班列延误：到站时给每票概率性生成异常
        if delay_min > 0:
            self._push(arr, "EXC", (cons.consignment_number, reason, delay_min))

    # ---------------- pending event processing ----------------
    def _process_pending(self, db):
        import time as _time
        budget = 600
        processed = 0
        _t0 = _time.monotonic()
        while budget > 0 and (_time.monotonic() - _t0) < 20.0 and self._pending and self._pending[0][0] <= self.sim_now:
            budget -= 1
            processed += 1
            # 每 200 个事件提交一次：防止单个 tick 的事务过大长时间占住 SQLite 写锁（世界冻结根因）
            if processed % 200 == 0:
                db.commit()
            ts, _seq, kind, payload = heapq.heappop(self._pending)
            if kind == "DPT":
                self._on_train_depart(db, payload[0])
            elif kind == "ARR":
                self._on_train_arrive(db, payload[0])
            elif kind == "RCL":
                self._add_event(db, payload[0], "RCL", "Rail consignment received", "收运")
            elif kind == "INT":
                self._add_event(db, payload[0], "INT", "Intermediate checkpoint passed", "途中检查点")
            elif kind == "POD":
                self._on_pod(db, payload[0])
            elif kind == "EXC":
                self._on_train_delay_exception(db, payload[0], payload[1], payload[2])

    def _on_train_depart(self, db, train_number):
        t = db.query(RailService).filter(RailService.train_number == train_number).first()
        if not t or t.status == "cancelled":
            return
        t.status = "in_transit" if t.delay_minutes == 0 else "delayed"
        t.actual_departure = self.sim_now
        for cons in t.consignments:
            if cons.current_status in ("booked", "loaded"):
                cons.current_status = "departed" if cons.current_location == t.origin else "in_transit"

    def _on_train_arrive(self, db, train_number):
        t = db.query(RailService).filter(RailService.train_number == train_number).first()
        if not t or t.status == "cancelled":
            return
        t.status = "arrived"
        t.actual_arrival = self.sim_now
        for cons in t.consignments:
            if cons.current_status not in ("delivered",):
                cons.current_status = "arrived"
                cons.current_location = t.destination

    def _add_event(self, db, consignment_number, code, desc_en, desc_cn):
        cons = db.query(RailConsignment).filter(
            RailConsignment.consignment_number == consignment_number).first()
        if not cons:
            return
        db.add(RailTrackingEvent(
            event_id=f"EVT-RSIM-{self._event_counter:06d}",
            consignment_number=consignment_number,
            event_code=code, event_desc=f"{desc_en} / {desc_cn}",
            location=cons.destination if code == "POD" else cons.current_location,
            timestamp=self.sim_now,
        ))
        self._event_counter += 1
        self.events_generated += 1

    def _on_pod(self, db, consignment_number):
        cons = db.query(RailConsignment).filter(
            RailConsignment.consignment_number == consignment_number).first()
        if not cons:
            return
        cons.current_status = "delivered"
        cons.current_location = cons.destination
        cons.delivered_at = self.sim_now
        self._add_event(db, consignment_number, "POD", "Proof of delivery", "签收交付")
        self._finalize_pod(db, cons)

    def _finalize_pod(self, db, cons):
        """票级 SLA 判定 + 违约异常 + 通知（与其它三种方式一致）。"""
        for line in cons.cargo_lines:
            if line.is_sla_breached or line.sla_deadline is None:
                continue
            if self.sim_now > line.sla_deadline:
                line.is_sla_breached = True
                line.breach_type = "excused" if self._is_excused(cons) else None
                if line.breach_type != "excused":
                    penalty = round(line.declared_value_nzd * random.uniform(0.02, 0.06), 2)
                    line.sla_penalty_nzd = penalty
                self._create_exception(
                    db, cons, "rail_delay",
                    f"Rail delivery missed SLA deadline for {cons.consignment_number}",
                    round((self.sim_now - line.sla_deadline).total_seconds() / 3600.0, 1),
                    f"Delivery of {line.commodity_desc} to {cons.destination} missed its SLA commitment. Estimated penalty {line.sla_penalty_nzd or 0:.0f} NZD.",
                    ["waive", "compensate"],
                    line=line,
                )

    def _is_excused(self, cons):
        loc = cons.destination
        for evs in self._active_events.values():
            if any(e["event_type"] in ("weather", "track_closure") and e["ends_at"] >= self.sim_now for e in evs):
                return True
        return False

    # ---------------- exceptions ----------------
    def _on_train_delay_exception(self, db, consignment_number, reason, delay_min):
        cons = db.query(RailConsignment).filter(
            RailConsignment.consignment_number == consignment_number).first()
        if not cons:
            return
        # 每票异常概率（控制整体异常率 8-12%）
        exc_type = REASON_TO_EXCEPTION.get(reason, "rail_delay")
        for line in cons.cargo_lines:
            if random.random() < 0.55:
                self._create_exception(
                    db, cons, exc_type,
                    f"Train {cons.train_number} delayed {delay_min} minutes ({reason})",
                    delay_min / 60.0,
                    f"{reason} delay on {cons.train_number} {cons.origin}-{cons.destination}. Revised arrival advised.",
                    ["rebook_next_service", "switch_route_or_mode", "customer_contingency"],
                    line=line,
                )
                break  # 一票一异常，控制量级

    def _create_exception(self, db, cons, exc_type, root_cause, delay_hours, diagnosis, recovery, line=None):
        from exception_ops import reopen_if_closed
        reopen_if_closed(db, "rail", cons.consignment_number, self.sim_now)
        _value = line.declared_value_nzd if line else cons.declared_value_nzd
        _tier = line.customer_tier if line else cons.customer_tier
        _hs = line.commodity_code if line else cons.commodity_code
        _temp = (line.temp_min_c is not None) if line else False
        _sla_dl = line.sla_deadline if line else cons.sla_deadline
        _customer = line.customer_name if line else cons.customer_name
        _ref = cons.consignment_number + (f"/票{line.line_number}" if line else "")

        eff_delivery = cons.estimated_delivery or (self.sim_now + timedelta(hours=delay_hours))
        sla_breach = (eff_delivery - _sla_dl).total_seconds() / 3600 if _sla_dl else delay_hours
        mapped = "delay" if exc_type in ("rail_delay", "weather_delay", "track_closure", "mechanical_failure", "signal_failure") else exc_type
        score = calculate_risk_score(cargo_value=_value, customer_tier=_tier, sla_breach_hours=sla_breach, exception_type=mapped)
        risk_level = categorize_risk(score)
        severity = calculate_severity(score, sla_breach, exc_type, is_dg=False, temp_required=_temp,
                                      perishable=(_hs or "").startswith(("02", "03", "04", "05", "07", "08", "16", "20", "21")))
        cls = classifier.classify_and_learn(root_cause or diagnosis or "", exc_type)
        category, root_cause_cat = map_exception_to_categories(exc_type)
        impact = DOWNSTREAM_IMPACT.get(exc_type, "delay -> SLA risk")
        cost = estimate_recovery_cost(exc_type, _value)
        learned = apply_learned_preferences(db, category)

        trigger_event_id = None
        detection_latency = None
        _ev = db.query(RailTrackingEvent).filter(
            RailTrackingEvent.consignment_number == cons.consignment_number,
            RailTrackingEvent.timestamp <= self.sim_now,
        ).order_by(RailTrackingEvent.timestamp.desc()).first()
        if _ev and (self.sim_now - _ev.timestamp) <= timedelta(hours=24):
            trigger_event_id = _ev.event_id
            detection_latency = round((self.sim_now - _ev.timestamp).total_seconds() / 60.0, 1)

        best_action, action_reason = select_best_recovery(category, _value, _tier, recovery, learned)
        if cls["is_ood"]:
            _status, _requires = "escalated", True
        elif risk_level == "low" and cls["classification_decision"] == "automatic":
            _status, _requires = "diagnosed", False
        else:
            _status, _requires = "pending_approval", True
        exc = RailException(
            exception_id=f"EXC-RSIM-{self._exc_counter:06d}",
            consignment_number=cons.consignment_number,
            consignment_line_id=line.id if line else None,
            exception_type=exc_type,
            severity=severity, risk_level=risk_level, risk_score=score,
            detected_at=self.sim_now,
            root_cause=root_cause, ai_diagnosis=diagnosis,
            ai_confidence=round(random.uniform(0.85, 0.98), 2),
            status=_status, requires_human_approval=_requires,
            recovery_options=recovery_options_json(category, _value, _tier, recovery, learned),
            trigger_event_id=trigger_event_id,
            detection_latency_minutes=detection_latency,
            delay_hours=delay_hours,
            business_section=cls["business_section"],
            classification_confidence=cls["classification_confidence"],
            classification_decision=cls["classification_decision"],
            ood_score=cls["ood_score"], is_ood=cls["is_ood"],
            exception_category=category, root_cause_category=root_cause_cat,
            predicted_downstream_impact=impact, recovery_cost=cost,
            recommended_action=best_action, recommendation_reason=action_reason,
            sla_clock_paused=False,
        )
        self._exc_counter += 1
        self.exceptions_generated += 1
        db.add(exc)
        db.flush()
        self._notify(db, exc, _customer, _ref, category, root_cause, recovery,
                     cls["classification_confidence"], cons.estimated_delivery)

    def _notify(self, db, exc, customer_name, reference, category, root_cause, recovery, confidence, revised_eta):
        contact = get_customer_contact(db, customer_name) or {}
        channel = contact.get("channel") or "email"
        msg = build_customer_notification(
            customer_name, reference, category, root_cause, revised_eta,
            recovery, confidence, self.sim_now + timedelta(hours=2)
        )
        if channel == "sms":
            eta = revised_eta.strftime("%d %b %H:%M") if revised_eta else "TBC"
            msg = f"Freight alert for {reference}: {category}. Revised ETA {eta}. Details emailed."
        db.add(ExceptionNotification(
            notification_id=f"NTF-RAIL-{self._exc_counter:06d}",
            mode="rail",
            exception_id=exc.exception_id,
            reference=reference,
            recipient=customer_name,
            recipient_email=contact.get("email"),
            recipient_phone=contact.get("phone") or contact.get("mobile"),
            channel=channel,
            # COM-003：高风险异常的通知必须人工审核后才外发
            review_status=("pending_review" if exc.risk_level == "high" else "approved"),
            message=msg,
            revised_eta=revised_eta,
            confidence=confidence,
            next_update_at=self.sim_now + timedelta(hours=2),
            sent_at=self.sim_now,
        ))

    # ---------------- environment / conditions ----------------
    def _generate_env_events(self, db):
        from world.causality import weather_events_for_mode
        for loc, event in weather_events_for_mode(db, "rail", self.sim_now, self._active_events):
            db.add(event)
            self._active_events.setdefault(loc, []).append({
                "event_type": event.event_type, "severity": event.severity,
                "description": event.description, "ends_at": event.ends_at,
                "impact_at": event.impact_at,
            })
        # 少量随机线路事件（信号/机械）
        from rail_freight_seed import RAIL_STATIONS
        if random.random() < 0.2:
            loc = random.choice(RAIL_STATIONS)[0]
            ev_type = random.choices(["signal", "mechanical", "track_closure"], weights=[0.5, 0.3, 0.2])[0]
            ends = self.sim_now + timedelta(hours=random.randint(4, 12))
            self._active_events.setdefault(loc, []).append({
                "event_type": ev_type, "severity": "moderate",
                "description": f"{loc} 铁路{'信号故障' if ev_type == 'signal' else '机车故障' if ev_type == 'mechanical' else '线路封闭'}",
                "ends_at": ends, "impact_at": self.sim_now,
            })
        db.commit()

    def _cleanup_env_events(self, db):
        now = self.sim_now
        for loc in list(self._active_events.keys()):
            self._active_events[loc] = [e for e in self._active_events[loc] if e["ends_at"] >= now]
            if not self._active_events[loc]:
                del self._active_events[loc]
        db.query(EnvironmentEvent).filter(
            EnvironmentEvent.mode == "rail", EnvironmentEvent.ends_at < now).delete()

    def _route_active_events(self, org, dst):
        now = self.sim_now
        def _impacting(loc):
            return [e for e in self._active_events.get(loc, [])
                    if e.get("impact_at", now) <= now <= e["ends_at"]]
        return _impacting(org) + _impacting(dst)

    def _update_track_conditions(self, db):
        for org, dst, _f, _km, _op, _ferry in RAIL_ROUTES:
            cond = "clear"
            events = self._route_active_events(org, dst)
            if events:
                cond = EVENT_TO_CONDITION.get(events[0]["event_type"], "slow")
            self._track_conditions[(org, dst)] = {"condition": cond}
            seg = db.query(RailSegment).filter(
                RailSegment.origin == org, RailSegment.destination == dst).first()
            if seg:
                seg.condition = cond
                seg.speed_factor = {"clear": 1.0, "slow": 0.7, "restricted": 0.5, "closed": 0.0}[cond]
                seg.description = CONDITION_DESCRIPTION[cond]
                seg.updated_at = self.sim_now
        db.commit()

    # ---------------- status derivation / cleanup ----------------
    def _derive_train_statuses(self, db):
        now = self.sim_now
        trains = db.query(RailService).filter(
            RailService.status.in_(["scheduled", "in_transit", "delayed"])).all()
        for t in trains:
            eff_dep = t.scheduled_departure + timedelta(minutes=t.delay_minutes or 0)
            eff_arr = t.scheduled_arrival + timedelta(minutes=t.delay_minutes or 0)
            if t.status == "scheduled" and now >= eff_dep - timedelta(hours=2):
                t.status = "loading"
            elif t.status == "loading" and now >= eff_dep:
                t.status = "in_transit" if t.delay_minutes == 0 else "delayed"
            elif t.status in ("in_transit", "delayed") and now >= eff_arr:
                t.status = "arrived"
                t.actual_arrival = now

    def _cleanup(self, db):
        cutoff = self.sim_now - timedelta(hours=settings.rail_sim_retention_hours)
        db.query(RailTrackingEvent).filter(RailTrackingEvent.timestamp < cutoff).delete()
        db.commit()


# Singleton used by main.py / world coordinator.
simulator = RailFreightSimulator()



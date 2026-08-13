"""
Live sea freight simulator - drives container cargo, tracking events and
exceptions against real PortConnect vessel schedules.
实时海运模拟器 - 基于 PortConnect 真实船期生成集装箱货物、追踪事件和异常

Design:
- Vessel schedules are REAL data from PortConnect (NZ ports), loaded at startup
  from the live API with a local JSON fallback.
- Container cargo (20-60 per commercial vessel visit), tracking events and
  exceptions are GENERATED against those real vessel visits.
- Vessel visit lifecycle: EXPECTED -> INPORT -> DEPARTED (derived from real time)
- Container lifecycle: at_sea -> discharged -> (customs/biosecurity hold) ->
  available -> gate_out -> delivered
- Exception injection: vessel delays, customs holds, MPI biosecurity holds,
  port congestion, cold-chain temperature excursions, damage
"""
import heapq
import json
import random
import threading
import time
from datetime import datetime, timedelta

from database import SessionLocal, WRITE_LOCK
from sea_freight_models import (
    SeaPort, VesselVisit, SeaContainer, SeaTrackingEvent, SeaException
)
from sea_freight_seed import (
    generate_ports, EXPORT_COMMODITIES, IMPORT_COMMODITIES, CUSTOMERS
)
from risk_calculator import calculate_risk_score, categorize_risk, calculate_severity
from config import settings
from event_classifier import classifier, map_exception_to_categories, RECOVERY_PLAYBOOK, DOWNSTREAM_IMPACT, estimate_recovery_cost, select_best_recovery
from notification_models import ExceptionNotification, build_customer_notification
from llm_client import enhance_diagnosis
from anomaly_detector import detector

# 活跃窗口：为 arrival 落在该窗口内的船生成集装箱
ACTIVE_WINDOW_BEFORE_HOURS = 120   # 5 days before
ACTIVE_WINDOW_AFTER_HOURS = 336    # 14 days after

# 集装箱 owner code (ISO 6346 前缀)
OWNER_CODES = ["MSCU", "MAEU", "CMAU", "CSLU", "OOCU", "ONEU", "HLXU", "TCNU", "TLLU", "FSCU"]

# 延误原因权重
DELAY_REASONS = [
    ("port_congestion", 0.35), ("weather", 0.25), ("berth_unavailable", 0.15),
    ("mechanical", 0.10), ("labour", 0.10),
]


class SeaFreightSimulator:
    """Live sea freight simulator running as a background thread."""

    def __init__(self, speed=None):
        self.sim_now = datetime.utcnow().replace(microsecond=0)
        self.speed = speed if speed is not None else settings.sea_sim_speed
        self.paused = False
        self.running = False
        self.started_at = None
        self._stop_event = threading.Event()
        self._thread = None
        self._last_real = time.monotonic()
        self._pending = []
        self._pending_seq = 0
        self._last_cleanup_sim = self.sim_now
        self._last_missing_check_sim = self.sim_now
        self._generated_vessels = set()
        self._loaded_vessels = False
        self.vessels_loaded = 0
        self.containers_generated = 0
        self.exceptions_generated = 0
        self.events_generated = 0

    # ----------------------------------------------------------
    # 线程控制
    # ----------------------------------------------------------
    def start(self, backfill=True):
        if self.running:
            return
        self.running = True
        self.started_at = datetime.utcnow()
        self._init_counters()
        with WRITE_LOCK:
            db = SessionLocal()
            try:
                generate_ports(db)
                self._load_vessel_visits(db)
                if backfill:
                    self._backfill(db)
            finally:
                db.close()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="sea-freight-sim")
        self._thread.start()
        print(f"[sea-sim] started speed={self.speed}x vessels={self.vessels_loaded} sim_now={self.sim_now.isoformat()}")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[sea-sim] stopped")

    def set_speed(self, speed):
        self.speed = max(0.0, min(float(speed), 3600.0))

    def _run(self):
        while not self._stop_event.is_set():
            t0 = time.monotonic()
            if not self.paused:
                now_real = time.monotonic()
                elapsed = now_real - self._last_real
                self._last_real = now_real
                self.sim_now += timedelta(seconds=elapsed * self.speed)
                try:
                    self.tick()
                except Exception as e:
                    print(f"[sea-sim] tick error: {e}")
            time.sleep(max(0.1, settings.sea_sim_tick_seconds - (time.monotonic() - t0)))

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------
    def _init_counters(self):
        db = SessionLocal()
        try:
            evt_row = db.query(SeaTrackingEvent.event_id).filter(
                SeaTrackingEvent.event_id.like("EVT-SIM-%")
            ).order_by(SeaTrackingEvent.event_id.desc()).first()
            self._event_counter = (int(evt_row[0].split("-")[2]) + 1) if evt_row else 1

            exc_row = db.query(SeaException.exception_id).filter(
                SeaException.exception_id.like("EXC-SIM-%")
            ).order_by(SeaException.exception_id.desc()).first()
            self._exc_counter = (int(exc_row[0].split("-")[2]) + 1) if exc_row else 1

            # container counter from max numeric suffix
            rows = db.query(SeaContainer.container_number).all()
            max_num = 0
            for r in rows:
                suffix = r[0][4:] if len(r[0]) >= 11 else ""
                if suffix.isdigit():
                    max_num = max(max_num, int(suffix))
            self._container_counter = max_num + 1
        finally:
            db.close()

    def _load_vessel_visits(self, db):
        """Load real vessel schedules from PortConnect (API -> JSON fallback) into DB."""
        from portconnect_client import get_vessels
        visits = get_vessels()
        seen = {r[0] for r in db.query(VesselVisit.vessel_visit_id).all()}
        for v in visits:
            vid = self._visit_id(v)
            if vid in seen:
                continue
            seen.add(vid)
            db.add(VesselVisit(
                vessel_visit_id=vid,
                vessel_name=v.get("vesselName", "Unknown"),
                imo_number=str(v.get("imoNumber")) if v.get("imoNumber") else None,
                inbound_voyage=v.get("inboundVoyage") or None,
                outbound_voyage=v.get("outboundVoyage") or None,
                vessel_status=v.get("vesselStatus", "EXPECTED"),
                vessel_type=v.get("vesselType"),
                port_code=v.get("portCode", "NZAKL"),
                wharf_name=v.get("wharfName"),
                berth=v.get("berth"),
                previous_port=v.get("previousPortName"),
                next_port=v.get("nextPortName"),
                vessel_operator=v.get("vesselOperator"),
                service_code=v.get("serviceCode"),
                arrival_datetime=self._parse_dt(v.get("arrivalDatetime")),
                departure_datetime=self._parse_dt(v.get("departureDatetime")),
                last_updated=self._parse_dt(v.get("lastUpdatedDateTime")),
            ))
            self.vessels_loaded += 1
        db.commit()
        self._loaded_vessels = True

    @staticmethod
    def _visit_id(v):
        ref = v.get("vesselVisitReference")
        if ref:
            return ref
        return "|".join([
            v.get("vesselName", ""),
            v.get("inboundVoyage") or "",
            v.get("outboundVoyage") or "",
            v.get("portCode", ""),
            v.get("arrivalDatetime") or "",
        ])

    @staticmethod
    def _parse_dt(s):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            return None

    def _backfill(self, db):
        """Generate containers and schedule events for commercial vessels in the active window."""
        lo = self.sim_now - timedelta(hours=ACTIVE_WINDOW_BEFORE_HOURS)
        hi = self.sim_now + timedelta(hours=ACTIVE_WINDOW_AFTER_HOURS)
        visits = db.query(VesselVisit).filter(
            VesselVisit.vessel_type == "COMMERCIAL",
            VesselVisit.arrival_datetime.isnot(None),
            VesselVisit.arrival_datetime >= lo,
            VesselVisit.arrival_datetime <= hi,
        ).all()
        for visit in visits:
            self._generate_containers_for_visit(db, visit)

    def _generate_containers_for_visit(self, db, visit):
        if visit.vessel_visit_id in self._generated_vessels:
            return
        self._generated_vessels.add(visit.vessel_visit_id)
        # 船舶延误注入 (~8% for EXPECTED vessels)
        if visit.vessel_status == "EXPECTED" and random.random() < 0.08:
            delay_minutes = int(random.choice([120, 180, 240, 360, 480, 720, 1440]))
            visit.delay_minutes = delay_minutes
            visit.delay_reason_code = random.choices(
                [r[0] for r in DELAY_REASONS], weights=[r[1] for r in DELAY_REASONS])[0]
            if visit.departure_datetime:
                visit.departure_datetime += timedelta(minutes=delay_minutes)
        n = random.randint(20, 60)
        for _ in range(n):
            self._create_container(db, visit)
        db.commit()

    # ----------------------------------------------------------
    # 集装箱与事件生成
    # ----------------------------------------------------------
    def _create_container(self, db, visit):
        # Heuristic: if previous port is international and next is NZ -> import; else export
        prev_intl = not self._is_nz_port_name(visit.previous_port)
        next_intl = not self._is_nz_port_name(visit.next_port)
        if prev_intl and not next_intl:
            direction = "import"
        elif next_intl and not prev_intl:
            direction = "export"
        else:
            direction = "import" if random.random() < 0.55 else "export"

        pool = IMPORT_COMMODITIES if direction == "import" else EXPORT_COMMODITIES
        desc, hs, value_range, tiers, ctype, temp = random.choice(pool)
        value = random.randint(*value_range)

        size = random.choices(["20FT", "40FT", "40HC"], weights=[0.4, 0.4, 0.2])[0]
        if ctype == "RF":
            size = "40HC" if random.random() < 0.5 else "40FT"
        weight = round(random.uniform(8000, 28000) if size == "20FT" else random.uniform(15000, 30000), 0)

        customer, tier = random.choice(CUSTOMERS)
        if random.random() < 0.08:
            tier = "VIP"
        elif tier == "VIP" and random.random() < 0.7:
            tier = "high"

        temp_min, temp_max = (None, None)
        if temp:
            temp_min, temp_max = temp

        owner = random.choice(OWNER_CODES)
        cn = f"{owner}{self._container_counter:07d}"
        self._container_counter += 1

        arrival = visit.arrival_datetime or self.sim_now
        is_dg = "DGR" in desc
        container = SeaContainer(
            container_number=cn, vessel_visit_id=visit.vessel_visit_id,
            direction=direction, size=size, container_type=ctype,
            gross_weight_kg=weight, commodity_code=hs, commodity_desc=desc,
            customer_name=customer, customer_tier=tier,
            declared_value_nzd=float(value),
            temp_required_c=temp_min, temp_min_c=temp_min, temp_max_c=temp_max,
            is_dg=is_dg, dg_class="3" if is_dg else None, un_number="UN1133" if is_dg else None,
            current_status="at_sea",
            scheduled_delivery=arrival + timedelta(hours=random.randint(36, 72)),
            sla_deadline=arrival + timedelta(hours=random.randint(60, 96)),
        )
        db.add(container)
        db.flush()
        self.containers_generated += 1

        if visit.delay_minutes > 0:
            self._create_exception(
                db, container, "vessel_delay",
                f"Vessel {visit.vessel_name} delayed {visit.delay_minutes} minutes ({visit.delay_reason_code})",
                visit.delay_minutes / 60.0,
                f"Vessel schedule deviation detected. {visit.delay_reason_code or 'operational'} "
                f"delay on {visit.vessel_name}. Revised arrival advised to consignee.",
                ["wait", "expedite_discharge"],
                reason_code=visit.delay_reason_code
            )

        # 运力/服务取消 (~0.8%)：计划舱位不可用
        if random.random() < 0.008:
            self._create_exception(
                db, container, "service_cancelled",
                f"Sailing {visit.vessel_name} {visit.outbound_voyage or ''} omitted, no slot for {container.container_number}",
                0.0,
                "Planned vessel sailing was cancelled and the booked container has no available slot.",
                ["rebook_next_sailing", "alternate_carrier", "split_shipment"]
            )

        self._schedule_container_events(container, visit, arrival)

    def _schedule_container_events(self, container, visit, arrival):
        cn = container.container_number
        port = visit.port_code
        vid = visit.vessel_visit_id

        self._push(arrival, "vessel_arrive", (vid,))
        dis = arrival + timedelta(hours=random.randint(3, 8))
        self._push(dis, "discharge", (cn, port, dis))

        # 正常 18-40h 可提取；5% 异常长停留（55-90h，压港/清关延误），供 dwell-time 异常检测发现
        if random.random() < 0.05:
            avail = dis + timedelta(hours=random.randint(55, 90))
        else:
            avail = dis + timedelta(hours=random.randint(18, 40))
        self._push(avail, "available", (cn, port, avail))

        gate_out = avail + timedelta(hours=random.randint(6, 24))
        self._push(gate_out, "gate_out", (cn, port))

        delivered = gate_out + timedelta(hours=random.randint(12, 48))
        self._push(delivered, "deliver", (cn, port))

        # 海关扣留 (进口，~12%)
        if container.direction == "import" and random.random() < 0.12:
            hold = dis + timedelta(hours=random.randint(2, 10))
            self._push(hold, "customs_hold", (cn, port))

        # MPI 生物安全 (食品/木制品，~8%)
        if self._is_biosecurity_risk(container) and random.random() < 0.08:
            self._push(dis + timedelta(hours=random.randint(4, 16)), "biosecurity_hold", (cn, port))

        # 冷藏温度异常 (~1.5%)
        if container.temp_min_c is not None and random.random() < 0.015:
            self._push(dis + timedelta(hours=random.randint(1, 6)), "temp_alert", (cn, port))

        # 货损 (~1%)
        if random.random() < 0.01:
            self._push(dis + timedelta(hours=random.randint(1, 8)), "damage", (cn, port))

        # 货物丢失/失踪 (~0.5%)
        if random.random() < 0.005:
            self._push(dis + timedelta(hours=random.randint(6, 24)), "lost", (cn, port))

        # 追踪/数据异常 (~1%)
        if random.random() < 0.01:
            self._push(dis + timedelta(hours=random.randint(8, 36)), "tracking_gap", (cn, port))

        # 派送失败 (~1%)
        if random.random() < 0.01:
            self._push(delivered + timedelta(hours=1), "failed_delivery", (cn, port))

    @staticmethod
    def _is_nz_port_name(name):
        if not name:
            return False
        return name.upper() in {
            "AUCKLAND", "TAURANGA", "WELLINGTON", "LYTTELTON", "CHRISTCHURCH",
            "TIMARU", "NELSON", "NAPIER", "PORT CHALMERS", "MARSDEN POINT",
            "NEW PLYMOUTH", "GISBORNE", "BLUFF", "DUNEDIN", "PICTON", "WANGANUI",
        }

    @staticmethod
    def _is_biosecurity_risk(container):
        hs = container.commodity_code or ""
        return hs.startswith(("02", "03", "04", "05", "07", "08", "16", "20", "21", "44", "94"))

    # ----------------------------------------------------------
    # 事件堆
    # ----------------------------------------------------------
    def _push(self, sim_time, kind, payload):
        self._pending_seq += 1
        heapq.heappush(self._pending, (sim_time, self._pending_seq, kind, payload))

    def _process_pending(self, db):
        while self._pending and self._pending[0][0] <= self.sim_now:
            _, _, kind, payload = heapq.heappop(self._pending)
            try:
                handler = getattr(self, f"_on_{kind}")
                handler(db, payload)
            except AttributeError:
                print(f"[sea-sim] unknown pending kind: {kind}")
            except Exception as e:
                print(f"[sea-sim] pending handler error ({kind}): {e}")

    def _insert_event(self, db, cn, code, desc, loc, reason=None, message=None, ts=None):
        event = SeaTrackingEvent(
            event_id=f"EVT-SIM-{self._event_counter:09d}",
            container_number=cn, event_code=code, event_desc=desc,
            location=loc, timestamp=ts or self.sim_now, source="portconnect",
            reason_code=reason, message=message or f"PortConnect: {code} {loc}"
        )
        self._event_counter += 1
        self.events_generated += 1
        db.add(event)

    # ----------------------------------------------------------
    # 事件处理器
    # ----------------------------------------------------------
    def _on_vessel_arrive(self, db, payload):
        vid = payload[0]
        visit = db.query(VesselVisit).filter(VesselVisit.vessel_visit_id == vid).first()
        if not visit:
            return
        if visit.vessel_status == "EXPECTED":
            visit.vessel_status = "INPORT"

    def _on_discharge(self, db, payload):
        cn, port, ts = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        c.current_status = "discharged"
        c.discharged_at = ts
        self._insert_event(db, cn, "DIS", "Container discharged", port, ts=ts)

    def _on_available(self, db, payload):
        cn, port, ts = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        if c.current_status not in ("customs_hold", "discharged"):
            return
        c.current_status = "available"
        c.available_at = ts
        self._insert_event(db, cn, "AVC", "Container available for collection", port, ts=ts)
        if c.discharged_at:
            dwell = (c.available_at - c.discharged_at).total_seconds() / 3600
            anomaly = detector.observe("sea", "DIS_AVC", dwell)
            if anomaly:
                self._create_predicted_exception(db, c, anomaly, "DIS->AVC")

    def _on_gate_out(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        c.current_status = "gate_out"
        self._insert_event(db, cn, "GTO", "Container gate out", port)

    def _on_deliver(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        db.flush()
        dup = db.query(SeaTrackingEvent).filter(
            SeaTrackingEvent.container_number == cn,
            SeaTrackingEvent.event_code == "DLV"
        ).first()
        if dup:
            return
        c.current_status = "delivered"
        c.delivered_at = self.sim_now
        self._insert_event(db, cn, "DLV", "Container delivered", port)
        if c.available_at:
            dwell = (c.delivered_at - c.available_at).total_seconds() / 3600
            anomaly = detector.observe("sea", "AVC_DLV", dwell)
            if anomaly:
                self._create_predicted_exception(db, c, anomaly, "AVC->DLV")

    def _on_customs_hold(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        c.current_status = "customs_hold"
        self._insert_event(db, cn, "CHD", "Customs hold placed", port, reason="customs_hold")
        self._create_exception(
            db, c, "customs_hold",
            "NZ Customs inspection hold",
            random.uniform(12, 48),
            "Customs selected container for inspection. Historical pattern: 88% release without finding.",
            ["wait", "expedite_documentation"]
        )

    def _on_biosecurity_hold(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        c.biosecurity_cleared = False
        self._insert_event(db, cn, "BIO", "MPI biosecurity inspection", port, reason="biosecurity")
        self._create_exception(
            db, c, "biosecurity_hold",
            "MPI biosecurity inspection hold",
            random.uniform(24, 72),
            "MPI selected container for biosecurity screening. Food/timber declaration triggers higher inspection rate.",
            ["wait", "expedite_documentation"]
        )

    def _on_temp_alert(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        c.temp_excursion_alert = True
        self._insert_event(db, cn, "TEMP", "Temperature excursion alert", port, reason="temp_excursion")
        self._create_exception(
            db, c, "temp_excursion",
            f"Temperature excursion outside {c.temp_min_c}-{c.temp_max_c}C range",
            0.0,
            "Reefer unit temperature deviation detected. Recommend expedited discharge and customer notification.",
            ["expedite_discharge", "upgrade_priority"]
        )

    def _on_damage(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        self._create_exception(
            db, c, "damage",
            "Container damage detected at discharge",
            0.0,
            "Stevedore reported container damage during discharge. Survey required.",
            ["survey_inspection", "insurance_claim"]
        )

    def _on_lost(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        self._create_exception(
            db, c, "lost",
            "Container cannot be located after discharge",
            0.0,
            "Expected arrival scan absent and terminal cannot locate the unit. Network trace initiated.",
            ["network_trace", "replacement", "insurance_claim"]
        )

    def _on_tracking_gap(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        self._create_exception(
            db, c, "tracking_gap",
            "No valid tracking event received",
            0.0,
            "Tracking feed stale; physical status unconfirmed. Integration ticket raised.",
            ["resend_event", "integration_ticket", "manual_milestone"]
        )

    def _on_failed_delivery(self, db, payload):
        cn, port = payload
        c = db.query(SeaContainer).filter(SeaContainer.container_number == cn).first()
        if not c:
            return
        self._create_exception(
            db, c, "failed_delivery",
            "Delivery attempt failed at receiving site",
            0.0,
            "Receiving site issue prevented handover. Redelivery rescheduled.",
            ["redelivery", "reschedule", "depot_collection"]
        )

    def _create_exception(self, db, container, exc_type, root_cause, delay_hours, diagnosis, recovery, reason_code=None):
        eff_delivery = container.estimated_delivery or (self.sim_now + timedelta(hours=delay_hours))
        sla_breach = (eff_delivery - container.sla_deadline).total_seconds() / 3600 if container.sla_deadline else delay_hours
        mapped = "delay" if exc_type == "vessel_delay" else exc_type
        score = calculate_risk_score(
            cargo_value=container.declared_value_nzd,
            customer_tier=container.customer_tier,
            sla_breach_hours=sla_breach,
            exception_type=mapped
        )
        risk_level = categorize_risk(score)
        severity = calculate_severity(
            score, sla_breach, exc_type,
            is_dg=container.is_dg,
            temp_required=container.temp_min_c is not None,
            perishable=(container.commodity_code or "").startswith(("02", "03", "04", "05", "07", "08", "16", "20", "21")),
        )
        cls = classifier.classify_and_learn(root_cause or diagnosis or "", exc_type)
        category, root_cause_cat = map_exception_to_categories(exc_type, reason_code)
        impact = DOWNSTREAM_IMPACT.get(exc_type, "delay -> SLA risk")
        cost = estimate_recovery_cost(exc_type, container.declared_value_nzd)
        best_action, action_reason = select_best_recovery(category, container.declared_value_nzd, container.customer_tier)
        if cls["is_ood"] and settings.llm_enabled:
            diagnosis = enhance_diagnosis(exc_type, root_cause, diagnosis)
        if cls["is_ood"]:
            _status, _requires = "escalated", True
        elif risk_level == "low" and cls["classification_decision"] == "automatic":
            _status, _requires = "diagnosed", False
        else:
            _status, _requires = "pending_approval", True
        exc = SeaException(
            exception_id=f"EXC-SIM-{self._exc_counter:06d}",
            container_number=container.container_number,
            exception_type=exc_type,
            severity=severity,
            risk_level=risk_level,
            risk_score=score,
            detected_at=self.sim_now,
            root_cause=root_cause,
            ai_diagnosis=diagnosis,
            ai_confidence=round(random.uniform(0.85, 0.98), 2),
            status=_status,
            requires_human_approval=_requires,
            recovery_options=json.dumps(RECOVERY_PLAYBOOK.get(category, recovery)),
            delay_hours=delay_hours,
            business_section=cls["business_section"],
            classification_confidence=cls["classification_confidence"],
            classification_decision=cls["classification_decision"],
            ood_score=cls["ood_score"],
            is_ood=cls["is_ood"],
            exception_category=category,
            root_cause_category=root_cause_cat,
            predicted_downstream_impact=impact,
            recovery_cost=cost,
            recommended_action=best_action,
            recommendation_reason=action_reason,
        )
        self._exc_counter += 1
        self.exceptions_generated += 1
        db.add(exc)
        db.flush()
        self._notify(db, exc, container.customer_name, container.container_number,
                     category, root_cause, recovery, cls["classification_confidence"],
                     container.estimated_delivery)

    def _notify(self, db, exc, customer_name, reference, category, root_cause, recovery, confidence, revised_eta):
        db.add(ExceptionNotification(
            notification_id=f"NTF-SEA-{self._exc_counter:06d}",
            mode="sea",
            exception_id=exc.exception_id,
            reference=reference,
            recipient=customer_name,
            channel="email",
            message=build_customer_notification(
                customer_name, reference, category, root_cause, revised_eta,
                recovery, confidence, self.sim_now + timedelta(hours=2)
            ),
            revised_eta=revised_eta,
            confidence=confidence,
            next_update_at=self.sim_now + timedelta(hours=2),
            sent_at=self.sim_now,
        ))

    def _create_predicted_exception(self, db, container, anomaly, transition):
        """Create a predictive anomaly exception from a dwell-time outlier."""
        exc = SeaException(
            exception_id=f"EXC-SIM-{self._exc_counter:06d}",
            container_number=container.container_number,
            exception_type="predicted_anomaly",
            severity="medium",
            risk_level="medium",
            risk_score=50,
            detected_at=self.sim_now,
            root_cause=f"{transition} dwell time abnormal for {container.container_number}",
            ai_diagnosis=f"Dwell time {transition} exceeds recent P95 by {anomaly['anomaly_score']}x. Potential congestion or clearance delay.",
            ai_confidence=round(random.uniform(0.7, 0.85), 2),
            status="detected",
            requires_human_approval=True,
            recovery_options=json.dumps(["monitor", "expedite_discharge"]),
            delay_hours=0.0,
            business_section="Time & Service Disruption",
            classification_decision="human_review",
            ood_score=0.0,
            is_ood=False,
            anomaly_score=anomaly["anomaly_score"],
            anomaly_reason=anomaly["anomaly_reason"],
            exception_category="Delay",
            root_cause_category="traffic-infrastructure",
        )
        self._exc_counter += 1
        self.exceptions_generated += 1
        db.add(exc)
        db.flush()

    # ----------------------------------------------------------
    # 状态推导
    # ----------------------------------------------------------
    def _derive_vessel_statuses(self, db):
        visits = db.query(VesselVisit).filter(
            VesselVisit.vessel_status.in_(["EXPECTED", "INPORT"])
        ).all()
        for v in visits:
            if v.arrival_datetime and self.sim_now >= v.arrival_datetime and v.vessel_status == "EXPECTED":
                v.vessel_status = "INPORT"
            if v.departure_datetime and self.sim_now >= v.departure_datetime:
                v.vessel_status = "DEPARTED"

    # ----------------------------------------------------------
    # 主 tick 与清理
    # ----------------------------------------------------------
    def tick(self):
        with WRITE_LOCK:
            db = SessionLocal()
            try:
                self._process_pending(db)
                self._derive_vessel_statuses(db)
                db.commit()
                if (self.sim_now - self._last_missing_check_sim) > timedelta(hours=2):
                    self._run_missing_event_detection(db)
                    self._last_missing_check_sim = self.sim_now
                if (self.sim_now - self._last_cleanup_sim) > timedelta(hours=1):
                    self._cleanup(db)
                    self._last_cleanup_sim = self.sim_now
            finally:
                db.close()

    def _run_missing_event_detection(self, db):
        """Flag containers whose next milestone is overdue (missing expected event)."""
        threshold = detector.get_p95("sea", "DIS_AVC")
        if not threshold:
            return
        stale = db.query(SeaContainer).filter(
            SeaContainer.discharged_at.isnot(None),
            SeaContainer.available_at.is_(None),
            SeaContainer.current_status == "discharged",
        ).all()
        for c in stale:
            elapsed = (self.sim_now - c.discharged_at).total_seconds() / 3600
            if elapsed > threshold * 1.5:
                anomaly = {
                    "anomaly_score": round(elapsed / threshold, 2),
                    "anomaly_reason": "missing_AVC_after_DIS",
                }
                self._create_predicted_exception(db, c, anomaly, "DIS->AVC missing")

    def _cleanup(self, db):
        cutoff = self.sim_now - timedelta(hours=settings.sea_sim_retention_hours)
        old_containers = db.query(SeaContainer).filter(
            SeaContainer.delivered_at.isnot(None),
            SeaContainer.delivered_at < cutoff
        ).all()
        if old_containers:
            cns = [c.container_number for c in old_containers]
            db.query(SeaException).filter(SeaException.container_number.in_(cns)).delete(synchronize_session=False)
            db.query(SeaTrackingEvent).filter(SeaTrackingEvent.container_number.in_(cns)).delete(synchronize_session=False)
            for c in old_containers:
                db.delete(c)
        db.commit()


# 全局单例
simulator = SeaFreightSimulator()

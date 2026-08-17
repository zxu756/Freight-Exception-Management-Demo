"""
Live road freight simulator - continuously generates NZ domestic road freight
trips, consignments, tracking events and exceptions in real time.
实时陆运模拟器 - 持续生成新西兰国内公路运输任务、托运单、追踪事件和异常

Design:
- Simulation clock advances at configurable speed (default 60x: 1 real second = 1 sim minute)
- ~1000-1500 trips/day across North/South Island line-haul, regional and
  inter-island (Cook Strait ferry) routes
- Each trip carries 1-3 consignments with realistic NZ cargo profiles
- Trip lifecycle: scheduled -> loading -> in_transit -> arrived -> delivered
- Inter-island trips cross the Cook Strait ferry (Wellington <-> Picton)
- Exception injection: congestion/weather delays, road closures, breakdowns,
  driver-hours breaches, ferry cancellations, cold-chain temperature excursions
- Data retention cleanup to keep the demo database bounded
"""
import heapq
import json
import random
import threading
import time
from datetime import datetime, timedelta

from database import SessionLocal, WRITE_LOCK
from road_freight_models import (
    Depot, RoadTrip, RoadConsignment, RoadTrackingEvent, RoadException, ConsignmentLine
)
from road_freight_seed import (
    generate_depots, road_distance, trip_duration_hours, FERRY_CROSSING_HOURS, NZ_DEPOTS,
    EXPORT_COMMODITIES, IMPORT_COMMODITIES, DOMESTIC_COMMODITIES, CUSTOMERS
)
from risk_calculator import calculate_risk_score, categorize_risk, calculate_severity
from config import settings
from event_classifier import classifier, map_exception_to_categories, DOWNSTREAM_IMPACT, estimate_recovery_cost, select_best_recovery, recovery_options_json
from notification_models import ExceptionNotification, build_customer_notification
from customer_models import get_customer_contact
from decision_models import apply_learned_preferences
from llm_client import enhance_diagnosis
from sla_models import get_policy, determine_breach, estimate_penalty, map_service_level_to_tier, is_excused, evaluate_breach
from environment_events import generate_event, get_active_events_for_route
from environment_models import EVENT_TYPE_TO_REASON, SEVERITY_DELAY_MINUTES
from anomaly_detector import detector
from world.clock import world_clock

# ============================================================
# 分拨中心岛别映射
# ============================================================
ISLAND_MAP = {c: i for c, _n, _city, _r, i, _h, _c in NZ_DEPOTS}
NORTH_ISLAND = {c for c, i in ISLAND_MAP.items() if i == "north"}
SOUTH_ISLAND = {c for c, i in ISLAND_MAP.items() if i == "south"}

# ============================================================
# 公路线路时刻表 (daily frequency, one-way each direction)
# ============================================================
ROUTE_PAIRS = [
    # 金三角 (Golden Triangle)
    ("AKL", "HLZ", 45, "Mainfreight", "semi_trailer"),
    ("AKL", "TRG", 40, "Mainfreight", "semi_trailer"),
    ("HLZ", "TRG", 20, "Fonterra Transport", "tanker"),
    ("HLZ", "ROT", 12, "Toll NZ", "semi_trailer"),
    # 北岛干线
    ("AKL", "WLG", 40, "Mainfreight", "semi_trailer"),
    ("AKL", "NPE", 18, "Toll NZ", "semi_trailer"),
    ("AKL", "NPL", 12, "PBT Transport", "semi_trailer"),
    ("AKL", "ROT", 15, "Toll NZ", "semi_trailer"),
    ("AKL", "TAI", 12, "Mainfreight", "box_van"),
    ("AKL", "WHA", 12, "PBT Transport", "semi_trailer"),
    ("AKL", "GIS", 10, "Toll NZ", "semi_trailer"),
    ("WLG", "PMR", 25, "Mainfreight", "semi_trailer"),
    ("WLG", "NPE", 12, "Hooker Pacific", "semi_trailer"),
    ("ROT", "TAI", 10, "Toll NZ", "box_van"),
    ("NPE", "GIS", 8, "Dynes Transport", "box_van"),
    # 南岛内部
    ("PIC", "CHC", 30, "Mainfreight", "semi_trailer"),
    ("PIC", "NSN", 10, "Dynes Transport", "semi_trailer"),
    ("CHC", "TIM", 18, "Mainfreight", "semi_trailer"),
    ("TIM", "DUD", 12, "HW Richardson Group", "semi_trailer"),
    ("DUD", "IVC", 15, "HW Richardson Group", "semi_trailer"),
    ("CHC", "DUD", 16, "Mainfreight", "semi_trailer"),
    ("CHC", "GBM", 10, "PBT Transport", "flatbed"),
    ("CHC", "ZQN", 12, "Mainfreight", "semi_trailer"),
    ("ZQN", "IVC", 8, "HW Richardson Group", "semi_trailer"),
    ("DUD", "ZQN", 8, "Toll NZ", "semi_trailer"),
    ("CHC", "OAM", 12, "Dynes Transport", "semi_trailer"),
    ("NSN", "BLH", 10, "Dynes Transport", "box_van"),
    ("TIM", "OAM", 8, "Dynes Transport", "box_van"),
    ("TIM", "ZQN", 6, "Toll NZ", "box_van"),
    # 跨库克海峡 (inter-island, via ferry)
    ("AKL", "CHC", 20, "Mainfreight", "semi_trailer"),
    ("AKL", "DUD", 12, "Hooker Pacific", "b_double"),
    ("AKL", "IVC", 6, "HW Richardson Group", "semi_trailer"),
    ("HLZ", "CHC", 10, "Mainfreight", "semi_trailer"),
    ("WLG", "CHC", 12, "Mainfreight", "semi_trailer"),
    ("WLG", "NSN", 8, "Dynes Transport", "semi_trailer"),
    ("AKL", "ZQN", 6, "Big Chill Distribution", "refrigerated"),
    # 纯渡轮短驳 (Cook Strait ferry shuttles)
    ("WLG", "PIC", 40, "Interislander Freight", "semi_trailer"),
]

# Expand to one-way route list
ROAD_ROUTES = []
for org, dst, freq, carrier, vt in ROUTE_PAIRS:
    ROAD_ROUTES.append((org, dst, freq, carrier, vt))
    ROAD_ROUTES.append((dst, org, freq, carrier, vt))

CARRIER_PREFIX = {
    "Mainfreight": "MF", "Toll NZ": "TL", "PBT Transport": "PB", "NZ Post": "NP",
    "CourierPost": "CP", "Big Chill Distribution": "BD", "Hooker Pacific": "HP",
    "Dynes Transport": "DY", "HW Richardson Group": "HW", "Fonterra Transport": "FT",
    "Halls Group": "HG", "Interislander Freight": "IS",
}

VEHICLE_CAPACITY = {"box_van": 4500, "semi_trailer": 22000, "b_double": 30000,
                    "refrigerated": 20000, "tanker": 26000, "flatbed": 24000,
                    "low_loader": 32000}

# 异常原因码 -> 异常类型映射
REASON_TO_EXCEPTION = {
    "congestion": "delay",
    "weather": "delay",
    "road_closure": "road_closure",
    "breakdown": "breakdown",
    "ferry": "ferry_delay",
    "driver_hours": "driver_hours",
    "accident": "accident",
}

# 延误原因权重（非跨岛）
DELAY_REASONS = [
    ("congestion", 0.30), ("weather", 0.22), ("road_closure", 0.14),
    ("breakdown", 0.12), ("driver_hours", 0.10), ("accident", 0.06),
]

# 线路级延误原因 profile（真实地理特征）：
# 库克海峡渡轮大风停航、亚瑟山口积雪封路、金三角拥堵、跨岛含渡轮
ROUTE_DELAY_PROFILES = {
    ("WLG", "PIC"): [("ferry", 0.55), ("weather", 0.35), ("congestion", 0.10)],
    ("PIC", "WLG"): [("ferry", 0.55), ("weather", 0.35), ("congestion", 0.10)],
    ("CHC", "GBM"): [("weather", 0.45), ("road_closure", 0.35), ("accident", 0.10), ("breakdown", 0.10)],
    ("GBM", "CHC"): [("weather", 0.45), ("road_closure", 0.35), ("accident", 0.10), ("breakdown", 0.10)],
    ("AKL", "HLZ"): [("congestion", 0.55), ("weather", 0.20), ("accident", 0.15), ("breakdown", 0.10)],
    ("HLZ", "AKL"): [("congestion", 0.55), ("weather", 0.20), ("accident", 0.15), ("breakdown", 0.10)],
    ("AKL", "TRG"): [("congestion", 0.50), ("weather", 0.20), ("accident", 0.15), ("breakdown", 0.15)],
    ("TRG", "AKL"): [("congestion", 0.50), ("weather", 0.20), ("accident", 0.15), ("breakdown", 0.15)],
    ("AKL", "CHC"): [("ferry", 0.35), ("weather", 0.30), ("congestion", 0.15), ("road_closure", 0.10), ("breakdown", 0.10)],
    ("CHC", "AKL"): [("ferry", 0.35), ("weather", 0.30), ("congestion", 0.15), ("road_closure", 0.10), ("breakdown", 0.10)],
    ("AKL", "DUD"): [("ferry", 0.35), ("weather", 0.30), ("congestion", 0.15), ("road_closure", 0.10), ("breakdown", 0.10)],
    ("DUD", "AKL"): [("ferry", 0.35), ("weather", 0.30), ("congestion", 0.15), ("road_closure", 0.10), ("breakdown", 0.10)],
    ("WLG", "CHC"): [("ferry", 0.45), ("weather", 0.35), ("congestion", 0.20)],
    ("CHC", "WLG"): [("ferry", 0.45), ("weather", 0.35), ("congestion", 0.20)],
    ("AKL", "ZQN"): [("weather", 0.40), ("ferry", 0.30), ("congestion", 0.15), ("road_closure", 0.15)],
    ("ZQN", "AKL"): [("weather", 0.40), ("ferry", 0.30), ("congestion", 0.15), ("road_closure", 0.15)],
}


def get_delay_reasons(org, dst):
    """Return route-specific delay reasons, or the default distribution."""
    return ROUTE_DELAY_PROFILES.get((org, dst), DELAY_REASONS)


# 路况等级 → 通行时间系数（1.0 正常；closed 绕行 3 倍）
CONDITION_TIME_FACTOR = {"clear": 1.0, "slow": 1.3, "congested": 1.8, "closed": 3.0}
CONDITION_SPEED_FACTOR = {"clear": 1.0, "slow": 0.7, "congested": 0.4, "closed": 0.0}
EVENT_TO_CONDITION = {"weather": "slow", "road_closure": "closed", "accident": "congested"}
CONDITION_DESCRIPTION = {
    "clear": "道路畅通",
    "slow": "天气影响，通行缓慢",
    "congested": "交通事故，交通拥堵",
    "closed": "道路封闭，需绕行",
}


class RoadFreightSimulator:
    """Live road freight operations simulator running as a background thread."""

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
        self._active_events = {}  # location -> [EnvironmentEvent]（内存缓存）
        self._road_conditions = {}  # (org, dst) -> {"condition", "description"}
        self.trips_generated = 0
        self.consignments_generated = 0
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
                generate_depots(db)
                self._init_route_schedule()
                self._rebuild_pending_from_db()
                if backfill:
                    self._backfill()
            finally:
                db.close()
        print(f"[road-sim] ready speed={self.speed}x sim_now={self.sim_now.isoformat()}")

    def stop(self):
        self.running = False
        print("[road-sim] stopped")

    def set_speed(self, speed):
        world_clock.set_speed(speed)

    @property
    def speed(self):
        """Global world speed (single clock shared by all modes)."""
        return world_clock.speed

    @property
    def paused(self):
        """Global world pause state (single clock shared by all modes)."""
        return world_clock.paused

    @paused.setter
    def paused(self, value):
        world_clock.paused = value



    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------
    def _init_counters(self):
        """Resume ID counters from existing DB data so restarts don't collide."""
        db = SessionLocal()
        try:
            self._used_trip_numbers = {r[0] for r in db.query(RoadTrip.trip_number).all()}

            cn_row = db.query(RoadConsignment.consignment_number).order_by(
                RoadConsignment.consignment_number.desc()).first()
            self._cn_counter = (int(cn_row[0].split("-")[1]) + 1) if cn_row else 50000001

            evt_row = db.query(RoadTrackingEvent.event_id).filter(
                RoadTrackingEvent.event_id.like("EVT-SIM-%")
            ).order_by(RoadTrackingEvent.event_id.desc()).first()
            self._event_counter = (int(evt_row[0].split("-")[2]) + 1) if evt_row else 1

            exc_row = db.query(RoadException.exception_id).filter(
                RoadException.exception_id.like("EXC-SIM-%")
            ).order_by(RoadException.exception_id.desc()).first()
            self._exc_counter = (int(exc_row[0].split("-")[2]) + 1) if exc_row else 1

            # 通知号也按同计数前缀（NTF-ROAD-xxxxx）：保留期清理可能删掉异常行，
            # 但通知行还在 —— 用两者最大值续号，避免 notification_id 撞唯一约束
            from notification_models import ExceptionNotification as _EN
            ntf_row = db.query(_EN.notification_id).filter(
                _EN.mode == "road",
                _EN.notification_id.like("NTF-ROAD-%"),
            ).order_by(_EN.notification_id.desc()).first()
            if ntf_row:
                self._exc_counter = max(self._exc_counter, int(ntf_row[0].split("-")[2]) + 1)
        finally:
            db.close()

    def _init_route_schedule(self):
        for org, dst, freq, carrier, vt in ROAD_ROUTES:
            key = (org, dst, carrier)
            interval = 1440.0 / (freq * settings.order_scale * settings.road_scale)
            first = self.sim_now - timedelta(hours=6)
            self._route_next_dep[key] = first + timedelta(minutes=random.uniform(0, interval))

    def _backfill(self):
        """Create trips for [sim_now - 6h, sim_now + 12h) so the dashboard has data immediately."""
        for key in list(self._route_next_dep.keys()):
            org, dst, carrier = key
            freq = next(r[2] for r in ROAD_ROUTES if r[0] == org and r[1] == dst and r[3] == carrier)
            interval = 1440.0 / (freq * settings.order_scale * settings.road_scale)
            while self._route_next_dep[key] < self.sim_now + timedelta(hours=12):
                if not self._trip_conflicts(org, dst, carrier, self._route_next_dep[key]):
                    self._create_trip(org, dst, carrier, dep=self._route_next_dep[key])
                self._route_next_dep[key] += timedelta(minutes=interval * random.uniform(0.8, 1.2))

    def _rebuild_pending_from_db(self):
        """Rebuild the in-memory pending event heap after a process restart."""
        db = SessionLocal()
        try:
            trips = db.query(RoadTrip).filter(
                RoadTrip.status != "cancelled",
                RoadTrip.scheduled_departure >= self.sim_now - timedelta(hours=48),
            ).all()
            for trip in trips:
                eff_dep = trip.scheduled_departure + timedelta(minutes=trip.delay_minutes or 0)
                eff_arr = trip.scheduled_arrival + timedelta(minutes=trip.delay_minutes or 0)
                consignments = db.query(RoadConsignment).filter(
                    RoadConsignment.trip_number == trip.trip_number).all()
                if not consignments:
                    continue
                cns = [c.consignment_number for c in consignments]
                if trip.status != "arrived":
                    self._push(eff_dep, "trip_dep", trip.trip_number)
                    self._push(eff_arr, "trip_arr", trip.trip_number)
                    if trip.delay_minutes and not db.query(RoadException).filter(
                            RoadException.consignment_number.in_(cns)
                    ).first():
                        self._push(trip.scheduled_departure - timedelta(minutes=30),
                                   "delay_announce", trip.trip_number)
                for c in consignments:
                    latest_row = db.query(RoadTrackingEvent.event_code).filter(
                        RoadTrackingEvent.consignment_number == c.consignment_number
                    ).order_by(RoadTrackingEvent.timestamp.desc(), RoadTrackingEvent.id.desc()).first()
                    latest = latest_row[0] if latest_row else None
                    chain = self._event_chain(trip, c)
                    codes = [code for _, code, _, _ in chain]
                    if latest and latest in codes:
                        start = codes.index(latest) + 1
                    elif latest == "DLY":
                        start = codes.index("DEP") if "DEP" in codes else 0
                    else:
                        start = 0
                    for ts, code, desc, loc in chain[start:]:
                        self._push(ts, "event", (c.consignment_number, code, desc, loc, None, None, ts))
        finally:
            db.close()

    def _event_chain(self, trip, consignment):
        """Ordered POD milestone chain for a consignment."""
        dep = trip.scheduled_departure
        eff_dep = dep + timedelta(minutes=trip.delay_minutes or 0)
        eff_arr = trip.scheduled_arrival + timedelta(minutes=trip.delay_minutes or 0)
        chain = [
            (dep - timedelta(hours=4), "PUP", "Consignment picked up", consignment.origin_depot),
            (dep - timedelta(hours=2), "LOAD", "Loaded onto vehicle", consignment.origin_depot),
            (eff_dep, "DEP", "Vehicle departed", consignment.origin_depot),
        ]
        if trip.is_inter_island:
            ferry_ts = eff_dep + (eff_arr - eff_dep) * 0.5
            chain.append((ferry_ts, "FERRY", "Cook Strait ferry crossing",
                          "WLG" if consignment.origin_depot in NORTH_ISLAND else "PIC"))
        chain.append((eff_arr, "ARR", "Vehicle arrived", consignment.destination_depot))
        chain.append((eff_arr + timedelta(hours=1), "UNLD", "Cargo unloaded", consignment.destination_depot))
        chain.append((eff_arr + timedelta(hours=2), "POD", "Proof of delivery signed", consignment.destination_depot))
        return chain

    # ----------------------------------------------------------
    # 主 tick
    # ----------------------------------------------------------
    def tick(self):
        with WRITE_LOCK:
            db = SessionLocal()
            try:
                self._spawn_due_trips()
                self._process_pending(db)
                self._derive_trip_statuses(db)
                if (self.sim_now - self._last_env_event_sim) > timedelta(hours=2):
                    self._generate_env_events(db)
                    self._cleanup_env_events(db)
                    self._update_road_conditions(db)
                    self._last_env_event_sim = self.sim_now
                if (self.sim_now - self._last_cleanup_sim) > timedelta(hours=1):
                    self._cleanup(db)
                    self._last_cleanup_sim = self.sim_now
            finally:
                db.close()

    def _generate_env_events(self, db):
        # 世界天气驱动的环境事件（天气 → 延误 因果链）
        from world.causality import weather_events_for_mode
        for loc, event in weather_events_for_mode(db, "road", self.sim_now, self._active_events):
            db.add(event)
            self._active_events.setdefault(loc, []).append({"event_type": event.event_type, "severity": event.severity, "description": event.description, "ends_at": event.ends_at, "impact_at": event.impact_at})
        # 少量随机非天气事件（事故/机械等）保持真实感
        from environment_events import ROAD_LOCATIONS
        if random.random() < 0.25:
            loc = random.choice(ROAD_LOCATIONS)
            event = generate_event(db, "road", loc, self.sim_now)
            if event:
                self._active_events.setdefault(loc, []).append({"event_type": event.event_type, "severity": event.severity, "description": event.description, "ends_at": event.ends_at})
        db.commit()

    def _cleanup_env_events(self, db):
        """清理过期的环境事件（内存 + DB）"""
        now = self.sim_now
        for loc in list(self._active_events.keys()):
            self._active_events[loc] = [e for e in self._active_events[loc] if e["ends_at"] >= now]
            if not self._active_events[loc]:
                del self._active_events[loc]
        from environment_models import EnvironmentEvent
        db.query(EnvironmentEvent).filter(
            EnvironmentEvent.mode == "road", EnvironmentEvent.ends_at < now).delete()

    def _route_active_events(self, org, dst):
        """查路线起终点是否有已过缓冲期、正在实际影响的事件"""
        now = self.sim_now

        def _impacting(loc):
            return [e for e in self._active_events.get(loc, [])
                    if e.get("impact_at", now) <= now <= e["ends_at"]]
        return _impacting(org) + _impacting(dst)

    def _update_road_conditions(self, db):
        """根据活跃环境事件更新各路段路况（内存 + DB）"""
        from road_freight_models import RoadSegment
        self._road_conditions = {}
        for org, dst, freq, carrier, vt in ROAD_ROUTES:
            events = self._route_active_events(org, dst)
            condition = "clear"
            for e in events:
                cond = EVENT_TO_CONDITION.get(e["event_type"])
                if cond and CONDITION_SPEED_FACTOR.get(cond, 1.0) < CONDITION_SPEED_FACTOR.get(condition, 1.0):
                    condition = cond
            self._road_conditions[(org, dst)] = {
                "condition": condition,
                "description": CONDITION_DESCRIPTION.get(condition, "道路畅通"),
            }
            # 同步 DB
            seg = db.query(RoadSegment).filter(
                RoadSegment.origin == org, RoadSegment.destination == dst).first()
            if not seg:
                seg = RoadSegment(origin=org, destination=dst)
                db.add(seg)
            seg.condition = condition
            seg.speed_factor = CONDITION_SPEED_FACTOR.get(condition, 1.0)
            seg.description = CONDITION_DESCRIPTION.get(condition, "道路畅通")
            seg.updated_at = self.sim_now
        db.commit()

    def _get_road_condition(self, org, dst):
        """查路段路况，返回 (condition, description)"""
        c = self._road_conditions.get((org, dst))
        if c:
            return c["condition"], c["description"]
        return "clear", "道路畅通"

    def _spawn_due_trips(self):
        for org, dst, freq, carrier, vt in ROAD_ROUTES:
            key = (org, dst, carrier)
            interval = 1440.0 / (freq * settings.order_scale * settings.road_scale)
            # 时钟大跳/重启后不补造超过 6 小时的历史班次（避免单 tick 卡死与重复堆积）
            if self._route_next_dep[key] < self.sim_now - timedelta(hours=6):
                self._route_next_dep[key] = self.sim_now - timedelta(minutes=30)
            while self._route_next_dep[key] < self.sim_now + timedelta(hours=12):
                if not self._trip_conflicts(org, dst, carrier, self._route_next_dep[key]):
                    self._create_trip(org, dst, carrier, dep=self._route_next_dep[key])
                self._route_next_dep[key] += timedelta(minutes=interval * random.uniform(0.8, 1.2))

    def _trip_conflicts(self, org, dst, carrier, dep):
        """Skip spawning if a trip on the same route already exists within 20 minutes."""
        db = SessionLocal()
        try:
            conflict = db.query(RoadTrip).filter(
                RoadTrip.origin_depot == org,
                RoadTrip.destination_depot == dst,
                RoadTrip.carrier == carrier,
                RoadTrip.scheduled_departure >= dep - timedelta(minutes=20),
                RoadTrip.scheduled_departure <= dep + timedelta(minutes=20),
            ).first()
            return conflict is not None
        finally:
            db.close()

    # ----------------------------------------------------------
    # 运输任务与托运单生成
    # ----------------------------------------------------------
    def _create_trip(self, org, dst, carrier, dep=None):
        route = next((r for r in ROAD_ROUTES if r[0] == org and r[1] == dst and r[3] == carrier), None)
        if route is None:
            return None
        vehicle_type = route[4]
        dep = dep or self._route_next_dep.get((org, dst, carrier), self.sim_now)
        is_inter_island = ISLAND_MAP[org] != ISLAND_MAP[dst]
        dur = trip_duration_hours(org, dst, is_inter_island)
        # 路况影响通行时间：缓行/拥堵/封闭 → 时间放大
        condition, _desc = self._get_road_condition(org, dst)
        dur = dur * CONDITION_TIME_FACTOR.get(condition, 1.0)
        arr = dep + timedelta(hours=dur)

        delay_minutes = 0
        delay_reason = None
        cancelled = not is_inter_island and random.random() < 0.008

        if not cancelled:
            # 环境事件驱动延误：查路线起终点是否有活跃事件
            events = self._route_active_events(org, dst)
            if events:
                event = random.choice(events)
                delay_minutes = random.randint(*SEVERITY_DELAY_MINUTES[event["severity"]])
                delay_reason = EVENT_TYPE_TO_REASON.get(event["event_type"], "weather")
            elif is_inter_island and random.random() < 0.05 * settings.exception_scale:
                delay_minutes = int(random.choice([180, 240, 300, 360, 420, 540, 720]))
                delay_reason = "ferry"
            elif random.random() < 0.03 * settings.exception_scale:
                delay_minutes = int(random.choice([15, 20, 30, 40, 45, 60, 90, 120]))
                delay_reason = random.choice(["breakdown", "driver_hours"])

        distance = road_distance(org, dst)
        capacity = VEHICLE_CAPACITY.get(vehicle_type, 15000)
        trip_number = self._unique_trip_number(carrier)

        db = SessionLocal()
        try:
            trip = RoadTrip(
                trip_number=trip_number, carrier=carrier, vehicle_type=vehicle_type,
                origin_depot=org, destination_depot=dst,
                is_inter_island=is_inter_island,
                scheduled_departure=dep, scheduled_arrival=arr,
                delay_minutes=delay_minutes, delay_reason_code=delay_reason,
                status="cancelled" if cancelled else "scheduled",
                distance_km=distance, capacity_kg=capacity,
                loaded_kg=int(capacity * random.uniform(0.5, 0.95)),
                driver_name=f"Driver {random.randint(100, 999)}",
                driver_hours_remaining=round(random.uniform(4, 13), 1),
                trip_date=dep,
            )
            trip.loaded_pct = round(trip.loaded_kg / capacity * 100, 1)
            db.add(trip)
            db.flush()
            self.trips_generated += 1

            if not cancelled:
                n_cons = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
                for _ in range(n_cons):
                    self._create_consignment(db, trip, dep, arr, delay_minutes)
                eff_dep = dep + timedelta(minutes=delay_minutes)
                eff_arr = arr + timedelta(minutes=delay_minutes)
                if delay_minutes > 0:
                    self._push(dep - timedelta(minutes=30), "delay_announce", trip_number)
                self._push(eff_dep, "trip_dep", trip_number)
                self._push(eff_arr, "trip_arr", trip_number)
            db.commit()
            db.refresh(trip)
            db.expunge(trip)
            return trip
        finally:
            db.close()

    def _unique_trip_number(self, carrier):
        prefix = CARRIER_PREFIX.get(carrier, "XX")
        for _ in range(100):
            num = random.randint(10000, 99999)
            candidate = f"{prefix}{num}"
            if candidate not in self._used_trip_numbers:
                self._used_trip_numbers.add(candidate)
                return candidate
        return f"{prefix}{random.randint(100000, 999999)}"

    def _create_consignment(self, db, trip, dep, arr, delay_minutes):
        org = trip.origin_depot
        dst = trip.destination_depot
        is_inter_island = trip.is_inter_island

        if org in {"TRG", "NPE", "NPL", "GIS"} or dst in {"TRG", "NPE", "NPL", "GIS"}:
            pool = EXPORT_COMMODITIES
            route_type = "regional"
        elif org in {"AKL", "CHC"} and dst in {"AKL", "CHC"}:
            pool = IMPORT_COMMODITIES if random.random() < 0.3 else DOMESTIC_COMMODITIES
            route_type = "line_haul"
        elif is_inter_island:
            pool = DOMESTIC_COMMODITIES
            route_type = "inter_island"
        else:
            pool = DOMESTIC_COMMODITIES if random.random() < 0.7 else EXPORT_COMMODITIES
            route_type = "line_haul" if road_distance(org, dst) > 250 else "regional"

        dur_hours = trip_duration_hours(org, dst, is_inter_island)

        # 拼装（LTL）：~40% 的托运单装多票货，每票独立货主/货值/SLA
        is_ltl = random.random() < 0.4
        n_lines = random.randint(2, 5) if is_ltl else 1

        # 逐票生成货物数据
        lines_meta = []
        for _ in range(n_lines):
            _desc, _hs, _vr, _tiers, _vt, _temp = random.choice(pool)
            _customer, _tier = random.choice(CUSTOMERS)
            if random.random() < 0.08:
                _tier = "VIP"
            elif _tier == "VIP" and random.random() < 0.7:
                _tier = "high"
            _svc = random.choices(["priority", "standard", "economy"], weights=[0.18, 0.62, 0.2])[0]
            _sla_h = max(8.0, round((dur_hours + 2.0) * random.choice([1.3, 1.6, 2.0, 2.5]), 1))
            if _svc == "priority":
                _sla_h = max(4.0, _sla_h * 0.6)
            lines_meta.append({
                "desc": _desc, "hs": _hs, "value": random.randint(*_vr),
                "vt": _vt, "temp": _temp, "customer": _customer,
                "tier": _tier, "svc": _svc, "sla_h": _sla_h,
            })

        # 主票 = 最高货值票（托运单字段镜像它，保持向后兼容）
        main = max(lines_meta, key=lambda d: d["value"])
        desc, hs, value = main["desc"], main["hs"], main["value"]
        vt, temp = main["vt"], main["temp"]
        customer, tier = main["customer"], main["tier"]
        service = main["svc"]
        sla_h = main["sla_h"]
        policy = get_policy("road", service)

        pieces = random.randint(2, 40)
        weight = round(pieces * random.uniform(50, 400), 1)
        volume = round(weight / 160.0, 2)

        priority = "normal"
        if "urgent" in desc or random.random() < 0.06:
            priority = "critical"
        elif tier in ("VIP", "high") and random.random() < 0.3:
            priority = "high"
        if priority == "critical":
            service = "priority"

        temp_min, temp_max = None, None
        if temp:
            temp_min, temp_max = temp

        cn = f"RD-{self._cn_counter:08d}"
        self._cn_counter += 1

        delivery_buffer = 2.0
        eff_arr = arr + timedelta(minutes=delay_minutes)
        cons = RoadConsignment(
            consignment_number=cn, trip_number=trip.trip_number,
            route_type=route_type, origin_depot=org, destination_depot=dst,
            pieces=pieces, gross_weight_kg=weight, volume_cbm=volume,
            commodity_code=hs, commodity_desc=desc,
            shipper_name=customer, consignee_name=f"{customer} DC",
            customer_name=customer, customer_tier=tier,
            declared_value_nzd=float(value), service_level=service,
            priority=priority,
            is_ltl=is_ltl,
            sla_tier=map_service_level_to_tier(service),
            temp_required_c=temp_min if (vt == "refrigerated" and temp_min is not None) else None,
            temp_min_c=temp_min, temp_max_c=temp_max,
            dg_class="3" if "DGR3" in desc else None,
            un_number="UN1133" if "DGR3" in desc else None,
            current_status="booked", current_location=org,
            scheduled_delivery=eff_arr + timedelta(hours=delivery_buffer),
            estimated_delivery=eff_arr + timedelta(hours=delivery_buffer),
            sla_deadline=dep + timedelta(hours=sla_h),
            sla_grace_deadline=dep + timedelta(hours=sla_h) + timedelta(hours=policy["grace_hours"]),
        )
        db.add(cons)
        db.flush()
        self.consignments_generated += 1

        # 票级货物行（LTL 多票 / FTL 单票），每票独立货主/货值/SLA
        for i, lm in enumerate(lines_meta):
            _lp = get_policy("road", lm["svc"])
            _ldl = dep + timedelta(hours=lm["sla_h"])
            _ltmin, _ltmax = (lm["temp"][0], lm["temp"][1]) if lm["temp"] else (None, None)
            db.add(ConsignmentLine(
                consignment_number=cn, line_number=i + 1,
                commodity_code=lm["hs"], commodity_desc=lm["desc"],
                shipper_name=lm["customer"], consignee_name=f"{lm['customer']} DC",
                customer_name=lm["customer"], customer_tier=lm["tier"],
                declared_value_nzd=float(lm["value"]),
                pieces=max(1, pieces // n_lines),
                gross_weight_kg=round(weight / n_lines, 1),
                service_level=lm["svc"], sla_tier=map_service_level_to_tier(lm["svc"]),
                temp_min_c=_ltmin, temp_max_c=_ltmax,
                scheduled_delivery=eff_arr + timedelta(hours=delivery_buffer),
                sla_deadline=_ldl,
                sla_grace_deadline=_ldl + timedelta(hours=_lp["grace_hours"]),
            ))

        self._schedule_consignment_events(cons, trip, dep, arr, delay_minutes)

    def _schedule_consignment_events(self, cons, trip, dep, arr, delay_minutes):
        eff_dep = dep + timedelta(minutes=delay_minutes)
        eff_arr = arr + timedelta(minutes=delay_minutes)
        cn = cons.consignment_number
        org, dst = trip.origin_depot, trip.destination_depot

        self._push(dep - timedelta(hours=4), "event", (cn, "PUP", "Consignment picked up", org, None, None, dep - timedelta(hours=4)))
        self._push(dep - timedelta(hours=2), "event", (cn, "LOAD", "Loaded onto vehicle", org, None, None, dep - timedelta(hours=2)))

        if trip.is_inter_island:
            ferry_ts = eff_dep + (eff_arr - eff_dep) * 0.5
            self._push(ferry_ts, "event", (cn, "FERRY", "Cook Strait ferry crossing",
                                           "WLG" if org in NORTH_ISLAND else "PIC", None, None, ferry_ts))

        self._push(eff_arr + timedelta(hours=2), "pod", (cn, eff_arr + timedelta(hours=2)))

        if cons.temp_min_c is not None and random.random() < 0.03 * settings.exception_scale:
            self._push(eff_dep + (eff_arr - eff_dep) * random.uniform(0.3, 0.8), "temp_alert", cn)

        # 货物丢失/失踪 (~0.5%)
        if random.random() < 0.005:
            self._push(eff_arr + timedelta(hours=1), "lost", cn)

        # 追踪/数据异常 (~1%)
        if random.random() < 0.01:
            self._push(eff_dep + (eff_arr - eff_dep) * random.uniform(0.2, 0.7), "tracking_gap", cn)

        # 派送失败 (~1%)
        if random.random() < 0.01:
            self._push(eff_arr + timedelta(hours=3), "failed_delivery", cn)

    # ----------------------------------------------------------
    # 事件堆
    # ----------------------------------------------------------
    def _push(self, sim_time, kind, payload):
        self._pending_seq += 1
        heapq.heappush(self._pending, (sim_time, self._pending_seq, kind, payload))

    def _process_pending(self, db):
        # 每 tick 最多处理 300 个到期事件：时钟大跳/重启后积压分批消化，避免单 tick 卡死
        import time as _time
        budget = 150
        processed = 0
        _t0 = _time.monotonic()
        while budget > 0 and (_time.monotonic() - _t0) < 5.0 and self._pending and self._pending[0][0] <= self.sim_now:
            budget -= 1
            processed += 1
            # 每 50 个事件提交一次：单个 tick 的写锁占用不超过数秒（前端 3s 轮询不撞死窗）
            if processed % 50 == 0:
                db.commit()
            _, _, kind, payload = heapq.heappop(self._pending)
            try:
                handler = getattr(self, f"_on_{kind}")
                handler(db, payload)
            except AttributeError:
                print(f"[road-sim] unknown pending kind: {kind}")
            except Exception as e:
                print(f"[road-sim] pending handler error ({kind}): {e}")

    # ----------------------------------------------------------
    # 事件处理器
    # ----------------------------------------------------------
    def _on_event(self, db, payload):
        cn, code, desc, loc, reason, message, ts = payload
        self._insert_event(db, cn, code, desc, loc, reason, message, ts=ts)
        # 重建路径（_rebuild_pending_from_db）用通用 event 链恢复里程碑：
        # POD 必须驱动交付状态机与 SLA/票级判定，否则重启后货物卡在未交付
        if code == "POD":
            c = db.query(RoadConsignment).filter(RoadConsignment.consignment_number == cn).first()
            if c and c.current_status != "POD":
                c.current_status = "POD"
                c.current_location = c.destination_depot
                c.delivered_at = ts or self.sim_now
                self._finalize_pod(db, c)

    def _insert_event(self, db, cn, code, desc, loc, reason=None, message=None, ts=None):
        event = RoadTrackingEvent(
            event_id=f"EVT-SIM-{self._event_counter:09d}",
            consignment_number=cn, event_code=code, event_desc=desc,
            location=loc, timestamp=ts or self.sim_now, source="tms",
            reason_code=reason, message=message or f"TMS status update: {code} {loc}"
        )
        self._event_counter += 1
        self.events_generated += 1
        db.add(event)

    def _on_trip_dep(self, db, trip_number):
        trip = db.query(RoadTrip).filter(RoadTrip.trip_number == trip_number).first()
        if not trip or trip.status == "cancelled":
            return
        trip.status = "in_transit"
        eff_dep = trip.scheduled_departure + timedelta(minutes=trip.delay_minutes or 0)
        trip.actual_departure = eff_dep
        db.flush()
        for c in db.query(RoadConsignment).filter(RoadConsignment.trip_number == trip_number).all():
            dup = db.query(RoadTrackingEvent).filter(
                RoadTrackingEvent.consignment_number == c.consignment_number,
                RoadTrackingEvent.event_code == "DEP"
            ).first()
            if dup:
                continue
            if c.current_status in ("booked", "PUP", "LOAD"):
                c.current_status = "DEP"
                c.current_location = trip.destination_depot
            self._insert_event(db, c.consignment_number, "DEP", "Vehicle departed",
                               trip.origin_depot, ts=eff_dep)

    def _on_trip_arr(self, db, trip_number):
        trip = db.query(RoadTrip).filter(RoadTrip.trip_number == trip_number).first()
        if not trip or trip.status == "cancelled":
            return
        trip.status = "arrived"
        eff_arr = trip.scheduled_arrival + timedelta(minutes=trip.delay_minutes or 0)
        trip.actual_arrival = eff_arr
        db.flush()
        if trip.actual_departure:
            dwell = (trip.actual_arrival - trip.actual_departure).total_seconds() / 3600
            anomaly = detector.observe("road", "DEP_ARR", dwell)
            if anomaly:
                for c in db.query(RoadConsignment).filter(RoadConsignment.trip_number == trip_number).all():
                    self._create_predicted_exception(db, c, anomaly, "DEP->ARR")
                    break
        for c in db.query(RoadConsignment).filter(RoadConsignment.trip_number == trip_number).all():
            dup = db.query(RoadTrackingEvent).filter(
                RoadTrackingEvent.consignment_number == c.consignment_number,
                RoadTrackingEvent.event_code == "ARR"
            ).first()
            if dup:
                continue
            c.current_status = "ARR"
            c.current_location = trip.destination_depot
            self._insert_event(db, c.consignment_number, "ARR", "Vehicle arrived",
                               trip.destination_depot, ts=eff_arr)
            self._push(eff_arr + timedelta(hours=1), "event",
                       (c.consignment_number, "UNLD", "Cargo unloaded", trip.destination_depot,
                        None, None, eff_arr + timedelta(hours=1)))

    def _on_delay_announce(self, db, trip_number):
        trip = db.query(RoadTrip).filter(RoadTrip.trip_number == trip_number).first()
        if not trip or trip.status == "cancelled" or not trip.delay_minutes:
            return
        exc_type = REASON_TO_EXCEPTION.get(trip.delay_reason_code, "delay")
        for c in db.query(RoadConsignment).filter(RoadConsignment.trip_number == trip_number).all():
            dup = db.query(RoadException).filter(
                RoadException.consignment_number == c.consignment_number,
                RoadException.exception_type == exc_type,
                RoadException.status != "resolved"
            ).count()
            if dup:
                continue
            delay_hours = trip.delay_minutes / 60.0
            root_cause, diagnosis, recovery = self._diagnose(trip, exc_type)
            self._create_exception(db, c, exc_type, root_cause, delay_hours, diagnosis, recovery,
                                   reason_code=trip.delay_reason_code)
            self._insert_event(db, c.consignment_number, "DLY", "Delay advisory received",
                               trip.origin_depot, reason=trip.delay_reason_code,
                               ts=trip.scheduled_departure - timedelta(minutes=30))

    def _diagnose(self, trip, exc_type):
        reason = trip.delay_reason_code
        if exc_type == "road_closure":
            return ("SH1 closed due to slip near Oamaru",
                    "NZTA reports SH1 closed after heavy rain caused a slip. Detour via inland route adds delay.",
                    ["reroute", "wait"])
        if exc_type == "ferry_delay":
            return ("Cook Strait ferry sailing cancelled due to strong winds",
                    "MetService issued gale warning for Cook Strait. Interislander cancelled sailings. "
                    "Consignment re-booked on next sailing.",
                    ["wait", "reroute"])
        if exc_type == "breakdown":
            return ("Vehicle breakdown en route",
                    "Vehicle mechanical fault detected. Recovery vehicle dispatched, load transferred to substitute unit.",
                    ["substitute_vehicle", "wait"])
        if exc_type == "driver_hours":
            return ("Driver exceeded legal work-time limits",
                    "Logbook audit shows driver approaching 13h work limit. Mandatory rest required. "
                    "Second driver dispatched.",
                    ["dispatch_second_driver", "wait"])
        if exc_type == "accident":
            return ("Traffic incident on route",
                    "Minor traffic incident causing lane closure and congestion on the corridor.",
                    ["reroute", "wait"])
        return (f"Trip delayed: {reason}",
                f"Operational delay ({reason}) on {trip.trip_number}. Revised ETA updated.",
                ["wait"])

    def _on_temp_alert(self, db, cn):
        c = db.query(RoadConsignment).filter(RoadConsignment.consignment_number == cn).first()
        if not c:
            return
        c.temp_excursion_alert = True
        self._create_exception(
            db, c, "temp_excursion",
            f"Temperature excursion outside {c.temp_min_c}-{c.temp_max_c}C range during transit",
            0.0,
            "Reefer temperature logger deviation detected. Shipper stability data supports short excursion. "
            "Recommend expedited delivery and customer notification.",
            ["wait", "substitute_vehicle", "express_courier"]
        )
        self._insert_event(db, cn, "DLY", "Temperature excursion alert",
                           c.destination_depot, reason="temp_excursion")

    def _on_lost(self, db, cn):
        c = db.query(RoadConsignment).filter(RoadConsignment.consignment_number == cn).first()
        if not c:
            return
        self._create_exception(
            db, c, "lost",
            "Consignment unit cannot be located",
            0.0,
            "Expected scan absent and the handling unit cannot be located. Network trace initiated.",
            ["network_trace", "replacement"]
        )

    def _on_tracking_gap(self, db, cn):
        c = db.query(RoadConsignment).filter(RoadConsignment.consignment_number == cn).first()
        if not c:
            return
        self._create_exception(
            db, c, "tracking_gap",
            "No valid tracking event received",
            0.0,
            "Tracking feed stale; physical status unconfirmed.",
            ["resend_event", "integration_ticket"]
        )

    def _on_failed_delivery(self, db, cn):
        c = db.query(RoadConsignment).filter(RoadConsignment.consignment_number == cn).first()
        if not c:
            return
        self._create_exception(
            db, c, "failed_delivery",
            "Delivery attempt failed at receiving site",
            0.0,
            "Receiving site issue prevented handover. Redelivery rescheduled.",
            ["redelivery", "reschedule"]
        )

    def _on_pod(self, db, payload):
        cn, ts = payload
        c = db.query(RoadConsignment).filter(RoadConsignment.consignment_number == cn).first()
        if not c:
            return
        db.flush()
        dup = db.query(RoadTrackingEvent).filter(
            RoadTrackingEvent.consignment_number == cn,
            RoadTrackingEvent.event_code == "POD"
        ).first()
        if dup:
            return
        c.current_status = "POD"
        c.current_location = c.destination_depot
        c.delivered_at = ts or self.sim_now
        self._insert_event(db, cn, "POD", "Proof of delivery signed", c.destination_depot)
        self._finalize_pod(db, c)

    def _finalize_pod(self, db, c):
        """交付收尾：箱级 SLA 判定 + 票级独立判罚（_on_pod 与重建路径共用）。"""
        cn = c.consignment_number
        # SLA 违约判定
        policy = get_policy("road", c.service_level or "standard")
        excused = False
        for e in db.query(RoadException).filter(RoadException.consignment_number == cn).all():
            if is_excused(e.exception_type, None) or any(k in (e.root_cause or "").lower() for k in ("weather", "road closure", "ferry", "slip")):
                excused = True
                break
        is_breached, breach_type, penalty = evaluate_breach(
            c.delivered_at, c.sla_deadline, policy["grace_hours"], policy["penalty_pct"],
            c.declared_value_nzd, excused)
        if is_breached or breach_type:
            c.is_sla_breached = is_breached
            c.breach_type = breach_type
            c.sla_penalty_nzd = penalty

        # 票级 SLA 判定：LTL 托运单内每票货独立判罚
        for line in db.query(ConsignmentLine).filter(ConsignmentLine.consignment_number == cn).all():
            _lp = get_policy("road", line.service_level or "standard")
            _b, _bt, _pen = evaluate_breach(
                c.delivered_at, line.sla_deadline, _lp["grace_hours"], _lp["penalty_pct"],
                line.declared_value_nzd, excused)
            if _b or _bt:
                line.is_sla_breached = _b
                line.breach_type = _bt
                line.sla_penalty_nzd = _pen
            # 票级异常：该票正式违约时，生成只针对该票的异常并通知该票货主
            if _b:
                late_hours = max(0.0, (c.delivered_at - line.sla_deadline).total_seconds() / 3600)
                self._create_exception(
                    db, c, "sla_breach",
                    f"票{line.line_number} {line.commodity_desc} SLA 违约（晚于截止 {line.sla_deadline.strftime('%m-%d %H:%M')}）",
                    late_hours,
                    f"Consignment line {line.line_number} ({line.commodity_desc}, {line.customer_name}) "
                    f"exceeded its SLA commitment. Estimated penalty {_pen or 0:.0f} NZD.",
                    ["waive", "compensate"],
                    consignment_line=line,
                )

    def _create_exception(self, db, consignment, exc_type, root_cause, delay_hours, diagnosis, recovery, reason_code=None, consignment_line=None):
        from exception_ops import reopen_if_closed
        reopen_if_closed(db, "road", consignment.consignment_number, self.sim_now)
        # 票级异常时用票的货物字段（货主/货值/温度/SLA/HS），通知也只发给该票货主
        _value = consignment_line.declared_value_nzd if consignment_line else consignment.declared_value_nzd
        _tier = consignment_line.customer_tier if consignment_line else consignment.customer_tier
        _hs = consignment_line.commodity_code if consignment_line else consignment.commodity_code
        _temp_required = (consignment_line.temp_min_c is not None) if consignment_line else (consignment.temp_min_c is not None)
        _sla_dl = consignment_line.sla_deadline if consignment_line else consignment.sla_deadline
        _customer = consignment_line.customer_name if consignment_line else consignment.customer_name
        _ref = consignment.consignment_number + (f"/票{consignment_line.line_number}" if consignment_line else "")
        eff_delivery = consignment.estimated_delivery or (self.sim_now + timedelta(hours=delay_hours))
        sla_breach = (eff_delivery - _sla_dl).total_seconds() / 3600 if _sla_dl else delay_hours
        mapped = "delay" if exc_type in ("ferry_delay", "delay", "road_closure", "breakdown",
                                         "driver_hours", "accident") else exc_type
        score = calculate_risk_score(
            cargo_value=_value,
            customer_tier=_tier,
            sla_breach_hours=sla_breach,
            exception_type=mapped
        )
        risk_level = categorize_risk(score)
        severity = calculate_severity(
            score, sla_breach, exc_type,
            is_dg=consignment.dg_class is not None,
            temp_required=_temp_required,
            perishable=(_hs or "").startswith(("02", "03", "04", "05", "07", "08", "16", "20", "21")),
        )
        cls = classifier.classify_and_learn(root_cause or diagnosis or "", exc_type)
        category, root_cause_cat = map_exception_to_categories(exc_type, reason_code)
        impact = DOWNSTREAM_IMPACT.get(exc_type, "delay -> SLA risk")
        cost = estimate_recovery_cost(exc_type, _value)
        learned = apply_learned_preferences(db, category)
        trigger_event_id = None
        detection_latency = None
        _ev = db.query(RoadTrackingEvent).filter(
            RoadTrackingEvent.consignment_number == consignment.consignment_number,
            RoadTrackingEvent.timestamp <= self.sim_now,
        ).order_by(RoadTrackingEvent.timestamp.desc()).first()
        if _ev and (self.sim_now - _ev.timestamp) <= timedelta(hours=24):
            trigger_event_id = _ev.event_id
            detection_latency = round((self.sim_now - _ev.timestamp).total_seconds() / 60.0, 1)
        best_action, action_reason = select_best_recovery(category, _value, _tier, recovery, learned)
        if cls["is_ood"] and settings.llm_enabled:
            diagnosis = enhance_diagnosis(exc_type, root_cause, diagnosis)
        if cls["is_ood"]:
            _status, _requires = "escalated", True
        elif risk_level == "low" and cls["classification_decision"] == "automatic":
            _status, _requires = "diagnosed", False
        else:
            _status, _requires = "pending_approval", True
        exc = RoadException(
            exception_id=f"EXC-SIM-{self._exc_counter:06d}",
            consignment_number=consignment.consignment_number,
            consignment_line_id=consignment_line.id if consignment_line else None,
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
            recovery_options=recovery_options_json(category, _value, _tier, recovery, learned),
            trigger_event_id=trigger_event_id,
            detection_latency_minutes=detection_latency,
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
            sla_clock_paused=exc_type == "failed_delivery",
            pause_reason="CU-06" if exc_type == "failed_delivery" else None,
        )
        self._exc_counter += 1
        self.exceptions_generated += 1
        db.add(exc)
        db.flush()
        self._notify(db, exc, _customer, _ref,
                     category, root_cause, recovery, cls["classification_confidence"],
                     consignment.estimated_delivery)

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
            notification_id=f"NTF-ROAD-{self._exc_counter:06d}",
            mode="road",
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

    def _create_predicted_exception(self, db, consignment, anomaly, transition):
        """Create a predictive anomaly exception from a dwell-time outlier."""
        best_action, action_reason = select_best_recovery(None, None, None, ["monitor", "reroute"])
        trigger_event_id = None
        detection_latency = None
        _ev = db.query(RoadTrackingEvent).filter(
            RoadTrackingEvent.consignment_number == consignment.consignment_number,
            RoadTrackingEvent.timestamp <= self.sim_now,
        ).order_by(RoadTrackingEvent.timestamp.desc()).first()
        if _ev and (self.sim_now - _ev.timestamp) <= timedelta(hours=24):
            trigger_event_id = _ev.event_id
            detection_latency = round((self.sim_now - _ev.timestamp).total_seconds() / 60.0, 1)
        exc = RoadException(
            exception_id=f"EXC-SIM-{self._exc_counter:06d}",
            consignment_number=consignment.consignment_number,
            exception_type="predicted_anomaly",
            severity="medium",
            risk_level="medium",
            risk_score=50,
            detected_at=self.sim_now,
            root_cause=f"{transition} dwell time abnormal for {consignment.consignment_number}",
            ai_diagnosis=f"Dwell time {transition} exceeds recent P95 by {anomaly['anomaly_score']}x. Potential route delay or congestion.",
            ai_confidence=round(random.uniform(0.7, 0.85), 2),
            status="detected",
            requires_human_approval=True,
            recovery_options=recovery_options_json(None, None, None, ["monitor", "reroute"]),
            recommended_action=best_action,
            recommendation_reason=action_reason,
            trigger_event_id=trigger_event_id,
            detection_latency_minutes=detection_latency,
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
    def _derive_trip_statuses(self, db):
        active = db.query(RoadTrip).filter(
            RoadTrip.status.in_(["scheduled", "loading", "in_transit", "delayed"])
        ).all()
        for trip in active:
            eff_dep = trip.scheduled_departure + timedelta(minutes=trip.delay_minutes or 0)
            eff_arr = trip.scheduled_arrival + timedelta(minutes=trip.delay_minutes or 0)
            if self.sim_now < trip.scheduled_departure - timedelta(minutes=40):
                new_status = "scheduled"
            elif self.sim_now < eff_dep:
                new_status = "loading" if not trip.delay_minutes else "delayed"
            elif self.sim_now < eff_arr:
                new_status = "in_transit"
            else:
                new_status = "arrived"
                trip.actual_arrival = eff_arr
            if new_status != trip.status:
                trip.status = new_status

    # ----------------------------------------------------------
    # 数据保留清理
    # ----------------------------------------------------------
    def _cleanup(self, db):
        cutoff = self.sim_now - timedelta(hours=settings.road_sim_retention_hours)
        old_cons = db.query(RoadConsignment).filter(
            RoadConsignment.delivered_at.isnot(None),
            RoadConsignment.delivered_at < cutoff
        ).all()
        if old_cons:
            cns = [c.consignment_number for c in old_cons]
            db.query(RoadException).filter(RoadException.consignment_number.in_(cns)).delete(synchronize_session=False)
            db.query(RoadTrackingEvent).filter(RoadTrackingEvent.consignment_number.in_(cns)).delete(synchronize_session=False)
            for c in old_cons:
                db.delete(c)
        old_trips = db.query(RoadTrip).filter(
            RoadTrip.status.in_(["arrived", "cancelled"]),
            RoadTrip.scheduled_arrival < cutoff - timedelta(hours=24)
        ).all()
        for t in old_trips:
            db.delete(t)
        db.commit()


# 全局单例
simulator = RoadFreightSimulator()

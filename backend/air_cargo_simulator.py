"""
Live air cargo simulator - continuously generates NZ domestic and international
air freight flights, waybills, tracking events and exceptions in real time.
实时空运模拟器 - 持续生成新西兰国内与国际空运航班、运单、追踪事件和异常

Design:
- Simulation clock advances at configurable speed (default 60x: 1 real second = 1 sim minute)
- ~330 flights/day across domestic trunk, regional, freighter and international routes
- Each flight carries 2-6 waybills with realistic NZ cargo profiles
- Flight lifecycle: scheduled -> boarding -> departed -> landed (-> customs -> delivered)
- Exception injection: delays (~10%), cancellations (~1.5% domestic), MPI customs holds,
  cold-chain temperature excursions, misroutes
- Data retention cleanup to keep the demo database bounded
"""
import heapq
import json
import random
import threading
import time
from datetime import datetime, timedelta

from database import SessionLocal, WRITE_LOCK
from air_cargo_models import (
    Airport, AirFlight, AirWaybill, AirTrackingEvent, AirCustomsInspection, AirException
)
from air_cargo_seed import generate_airports, flight_duration as _base_flight_duration
from risk_calculator import calculate_risk_score, categorize_risk, calculate_severity
from config import settings
from event_classifier import classifier
from anomaly_detector import detector

# ============================================================
# 航班时刻表 (daily frequencies, one-way)
# ============================================================
DOMESTIC_ROUTES = [
    # (origin, dest, freq/day, airline, aircraft, freighter)
    ("AKL", "CHC", 16, "Air New Zealand Cargo", "A320neo", False),
    ("CHC", "AKL", 16, "Air New Zealand Cargo", "A320neo", False),
    ("AKL", "WLG", 18, "Air New Zealand Cargo", "A321neo", False),
    ("WLG", "AKL", 18, "Air New Zealand Cargo", "A321neo", False),
    ("CHC", "WLG", 10, "Air New Zealand Cargo", "A320neo", False),
    ("WLG", "CHC", 10, "Air New Zealand Cargo", "A320neo", False),
    ("AKL", "ZQN", 8, "Air New Zealand Cargo", "A320neo", False),
    ("ZQN", "AKL", 8, "Air New Zealand Cargo", "A320neo", False),
    ("CHC", "ZQN", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("ZQN", "CHC", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "DUD", 6, "Air New Zealand Cargo", "A320neo", False),
    ("DUD", "AKL", 6, "Air New Zealand Cargo", "A320neo", False),
    ("CHC", "DUD", 6, "Air New Zealand Cargo", "ATR72-600", False),
    ("DUD", "CHC", 6, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "NSN", 6, "Air New Zealand Cargo", "ATR72-600", False),
    ("NSN", "AKL", 6, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "NPE", 6, "Air New Zealand Cargo", "ATR72-600", False),
    ("NPE", "AKL", 6, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "HLZ", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("HLZ", "AKL", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "TRG", 5, "Air New Zealand Cargo", "ATR72-600", False),
    ("TRG", "AKL", 5, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "PMR", 5, "Air New Zealand Cargo", "ATR72-600", False),
    ("PMR", "AKL", 5, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "NPL", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("NPL", "AKL", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "GIS", 3, "Air New Zealand Cargo", "ATR72-600", False),
    ("GIS", "AKL", 3, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "ROT", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("ROT", "AKL", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("CHC", "IVC", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("IVC", "CHC", 4, "Air New Zealand Cargo", "ATR72-600", False),
    ("AKL", "IVC", 2, "Air New Zealand Cargo", "A320neo", False),
    ("IVC", "AKL", 2, "Air New Zealand Cargo", "A320neo", False),
    ("WLG", "ZQN", 3, "Air New Zealand Cargo", "ATR72-600", False),
    ("ZQN", "WLG", 3, "Air New Zealand Cargo", "ATR72-600", False),
    # Dedicated freighters
    ("AKL", "CHC", 2, "Parcelair", "B737-400F", True),
    ("CHC", "AKL", 2, "Parcelair", "B737-400F", True),
    ("AKL", "WLG", 1, "Parcelair", "B737-400F", True),
    ("WLG", "AKL", 1, "Parcelair", "B737-400F", True),
    ("CHC", "HLZ", 1, "Parcelair", "B737-400F", True),
    ("HLZ", "CHC", 1, "Parcelair", "B737-400F", True),
    ("AKL", "NPE", 1, "Airwork", "B737-400F", True),
    ("NPE", "AKL", 1, "Airwork", "B737-400F", True),
]

INTL_ROUTES = [
    # (origin, dest, freq/day, airline, aircraft, freighter)
    ("AKL", "SYD", 4, "Qantas Freight", "B737-800", False),
    ("AKL", "SYD", 2, "Air New Zealand Cargo", "A321neo", False),
    ("SYD", "AKL", 4, "Qantas Freight", "B737-800", False),
    ("SYD", "AKL", 2, "Air New Zealand Cargo", "A321neo", False),
    ("AKL", "MEL", 3, "Qantas Freight", "B737-800", False),
    ("MEL", "AKL", 3, "Qantas Freight", "B737-800", False),
    ("AKL", "BNE", 2, "Air New Zealand Cargo", "A321neo", False),
    ("BNE", "AKL", 2, "Air New Zealand Cargo", "A321neo", False),
    ("AKL", "PVG", 2, "Air New Zealand Cargo", "B787-9", False),
    ("PVG", "AKL", 2, "Air New Zealand Cargo", "B787-9", False),
    ("AKL", "CAN", 1, "China Southern Cargo", "A330-300", False),
    ("CAN", "AKL", 1, "China Southern Cargo", "A330-300", False),
    ("AKL", "HKG", 2, "Cathay Pacific Cargo", "A350-1000", False),
    ("HKG", "AKL", 2, "Cathay Pacific Cargo", "A350-1000", False),
    ("AKL", "SIN", 3, "Singapore Airlines Cargo", "A350-900", False),
    ("SIN", "AKL", 3, "Singapore Airlines Cargo", "A350-900", False),
    ("AKL", "NRT", 1, "Air New Zealand Cargo", "B787-9", False),
    ("NRT", "AKL", 1, "Air New Zealand Cargo", "B787-9", False),
    ("AKL", "ICN", 1, "Korean Air Cargo", "B777-300ER", False),
    ("ICN", "AKL", 1, "Korean Air Cargo", "B777-300ER", False),
    ("AKL", "LAX", 2, "Air New Zealand Cargo", "B777-300ER", False),
    ("LAX", "AKL", 2, "Air New Zealand Cargo", "B777-300ER", False),
    ("AKL", "LAX", 1, "Atlas Air", "B747-8F", True),
    ("LAX", "AKL", 1, "Atlas Air", "B747-8F", True),
    ("AKL", "SFO", 1, "United Cargo", "B787-9", False),
    ("SFO", "AKL", 1, "United Cargo", "B787-9", False),
    ("AKL", "DXB", 1, "Emirates SkyCargo", "A380-800", False),
    ("DXB", "AKL", 1, "Emirates SkyCargo", "A380-800", False),
    ("AKL", "NAN", 3, "Fiji Airways", "A330-200", False),
    ("NAN", "AKL", 3, "Fiji Airways", "A330-200", False),
    ("AKL", "RAR", 1, "Air New Zealand Cargo", "A321neo", False),
    ("RAR", "AKL", 1, "Air New Zealand Cargo", "A321neo", False),
    ("AKL", "APW", 1, "Air New Zealand Cargo", "A320neo", False),
    ("APW", "AKL", 1, "Air New Zealand Cargo", "A320neo", False),
    ("AKL", "TBU", 1, "Air New Zealand Cargo", "A320neo", False),
    ("TBU", "AKL", 1, "Air New Zealand Cargo", "A320neo", False),
    ("CHC", "SYD", 1, "Air New Zealand Cargo", "A320neo", False),
    ("SYD", "CHC", 1, "Air New Zealand Cargo", "A320neo", False),
    ("CHC", "CAN", 1, "China Southern Cargo", "A330-300", False),
    ("CAN", "CHC", 1, "China Southern Cargo", "A330-300", False),
    ("CHC", "SIN", 1, "Singapore Airlines Cargo", "A350-900", False),
    ("SIN", "CHC", 1, "Singapore Airlines Cargo", "A350-900", False),
    ("CHC", "MEL", 1, "Qantas Freight", "B737-800", False),
    ("MEL", "CHC", 1, "Qantas Freight", "B737-800", False),
    ("WLG", "SYD", 2, "Air New Zealand Cargo", "A321neo", False),
    ("SYD", "WLG", 2, "Air New Zealand Cargo", "A321neo", False),
    ("ZQN", "SYD", 1, "Qantas Freight", "B737-800", False),
    ("SYD", "ZQN", 1, "Qantas Freight", "B737-800", False),
    ("ZQN", "MEL", 1, "Air New Zealand Cargo", "A321neo", False),
    ("MEL", "ZQN", 1, "Air New Zealand Cargo", "A321neo", False),
]

NZ_AIRPORTS_SET = {r[0] for r in DOMESTIC_ROUTES} | {r[1] for r in DOMESTIC_ROUTES} | \
                  {r[0] for r in INTL_ROUTES if r[0] in {"AKL", "CHC", "WLG", "ZQN", "DUD", "NSN", "NPE", "HLZ", "TRG", "PMR", "NPL", "GIS", "IVC", "ROT"}}

AIRLINE_PREFIX = {
    "Air New Zealand Cargo": "NZ",
    "Qantas Freight": "QF",
    "Singapore Airlines Cargo": "SQ",
    "Cathay Pacific Cargo": "CX",
    "China Southern Cargo": "CZ",
    "Emirates SkyCargo": "EK",
    "Atlas Air": "5Y",
    "Parcelair": "PA",
    "Airwork": "AWK",
    "United Cargo": "UA",
    "Korean Air Cargo": "KE",
    "Fiji Airways": "FJ",
}

EXTRA_DURATIONS = {
    ("AKL", "MEL"): 3.8, ("MEL", "AKL"): 3.6, ("AKL", "BNE"): 3.6, ("BNE", "AKL"): 3.4,
    ("AKL", "CAN"): 11.5, ("CAN", "AKL"): 11.0, ("AKL", "NRT"): 11.0, ("NRT", "AKL"): 10.5,
    ("AKL", "ICN"): 12.5, ("ICN", "AKL"): 11.8, ("AKL", "SFO"): 12.5, ("SFO", "AKL"): 13.0,
    ("AKL", "RAR"): 4.0, ("RAR", "AKL"): 3.9, ("AKL", "APW"): 4.0, ("APW", "AKL"): 3.9,
    ("AKL", "TBU"): 3.0, ("TBU", "AKL"): 2.9, ("CHC", "SYD"): 3.3, ("SYD", "CHC"): 3.1,
    ("CHC", "SIN"): 10.5, ("SIN", "CHC"): 9.8, ("CHC", "MEL"): 3.6, ("MEL", "CHC"): 3.4,
    ("WLG", "SYD"): 3.5, ("SYD", "WLG"): 3.2, ("ZQN", "SYD"): 3.2, ("SYD", "ZQN"): 3.0,
    ("ZQN", "MEL"): 3.5, ("MEL", "ZQN"): 3.3, ("AKL", "ZQN"): 1.9, ("ZQN", "AKL"): 1.8,
    ("CHC", "ZQN"): 1.0, ("ZQN", "CHC"): 1.0, ("WLG", "ZQN"): 1.2, ("ZQN", "WLG"): 1.2,
    ("AKL", "DUD"): 1.9, ("DUD", "AKL"): 1.8, ("CHC", "DUD"): 1.0, ("DUD", "CHC"): 1.0,
    ("AKL", "NSN"): 1.3, ("NSN", "AKL"): 1.3, ("AKL", "HLZ"): 1.0, ("HLZ", "AKL"): 1.0,
    ("AKL", "TRG"): 1.0, ("TRG", "AKL"): 1.0, ("AKL", "PMR"): 1.1, ("PMR", "AKL"): 1.1,
    ("AKL", "NPL"): 1.0, ("NPL", "AKL"): 1.0, ("AKL", "GIS"): 1.1, ("GIS", "AKL"): 1.1,
    ("AKL", "ROT"): 0.9, ("ROT", "AKL"): 0.9, ("AKL", "IVC"): 2.0, ("IVC", "AKL"): 2.0,
    ("CHC", "IVC"): 1.0, ("IVC", "CHC"): 1.0, ("CHC", "HLZ"): 1.2, ("HLZ", "CHC"): 1.2,
}


def sim_flight_duration(org, dst):
    return EXTRA_DURATIONS.get((org, dst)) or _base_flight_duration(org, dst)


# ============================================================
# 货物商品池
# ============================================================
EXPORT_COMMODITIES = [
    ("Dairy - infant formula", "040221", (45000, 95000), ["VIP", "high"], "PER", (2.0, 25.0)),
    ("Chilled lamb cuts", "020422", (55000, 120000), ["VIP", "high"], "PER", (-1.0, 4.0)),
    ("Frozen beef primal cuts", "020220", (40000, 90000), ["high"], "PER", (-18.0, -15.0)),
    ("Live rock lobster", "030632", (30000, 80000), ["VIP"], "PER", (2.0, 8.0)),
    ("Fresh salmon fillets", "030213", (20000, 50000), ["high"], "PER", (0.0, 2.0)),
    ("Frozen mussel products", "030732", (15000, 40000), ["high"], "PER", (-18.0, -15.0)),
    ("Zespri kiwifruit", "081050", (15000, 35000), ["high"], "PER", (0.0, 1.0)),
    ("New season apples", "080810", (10000, 25000), ["medium"], "PER", (0.0, 4.0)),
    ("Manuka honey", "040900", (18000, 60000), ["high", "medium"], None, None),
    ("Marlborough wine", "220421", (8000, 25000), ["medium"], None, None),
    ("Horticulture plant cuttings", "060210", (20000, 50000), ["high"], "PER", (4.0, 15.0)),
    ("Medical diagnostic devices", "901890", (60000, 150000), ["VIP"], "VAL", None),
    ("Pharmaceutical products", "300490", (50000, 140000), ["VIP"], "PHR", (2.0, 8.0)),
    ("Aircraft AOG spare parts", "841191", (30000, 90000), ["high"], None, None),
    ("Wool fibre", "510111", (8000, 20000), ["medium"], None, None),
    ("Deer velvet products", "050790", (25000, 60000), ["high"], None, None),
    ("Sea urchin (kina)", "030791", (12000, 30000), ["medium"], "PER", (0.0, 4.0)),
]

IMPORT_COMMODITIES = [
    ("E-commerce parcels (consolidated)", "990000", (20000, 60000), ["medium", "low"], None, None),
    ("Consumer electronics", "854231", (50000, 120000), ["high"], None, None),
    ("Automotive parts", "870840", (20000, 50000), ["medium"], None, None),
    ("Pharmaceuticals (cold chain)", "300241", (80000, 200000), ["VIP"], "PHR", (2.0, 8.0)),
    ("Packaged food products", "210390", (15000, 40000), ["medium"], "PER", (None, 25.0)),
    ("Industrial adhesives (DGR3)", "350691", (10000, 30000), ["medium"], "DGR", None),
    ("Industrial machinery parts", "848390", (25000, 70000), ["high"], None, None),
    ("Textiles and apparel", "620462", (12000, 30000), ["medium"], None, None),
    ("Medical consumables", "901831", (30000, 80000), ["high"], "VAL", None),
    ("Fresh tropical produce", "071490", (5000, 15000), ["low"], "PER", (5.0, 15.0)),
    ("Lithium battery equipment (DGR9)", "850760", (18000, 45000), ["medium"], "DGR", None),
    ("Courier express parcels", "990000", (8000, 20000), ["low"], None, None),
]

DOMESTIC_COMMODITIES = [
    ("General freight (mixed pallets)", "990000", (10000, 30000), ["medium"], None, None),
    ("Chilled dairy products", "040310", (6000, 20000), ["medium"], "PER", (0.0, 4.0)),
    ("Legal documents and contracts", "490199", (5000, 15000), ["high"], None, None),
    ("Fresh salmon fillets", "030213", (15000, 35000), ["high"], "PER", (0.0, 2.0)),
    ("Medical supplies and equipment", "901831", (25000, 60000), ["high"], "VAL", None),
    ("Beverage distribution stock", "220210", (8000, 20000), ["medium"], None, None),
    ("Courier parcels", "990000", (5000, 15000), ["low"], None, None),
    ("Machine spare parts (urgent)", "848390", (20000, 50000), ["VIP"], None, None),
    ("Construction materials", "730890", (8000, 20000), ["medium"], None, None),
    ("Retail store stock", "990000", (10000, 25000), ["medium"], None, None),
    ("Newspapers and magazines", "490290", (2000, 8000), ["low"], None, None),
    ("Seafood (Pacific oysters)", "030711", (12000, 30000), ["medium"], "PER", (0.0, 4.0)),
]

CUSTOMERS = [
    ("Fonterra", "VIP"), ("Silver Fern Farms", "VIP"), ("Zespri International", "high"),
    ("Fisher & Paykel Healthcare", "VIP"), ("Fisher & Paykel Appliances", "high"),
    ("Sanford Limited", "high"), ("Sealord Group", "high"), ("Mount Cook Alpine Salmon", "high"),
    ("Manuka Health", "high"), ("Cloudy Bay Vineyards", "medium"), ("Wools of New Zealand", "medium"),
    ("Mainfreight", "medium"), ("Foodstuffs NZ", "medium"), ("Countdown Supermarkets", "high"),
    ("NZ Post", "low"), ("Toyota NZ", "medium"), ("Fletcher Building", "medium"),
    ("Goodman Fielder", "medium"), ("Coca-Cola Amatil NZ", "medium"), ("Pharmac NZ", "VIP"),
    ("Kmart NZ", "low"), ("The Warehouse Group", "low"), ("Briscoe Group", "medium"),
    ("PlaceMakers", "medium"), ("Steel & Tube", "medium"), ("Gallagher Group", "high"),
    ("Rocket Lab", "high"), ("Air New Zealand Engineering", "high"), ("Russell McVeagh", "high"),
    ("Southern DHB", "high"), ("Pacific Produce Imports", "low"), ("Pacific Fresh Foods", "medium"),
    ("Plant & Food Research", "high"), ("Comvita", "medium"),
]

DELAY_REASONS = [
    ("weather", 0.35), ("congestion", 0.25), ("technical", 0.15), ("crew", 0.10),
    ("volcanic_ash", 0.05), ("security", 0.05), ("air_traffic", 0.05),
]


class AirCargoSimulator:
    """Live air cargo operations simulator running as a background thread."""

    def __init__(self, speed=None):
        self.sim_now = datetime.utcnow().replace(microsecond=0)
        self.speed = speed if speed is not None else settings.air_sim_speed
        self.paused = False
        self.running = False
        self.started_at = None
        self._stop_event = threading.Event()
        self._thread = None
        self._last_real = time.monotonic()
        self._route_next_dep = {}
        self._pending = []
        self._pending_seq = 0
        self._last_cleanup_sim = self.sim_now
        self.flights_generated = 0
        self.waybills_generated = 0
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
                generate_airports(db)
                self._init_route_schedule()
                self._rebuild_pending_from_db()
                if backfill:
                    self._backfill()
            finally:
                db.close()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="air-cargo-sim")
        self._thread.start()
        print(f"[air-sim] started speed={self.speed}x sim_now={self.sim_now.isoformat()}")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[air-sim] stopped")

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
                    print(f"[air-sim] tick error: {e}")
            time.sleep(max(0.1, settings.air_sim_tick_seconds - (time.monotonic() - t0)))

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------
    def _init_counters(self):
        """Resume ID counters from existing DB data so restarts don't collide."""
        db = SessionLocal()
        try:
            self._used_flight_numbers = {f[0] for f in db.query(AirFlight.flight_number).all()}

            awb_row = db.query(AirWaybill.awb_number).order_by(AirWaybill.awb_number.desc()).first()
            self._awb_counter = (int(awb_row[0].split("-")[1]) + 1) if awb_row else 81000001

            evt_row = db.query(AirTrackingEvent.event_id).filter(
                AirTrackingEvent.event_id.like("EVT-SIM-%")
            ).order_by(AirTrackingEvent.event_id.desc()).first()
            self._event_counter = (int(evt_row[0].split("-")[2]) + 1) if evt_row else 1

            exc_row = db.query(AirException.exception_id).filter(
                AirException.exception_id.like("EXC-SIM-%")
            ).order_by(AirException.exception_id.desc()).first()
            self._exc_counter = (int(exc_row[0].split("-")[2]) + 1) if exc_row else 1

            insp_row = db.query(AirCustomsInspection.inspection_id).filter(
                AirCustomsInspection.inspection_id.like("INS-SIM-%")
            ).order_by(AirCustomsInspection.inspection_id.desc()).first()
            self._insp_counter = (int(insp_row[0].split("-")[2]) + 1) if insp_row else 1
        finally:
            db.close()

    def _init_route_schedule(self):
        routes = DOMESTIC_ROUTES + INTL_ROUTES
        for org, dst, freq, airline, ac, freight in routes:
            key = (org, dst, airline)
            interval = 1440.0 / freq
            first = self.sim_now - timedelta(hours=6)
            self._route_next_dep[key] = first + timedelta(minutes=random.uniform(0, interval))

    def _backfill(self):
        """Create flights for [sim_now - 6h, sim_now + 12h) so the dashboard has data immediately."""
        for key in list(self._route_next_dep.keys()):
            org, dst, airline = key
            freq = next(r[2] for r in DOMESTIC_ROUTES + INTL_ROUTES
                        if r[0] == org and r[1] == dst and r[3] == airline)
            interval = 1440.0 / freq
            while self._route_next_dep[key] < self.sim_now + timedelta(hours=12):
                if not self._flight_conflicts(org, dst, airline, self._route_next_dep[key]):
                    self._create_flight(org, dst, airline, dep=self._route_next_dep[key])
                self._route_next_dep[key] += timedelta(minutes=interval * random.uniform(0.8, 1.2))

    def _rebuild_pending_from_db(self):
        """Rebuild the in-memory pending event heap after a process restart.

        Waybills resume their Cargo IMP milestone chain from the last event
        already recorded, so tracking timelines continue seamlessly.
        """
        db = SessionLocal()
        try:
            flights = db.query(AirFlight).filter(AirFlight.status != "cancelled").all()
            for flight in flights:
                eff_dep = flight.scheduled_departure + timedelta(minutes=flight.delay_minutes or 0)
                eff_arr = flight.scheduled_arrival + timedelta(minutes=flight.delay_minutes or 0)
                waybills = db.query(AirWaybill).filter(
                    AirWaybill.flight_number == flight.flight_number).all()
                if not waybills:
                    continue
                awbs = [w.awb_number for w in waybills]
                if flight.status != "landed":
                    self._push(eff_dep, "flight_dep", flight.flight_number)
                    self._push(eff_arr, "flight_arr", flight.flight_number)
                    if flight.delay_minutes and not db.query(AirException).filter(
                            AirException.awb_number.in_(awbs),
                            AirException.exception_type.in_(["delay", "offload"])
                    ).first():
                        self._push(flight.scheduled_departure - timedelta(minutes=30),
                                   "delay_announce", flight.flight_number)
                for w in waybills:
                    hold = db.query(AirCustomsInspection).filter(
                        AirCustomsInspection.awb_number == w.awb_number,
                        AirCustomsInspection.status == "hold"
                    ).first()
                    latest_row = db.query(AirTrackingEvent.event_code).filter(
                        AirTrackingEvent.awb_number == w.awb_number
                    ).order_by(AirTrackingEvent.timestamp.desc(), AirTrackingEvent.id.desc()).first()
                    latest = latest_row[0] if latest_row else None
                    chain = self._event_chain(flight, w, hold)
                    codes = [c for _, c, _, _ in chain]
                    if latest and latest in codes:
                        start = codes.index(latest) + 1
                    elif latest == "DLY":
                        start = codes.index("DEP") if "DEP" in codes else 0
                    else:
                        start = 0
                    for ts, code, desc, loc in chain[start:]:
                        self._push(ts, "event", (w.awb_number, code, desc, loc, None, None, ts))
            for insp in db.query(AirCustomsInspection).filter(
                    AirCustomsInspection.status == "hold").all():
                self._push(insp.initiated_at + timedelta(hours=6),
                           "inspection_release", insp.inspection_id)
        finally:
            db.close()

    def _event_chain(self, flight, waybill, hold_inspection=None):
        """Ordered Cargo IMP milestone chain for a waybill."""
        dep = flight.scheduled_departure
        arr = flight.scheduled_arrival
        eff_dep = dep + timedelta(minutes=flight.delay_minutes or 0)
        eff_arr = arr + timedelta(minutes=flight.delay_minutes or 0)
        is_domestic = waybill.route_type == "domestic"
        chain = [
            (dep - timedelta(hours=9), "FNA", "Air waybill created", waybill.origin_airport),
            (dep - timedelta(hours=8), "BKD", "Booking confirmed", waybill.origin_airport),
            (dep - timedelta(hours=3), "RCS", "Cargo received at terminal", waybill.origin_airport),
            (eff_dep, "DEP", "Flight departed", waybill.origin_airport),
            (eff_arr, "ARR", "Flight arrived", waybill.destination_airport),
        ]
        if not is_domestic:
            chain.append((eff_arr + timedelta(minutes=20), "MNF",
                          "Manifest submitted to customs", waybill.destination_airport))
            if hold_inspection:
                release_at = hold_inspection.initiated_at + timedelta(hours=6)
                chain.append((eff_arr + timedelta(minutes=40), "CDZ",
                              "Customs hold placed", waybill.destination_airport))
                chain.append((release_at + timedelta(hours=1), "CCD",
                              "Customs cleared", waybill.destination_airport))
                chain.append((release_at + timedelta(hours=1, minutes=30), "NFD",
                              "Notify for delivery", waybill.destination_airport))
            else:
                chain.append((eff_arr + timedelta(hours=2), "CCD",
                              "Customs cleared", waybill.destination_airport))
                chain.append((eff_arr + timedelta(hours=3), "NFD",
                              "Notify for delivery", waybill.destination_airport))
        chain.append((eff_arr + timedelta(hours=3 if is_domestic else 6), "DLV",
                      "Delivered to consignee", waybill.destination_airport))
        return chain

    # ----------------------------------------------------------
    # 主 tick
    # ----------------------------------------------------------
    def tick(self):
        with WRITE_LOCK:
            db = SessionLocal()
            try:
                self._spawn_due_flights()
                self._process_pending(db)
                self._derive_flight_statuses(db)
                if (self.sim_now - self._last_cleanup_sim) > timedelta(hours=1):
                    self._cleanup(db)
                    self._last_cleanup_sim = self.sim_now
            finally:
                db.close()

    def _spawn_due_flights(self):
        routes = DOMESTIC_ROUTES + INTL_ROUTES
        for org, dst, freq, airline, ac, freight in routes:
            key = (org, dst, airline)
            interval = 1440.0 / freq
            while self._route_next_dep[key] < self.sim_now + timedelta(hours=12):
                if not self._flight_conflicts(org, dst, airline, self._route_next_dep[key]):
                    self._create_flight(org, dst, airline, dep=self._route_next_dep[key])
                self._route_next_dep[key] += timedelta(minutes=interval * random.uniform(0.8, 1.2))

    def _flight_conflicts(self, org, dst, airline, dep):
        """Skip spawning if a flight on the same route already exists within 20 minutes."""
        db = SessionLocal()
        try:
            conflict = db.query(AirFlight).filter(
                AirFlight.origin_airport == org,
                AirFlight.destination_airport == dst,
                AirFlight.airline == airline,
                AirFlight.scheduled_departure >= dep - timedelta(minutes=20),
                AirFlight.scheduled_departure <= dep + timedelta(minutes=20),
            ).first()
            return conflict is not None
        finally:
            db.close()

    # ----------------------------------------------------------
    # 航班与运单生成
    # ----------------------------------------------------------
    def _create_flight(self, org, dst, airline, dep=None):
        route = next((r for r in DOMESTIC_ROUTES + INTL_ROUTES
                      if r[0] == org and r[1] == dst and r[3] == airline), None)
        if route is None:
            return None
        aircraft = route[4]
        freighter = route[5]
        dep = dep or self._route_next_dep.get((org, dst, airline), self.sim_now)
        dur = sim_flight_duration(org, dst)
        arr = dep + timedelta(hours=dur)

        is_domestic = org in {"AKL", "CHC", "WLG", "ZQN", "DUD", "NSN", "NPE", "HLZ", "TRG", "PMR", "NPL", "GIS", "IVC", "ROT"} and \
            dst in {"AKL", "CHC", "WLG", "ZQN", "DUD", "NSN", "NPE", "HLZ", "TRG", "PMR", "NPL", "GIS", "IVC", "ROT"}

        cancelled = is_domestic and random.random() < 0.015
        delay_minutes = 0
        delay_reason = None
        if not cancelled and random.random() < 0.10:
            delay_minutes = int(random.choice([15, 20, 25, 30, 35, 40, 45, 55, 60, 75, 90, 120, 150, 180, 240]))
            delay_reason = random.choices([r[0] for r in DELAY_REASONS],
                                          weights=[r[1] for r in DELAY_REASONS])[0]

        capacity = self._aircraft_capacity(aircraft)
        flight_number = self._unique_flight_number(airline)

        db = SessionLocal()
        try:
            flight = AirFlight(
                flight_number=flight_number, airline=airline, aircraft_type=aircraft,
                is_freighter=freighter, origin_airport=org, destination_airport=dst,
                scheduled_departure=dep, scheduled_arrival=arr,
                delay_minutes=delay_minutes, delay_reason_code=delay_reason,
                status="cancelled" if cancelled else "scheduled",
                capacity_kg=capacity,
                loaded_kg=int(capacity * random.uniform(0.55, 0.95)),
                flight_date=dep,
            )
            flight.loaded_pct = round(flight.loaded_kg / capacity * 100, 1)
            db.add(flight)
            db.flush()
            self.flights_generated += 1

            if not cancelled:
                n_waybills = random.choices([2, 3, 4, 5, 6], weights=[0.15, 0.3, 0.3, 0.15, 0.1])[0]
                for _ in range(n_waybills):
                    self._create_waybill(db, flight, dep, arr, delay_minutes, is_domestic)
                eff_dep = dep + timedelta(minutes=delay_minutes)
                eff_arr = arr + timedelta(minutes=delay_minutes)
                if delay_minutes > 0:
                    self._push(dep - timedelta(minutes=30), "delay_announce", flight_number)
                self._push(eff_dep, "flight_dep", flight_number)
                self._push(eff_arr, "flight_arr", flight_number)
            db.commit()
            db.refresh(flight)
            db.expunge(flight)
            return flight
        finally:
            db.close()

    def _aircraft_capacity(self, aircraft):
        caps = {"ATR72-600": 1200, "A320neo": 4500, "A321neo": 5000, "B737-800": 5000,
                "B737-400F": 18000, "A330-200": 11000, "A330-300": 11000, "A350-900": 13000,
                "A350-1000": 14000, "B787-9": 15000, "B777-300ER": 16000, "A380-800": 16000,
                "B747-8F": 115000}
        return caps.get(aircraft, 8000)

    def _unique_flight_number(self, airline):
        prefix = AIRLINE_PREFIX.get(airline, "XX")
        for _ in range(100):
            num = random.randint(1000, 9999)
            candidate = f"{prefix}{num}"
            if candidate not in self._used_flight_numbers:
                self._used_flight_numbers.add(candidate)
                return candidate
        return f"{prefix}{random.randint(10000, 99999)}"

    def _create_waybill(self, db, flight, dep, arr, delay_minutes, is_domestic):
        org = flight.origin_airport
        dst = flight.destination_airport
        if is_domestic:
            pool = DOMESTIC_COMMODITIES
            route_type = "domestic"
        else:
            exporting = org in {"AKL", "CHC", "WLG", "ZQN"}
            pool = EXPORT_COMMODITIES if exporting else IMPORT_COMMODITIES
            route_type = "international"

        desc, hs, value_range, tiers, shc, temp = random.choice(pool)
        value = random.randint(*value_range)
        pieces = random.randint(2, 25)
        weight = round(pieces * random.uniform(40, 120), 1)
        volume = round(weight / 160.0, 2)
        chargeable = max(weight, round(volume * 167, 1))

        customer, tier = random.choice(CUSTOMERS)
        if random.random() < 0.1:
            tier = "VIP"
        elif tier == "VIP" and random.random() < 0.7:
            tier = "high"

        service = "express" if (random.random() < 0.2) else "standard"
        priority = "normal"
        if "urgent" in desc or "AOG" in desc or random.random() < 0.08:
            priority = "critical"
        elif tier in ("VIP", "high") and random.random() < 0.3:
            priority = "high"
        if priority == "critical":
            service = "express"

        sla_h = {"domestic": random.choice([10, 24]), "international": random.choice([36, 48, 60, 72])}[route_type]
        if service == "express":
            sla_h = max(8, sla_h // 2)

        temp_min, temp_max = None, None
        if temp:
            temp_min, temp_max = temp

        awb_number = f"086-{self._awb_counter:08d}"
        self._awb_counter += 1
        hawb = None
        if "consolidated" in desc and random.random() < 0.7:
            hawb = f"086-{self._awb_counter:08d}"
            self._awb_counter += 1

        delivery_buffer = 3.0 if is_domestic else 6.0
        eff_arr = arr + timedelta(minutes=delay_minutes)
        waybill = AirWaybill(
            awb_number=awb_number, hawb_number=hawb, route_type=route_type,
            origin_airport=org, destination_airport=dst,
            transit_points=json.dumps([]),
            flight_number=flight.flight_number,
            pieces=pieces, gross_weight_kg=weight, volume_cbm=volume,
            chargeable_weight_kg=chargeable,
            commodity_code=hs, commodity_desc=desc,
            shipper_name=customer, consignee_name=f"{customer} DC",
            customer_name=customer, customer_tier=tier,
            declared_value_nzd=float(value), service_level=service,
            priority=priority,
            sla_tier={"VIP": "gold", "high": "gold", "medium": "silver", "low": "bronze"}[tier],
            special_handling_codes=shc,
            dg_class="3" if "DGR3" in desc else ("9" if "DGR9" in desc else None),
            un_number="UN1133" if "DGR3" in desc else ("UN3480" if "DGR9" in desc else None),
            temp_required_c=temp_min if (shc == "PER" and temp_min is not None) else None,
            temp_min_c=temp_min, temp_max_c=temp_max,
            expiry_date=(dep + timedelta(hours=random.choice([30, 48, 72]))) if shc == "PER" else None,
            current_status="booked", current_location=org,
            scheduled_delivery=eff_arr + timedelta(hours=delivery_buffer),
            estimated_delivery=eff_arr + timedelta(hours=delivery_buffer),
            sla_deadline=dep + timedelta(hours=sla_h),
        )
        db.add(waybill)
        db.flush()
        self.waybills_generated += 1

        self._schedule_waybill_events(waybill, flight, dep, arr, delay_minutes, is_domestic)

    def _schedule_waybill_events(self, waybill, flight, dep, arr, delay_minutes, is_domestic):
        """Schedule waybill-specific milestone events (flight-level events are scheduled once per flight)."""
        eff_arr = arr + timedelta(minutes=delay_minutes)
        awb = waybill.awb_number
        org, dst = flight.origin_airport, flight.destination_airport

        self._push(dep - timedelta(hours=9), "event", (awb, "FNA", "Air waybill created", org, None, None, dep - timedelta(hours=9)))
        self._push(dep - timedelta(hours=8), "event", (awb, "BKD", "Booking confirmed", org, None, None, dep - timedelta(hours=8)))
        self._push(dep - timedelta(hours=3), "event", (awb, "RCS", "Cargo received at terminal", org, None, None, dep - timedelta(hours=3)))

        if not is_domestic:
            self._push(eff_arr + timedelta(minutes=20), "event",
                       (awb, "MNF", "Manifest submitted to customs", dst, None, None, eff_arr + timedelta(minutes=20)))
            self._push(eff_arr + timedelta(hours=2), "customs_clear",
                       (awb, eff_arr + timedelta(hours=2), eff_arr + timedelta(hours=3)))
            if random.random() < 0.05 and self._is_food_cargo(waybill):
                self._push(eff_arr + timedelta(minutes=20), "customs_hold", awb)
            if waybill.temp_min_c is not None and random.random() < 0.012:
                self._push(eff_arr, "temp_alert", awb)
        self._push(eff_arr + timedelta(hours=3 if is_domestic else 6), "dlv", awb)

    def _is_food_cargo(self, waybill):
        hs = waybill.commodity_code or ""
        return hs.startswith(("02", "03", "04", "05", "07", "08", "16", "20", "21"))

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
                print(f"[air-sim] unknown pending kind: {kind}")
            except Exception as e:
                print(f"[air-sim] pending handler error ({kind}): {e}")

    # ----------------------------------------------------------
    # 事件处理器
    # ----------------------------------------------------------
    def _on_event(self, db, payload):
        awb, code, desc, loc, reason, message, ts = payload
        self._insert_event(db, awb, code, desc, loc, reason, message, ts=ts)

    def _insert_event(self, db, awb, code, desc, loc, reason=None, message=None, ts=None):
        event = AirTrackingEvent(
            event_id=f"EVT-SIM-{self._event_counter:09d}",
            awb_number=awb, event_code=code, event_desc=desc,
            location=loc, timestamp=ts or self.sim_now, source="carrier_api",
            reason_code=reason,
            message=message or f"Carrier status update: {code} {loc}"
        )
        self._event_counter += 1
        self.events_generated += 1
        db.add(event)

    def _on_flight_dep(self, db, flight_number):
        flight = db.query(AirFlight).filter(AirFlight.flight_number == flight_number).first()
        if not flight or flight.status == "cancelled":
            return
        flight.status = "departed"
        eff_dep = flight.scheduled_departure + timedelta(minutes=flight.delay_minutes or 0)
        flight.actual_departure = eff_dep
        db.flush()
        for w in db.query(AirWaybill).filter(AirWaybill.flight_number == flight_number).all():
            dup = db.query(AirTrackingEvent).filter(
                AirTrackingEvent.awb_number == w.awb_number,
                AirTrackingEvent.event_code == "DEP"
            ).first()
            if dup:
                continue
            if w.current_status in ("booked", "RCS"):
                w.current_status = "DEP"
                w.current_location = flight.destination_airport
            self._insert_event(db, w.awb_number, "DEP", "Flight departed",
                               flight.origin_airport, ts=eff_dep)

    def _on_flight_arr(self, db, flight_number):
        flight = db.query(AirFlight).filter(AirFlight.flight_number == flight_number).first()
        if not flight or flight.status == "cancelled":
            return
        flight.status = "landed"
        eff_arr = flight.scheduled_arrival + timedelta(minutes=flight.delay_minutes or 0)
        flight.actual_arrival = eff_arr
        db.flush()
        if flight.actual_departure:
            dwell = (flight.actual_arrival - flight.actual_departure).total_seconds() / 3600
            anomaly = detector.observe("air", "DEP_ARR", dwell)
            if anomaly:
                for w in db.query(AirWaybill).filter(AirWaybill.flight_number == flight_number).all():
                    self._create_predicted_exception(db, w, anomaly, "DEP->ARR")
                    break
        for w in db.query(AirWaybill).filter(AirWaybill.flight_number == flight_number).all():
            dup = db.query(AirTrackingEvent).filter(
                AirTrackingEvent.awb_number == w.awb_number,
                AirTrackingEvent.event_code == "ARR"
            ).first()
            if dup:
                continue
            w.current_status = "ARR"
            w.current_location = flight.destination_airport
            self._insert_event(db, w.awb_number, "ARR", "Flight arrived",
                               flight.destination_airport, ts=eff_arr)
            if w.route_type == "international" and random.random() < 0.004:
                self._create_exception(db, w, "misroute",
                                       f"Cargo offloaded at incorrect destination during {flight.flight_number} arrival",
                                       delay_hours=12.0,
                                       diagnosis="Manifest discrepancy detected at destination. Cargo scanned at wrong ULD position.",
                                       recovery=["rebook_next_flight", "express_courier"])

    def _on_delay_announce(self, db, flight_number):
        flight = db.query(AirFlight).filter(AirFlight.flight_number == flight_number).first()
        if not flight or flight.status == "cancelled" or not flight.delay_minutes:
            return
        waybills = db.query(AirWaybill).filter(AirWaybill.flight_number == flight_number).all()
        for w in waybills:
            dup = db.query(AirException).filter(
                AirException.awb_number == w.awb_number,
                AirException.exception_type.in_(["delay", "offload"]),
                AirException.status != "resolved"
            ).count()
            if dup:
                continue
            delay_hours = flight.delay_minutes / 60.0
            self._create_exception(
                db, w, "delay",
                f"Flight {flight.flight_number} delayed {flight.delay_minutes} minutes ({flight.delay_reason_code})",
                delay_hours=delay_hours,
                diagnosis=(f"{flight.delay_reason_code or 'operational'} delay on {flight.flight_number} "
                           f"{flight.origin_airport}-{flight.destination_airport}. "
                           f"Revised departure {delay_hours:.1f}h later than scheduled."),
                recovery=["wait", "rebook_next_flight", "upgrade_priority"]
            )
            self._insert_event(db, w.awb_number, "DLY", "Delay advisory received",
                               flight.origin_airport, reason=flight.delay_reason_code,
                               ts=flight.scheduled_departure - timedelta(minutes=30))

    def _on_customs_hold(self, db, awb):
        w = db.query(AirWaybill).filter(AirWaybill.awb_number == awb).first()
        if not w:
            return
        inspection = AirCustomsInspection(
            inspection_id=f"INS-SIM-{self._insp_counter:06d}",
            awb_number=awb,
            inspection_type=random.choice(["mpi_biosecurity", "mpi_physical", "customs_xray"]),
            agency="MPI" if random.random() > 0.3 else "NZ_Customs",
            status="hold",
            initiated_at=self.sim_now,
        )
        self._insp_counter += 1
        db.add(inspection)
        self._create_exception(
            db, w, "customs_hold",
            "NZ Customs inspection hold at arrival",
            delay_hours=random.uniform(4, 8),
            diagnosis="Customs selected consignment for inspection. Historical pattern: 92% of similar holds release without finding.",
            recovery=["wait", "upgrade_priority"]
        )
        self._insert_event(db, awb, "CDZ", "Customs hold placed", w.destination_airport, reason="mpi_hold")
        release_at = self.sim_now + timedelta(hours=random.uniform(4, 8))
        self._push(release_at, "inspection_release", inspection.inspection_id)
        self._push(release_at + timedelta(hours=1), "event",
                   (awb, "CCD", "Customs cleared", w.destination_airport, None, None, release_at + timedelta(hours=1)))
        self._push(release_at + timedelta(hours=1, minutes=30), "event",
                   (awb, "NFD", "Notify for delivery", w.destination_airport, None, None, release_at + timedelta(hours=1, minutes=30)))

    def _on_customs_clear(self, db, payload):
        awb, ts_ccd, ts_nfd = payload
        hold = db.query(AirCustomsInspection).filter(
            AirCustomsInspection.awb_number == awb,
            AirCustomsInspection.status == "hold"
        ).first()
        if hold:
            return
        w = db.query(AirWaybill).filter(AirWaybill.awb_number == awb).first()
        if not w:
            return
        self._insert_event(db, awb, "CCD", "Customs cleared", w.destination_airport, ts=ts_ccd)
        self._push(ts_nfd, "event",
                   (awb, "NFD", "Notify for delivery", w.destination_airport, None, None, ts_nfd))

    def _on_inspection_release(self, db, inspection_id):
        inspection = db.query(AirCustomsInspection).filter(
            AirCustomsInspection.inspection_id == inspection_id).first()
        if inspection:
            inspection.status = "released"
            inspection.released_at = self.sim_now
            inspection.finding = "No biosecurity risk material found"

    def _on_temp_alert(self, db, awb):
        w = db.query(AirWaybill).filter(AirWaybill.awb_number == awb).first()
        if not w:
            return
        w.temp_excursion_alert = True
        self._create_exception(
            db, w, "temp_excursion",
            f"Temperature excursion outside {w.temp_min_c}-{w.temp_max_c}C range during transit",
            delay_hours=0.0,
            diagnosis=("Temperature logger deviation detected. Shipper stability data "
                       "supports short excursion. Recommend expedited release and customer notification."),
            recovery=["wait", "upgrade_priority", "rebook_next_flight"]
        )
        self._insert_event(db, awb, "DLY", "Temperature excursion alert",
                           w.destination_airport, reason="temp_excursion")

    def _on_dlv(self, db, awb):
        w = db.query(AirWaybill).filter(AirWaybill.awb_number == awb).first()
        if not w:
            return
        db.flush()
        dup = db.query(AirTrackingEvent).filter(
            AirTrackingEvent.awb_number == awb,
            AirTrackingEvent.event_code == "DLV"
        ).first()
        if dup:
            return
        w.current_status = "DLV"
        w.current_location = w.destination_airport
        w.delivered_at = self.sim_now
        self._insert_event(db, awb, "DLV", "Delivered to consignee", w.destination_airport)

    def _create_exception(self, db, waybill, exc_type, root_cause, delay_hours, diagnosis, recovery):
        eff_delivery = waybill.estimated_delivery or (self.sim_now + timedelta(hours=delay_hours))
        sla_breach = (eff_delivery - waybill.sla_deadline).total_seconds() / 3600
        score = calculate_risk_score(
            cargo_value=waybill.declared_value_nzd,
            customer_tier=waybill.customer_tier,
            sla_breach_hours=sla_breach,
            exception_type="customs_hold" if exc_type == "customs_hold" else exc_type
        )
        risk_level = categorize_risk(score)
        severity = calculate_severity(score, sla_breach, exc_type)
        cls = classifier.classify_and_learn(root_cause or diagnosis or "", exc_type)
        exc = AirException(
            exception_id=f"EXC-SIM-{self._exc_counter:06d}",
            awb_number=waybill.awb_number,
            exception_type=exc_type,
            severity=severity,
            risk_level=risk_level,
            risk_score=score,
            detected_at=self.sim_now,
            root_cause=root_cause,
            ai_diagnosis=diagnosis,
            ai_confidence=round(random.uniform(0.85, 0.98), 2),
            status="escalated" if cls["is_ood"] else ("diagnosed" if risk_level == "low" else "pending_approval"),
            requires_human_approval=cls["is_ood"] or risk_level != "low",
            recovery_options=json.dumps(recovery),
            delay_hours=delay_hours,
            business_section=cls["business_section"],
            classification_confidence=cls["classification_confidence"],
            classification_decision=cls["classification_decision"],
            ood_score=cls["ood_score"],
            is_ood=cls["is_ood"],
        )
        self._exc_counter += 1
        self.exceptions_generated += 1
        db.add(exc)
        db.flush()

    def _create_predicted_exception(self, db, waybill, anomaly, transition):
        """Create a predictive anomaly exception from a dwell-time outlier."""
        exc = AirException(
            exception_id=f"EXC-SIM-{self._exc_counter:06d}",
            awb_number=waybill.awb_number,
            exception_type="predicted_anomaly",
            severity="medium",
            risk_level="medium",
            risk_score=50,
            detected_at=self.sim_now,
            root_cause=f"{transition} dwell time abnormal for {waybill.awb_number}",
            ai_diagnosis=f"Dwell time {transition} exceeds recent P95 by {anomaly['anomaly_score']}x. Potential air traffic or congestion delay.",
            ai_confidence=round(random.uniform(0.7, 0.85), 2),
            status="detected",
            requires_human_approval=True,
            recovery_options=json.dumps(["monitor", "upgrade_priority"]),
            delay_hours=0.0,
            business_section="Time & Service Disruption",
            classification_decision="human_review",
            ood_score=0.0,
            is_ood=False,
            anomaly_score=anomaly["anomaly_score"],
            anomaly_reason=anomaly["anomaly_reason"],
        )
        self._exc_counter += 1
        self.exceptions_generated += 1
        db.add(exc)
        db.flush()

    # ----------------------------------------------------------
    # 状态推导
    # ----------------------------------------------------------
    def _derive_flight_statuses(self, db):
        active = db.query(AirFlight).filter(
            AirFlight.status.in_(["scheduled", "boarding", "delayed", "departed"])
        ).all()
        for flight in active:
            eff_dep = flight.scheduled_departure + timedelta(minutes=flight.delay_minutes or 0)
            eff_arr = flight.scheduled_arrival + timedelta(minutes=flight.delay_minutes or 0)
            if self.sim_now < flight.scheduled_departure - timedelta(minutes=40):
                new_status = "scheduled"
            elif self.sim_now < eff_dep:
                new_status = "boarding" if not flight.delay_minutes else "delayed"
            elif self.sim_now < eff_arr:
                new_status = "departed"
            else:
                new_status = "landed"
                flight.actual_arrival = eff_arr
            if new_status != flight.status:
                flight.status = new_status

    # ----------------------------------------------------------
    # 数据保留清理
    # ----------------------------------------------------------
    def _cleanup(self, db):
        cutoff = self.sim_now - timedelta(hours=settings.air_sim_retention_hours)
        old_waybills = db.query(AirWaybill).filter(
            AirWaybill.delivered_at.isnot(None),
            AirWaybill.delivered_at < cutoff
        ).all()
        if old_waybills:
            awbs = [w.awb_number for w in old_waybills]
            db.query(AirException).filter(AirException.awb_number.in_(awbs)).delete(synchronize_session=False)
            db.query(AirCustomsInspection).filter(AirCustomsInspection.awb_number.in_(awbs)).delete(synchronize_session=False)
            db.query(AirTrackingEvent).filter(AirTrackingEvent.awb_number.in_(awbs)).delete(synchronize_session=False)
            for w in old_waybills:
                db.delete(w)
        old_flights = db.query(AirFlight).filter(
            AirFlight.status.in_(["landed", "cancelled"]),
            AirFlight.scheduled_arrival < cutoff - timedelta(hours=24)
        ).all()
        for f in old_flights:
            db.delete(f)
        db.commit()


# 全局单例
simulator = AirCargoSimulator()

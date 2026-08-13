"""
Road freight seed data for NZ domestic road freight simulation.
陆运货物模拟数据生成器 - 新西兰国内公路货运

Generates a realistic snapshot of Southern Freight road operations:
- Depots: North/South Island distribution centres + hubs
- Trips: line-haul, regional and inter-island (Cook Strait ferry) trucking
- Consignments: dairy, meat, seafood, produce, retail, construction, pharma
- Tracking events: proof-of-delivery milestone chains
- Exceptions: delay, road closure, breakdown, ferry cancellation, temp excursion

Usage:
    python road_freight_seed.py          # seed default dataset
    python road_freight_seed.py --clear  # clear road freight tables only
"""
import json
import random
import sys
from datetime import datetime, timedelta, timezone

from database import engine, Base, SessionLocal
from road_freight_models import (
    Depot, RoadTrip, RoadConsignment, RoadTrackingEvent, RoadException
)
from risk_calculator import calculate_risk_score, categorize_risk, calculate_severity
from event_classifier import classifier

random.seed(42)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# 分拨中心数据 - NZ depots (North + South Island)
# ============================================================
NZ_DEPOTS = [
    # (code, name, city, region, island, is_hub, congestion)
    ("AKL", "Auckland Metro Depot", "Auckland", "Auckland", "north", True, 5),
    ("HLZ", "Hamilton Depot", "Hamilton", "Waikato", "north", True, 3),
    ("TRG", "Tauranga Port Depot", "Tauranga", "Bay of Plenty", "north", True, 4),
    ("ROT", "Rotorua Depot", "Rotorua", "Bay of Plenty", "north", False, 2),
    ("GIS", "Gisborne Depot", "Gisborne", "Gisborne", "north", False, 1),
    ("NPE", "Napier-Hastings Depot", "Napier", "Hawke's Bay", "north", False, 2),
    ("NPL", "New Plymouth Depot", "New Plymouth", "Taranaki", "north", False, 1),
    ("PMR", "Palmerston North Depot", "Palmerston North", "Manawatu", "north", False, 2),
    ("WLG", "Wellington Metro Depot", "Wellington", "Wellington", "north", True, 4),
    ("WHA", "Whangarei Depot", "Whangarei", "Northland", "north", False, 1),
    ("TAI", "Taupo Depot", "Taupo", "Waikato", "north", False, 1),
    ("PIC", "Picton Ferry Terminal", "Picton", "Marlborough", "south", False, 3),
    ("NSN", "Nelson Depot", "Nelson", "Nelson-Tasman", "south", False, 2),
    ("BLH", "Blenheim Depot", "Blenheim", "Marlborough", "south", False, 1),
    ("GBM", "Greymouth Depot", "Greymouth", "West Coast", "south", False, 1),
    ("CHC", "Christchurch Metro Depot", "Christchurch", "Canterbury", "south", True, 4),
    ("TIM", "Timaru Depot", "Timaru", "Canterbury", "south", False, 1),
    ("OAM", "Oamaru Depot", "Oamaru", "Otago", "south", False, 1),
    ("DUD", "Dunedin Depot", "Dunedin", "Otago", "south", False, 2),
    ("ZQN", "Queenstown Depot", "Queenstown", "Otago", "south", False, 2),
    ("IVC", "Invercargill Depot", "Invercargill", "Southland", "south", False, 1),
]

WEATHER_POOL = [
    "Clear, 12C, light NW wind",
    "Overcast, 9C, moderate S wind",
    "Rain showers, 8C, strong SW wind",
    "Fog patches, 5C, calm",
    "Fine, 15C, light breeze",
    "Gusty northerlies, 11C",
    "Snow showers nearby, 2C",
    "Icy roads, 1C, frost warning",
]

# ============================================================
# 公路距离 (km) - key corridor distances
# ============================================================
ROAD_DISTANCES = {
    ("AKL", "HLZ"): 125, ("HLZ", "AKL"): 125,
    ("AKL", "TRG"): 205, ("TRG", "AKL"): 205,
    ("HLZ", "TRG"): 110, ("TRG", "HLZ"): 110,
    ("AKL", "WLG"): 645, ("WLG", "AKL"): 645,
    ("AKL", "NPE"): 415, ("NPE", "AKL"): 415,
    ("AKL", "NPL"): 360, ("NPL", "AKL"): 360,
    ("AKL", "ROT"): 230, ("ROT", "AKL"): 230,
    ("AKL", "TAI"): 275, ("TAI", "AKL"): 275,
    ("AKL", "WHA"): 160, ("WHA", "AKL"): 160,
    ("AKL", "GIS"): 475, ("GIS", "AKL"): 475,
    ("WLG", "PMR"): 140, ("PMR", "WLG"): 140,
    ("WLG", "NPE"): 320, ("NPE", "WLG"): 320,
    ("PIC", "CHC"): 335, ("CHC", "PIC"): 335,
    ("PIC", "NSN"): 110, ("NSN", "PIC"): 110,
    ("NSN", "BLH"): 115, ("BLH", "NSN"): 115,
    ("CHC", "TIM"): 165, ("TIM", "CHC"): 165,
    ("TIM", "DUD"): 200, ("DUD", "TIM"): 200,
    ("DUD", "IVC"): 205, ("IVC", "DUD"): 205,
    ("CHC", "DUD"): 360, ("DUD", "CHC"): 360,
    ("CHC", "GBM"): 245, ("GBM", "CHC"): 245,
    ("CHC", "ZQN"): 480, ("ZQN", "CHC"): 480,
    ("ZQN", "IVC"): 190, ("IVC", "ZQN"): 190,
    ("DUD", "ZQN"): 280, ("ZQN", "DUD"): 280,
    ("CHC", "OAM"): 250, ("OAM", "CHC"): 250,
    ("WLG", "PIC"): 92, ("PIC", "WLG"): 92,
    # Inter-island (via ferry) - land distance excluding ferry leg
    ("AKL", "CHC"): 980, ("CHC", "AKL"): 980,
    ("AKL", "DUD"): 1345, ("DUD", "AKL"): 1345,
    ("AKL", "IVC"): 1550, ("IVC", "AKL"): 1550,
    ("HLZ", "CHC"): 855, ("CHC", "HLZ"): 855,
    ("WLG", "CHC"): 335, ("CHC", "WLG"): 335,
    ("WLG", "NSN"): 110, ("NSN", "WLG"): 110,
    ("AKL", "ZQN"): 1390, ("ZQN", "AKL"): 1390,
}

# Cook Strait ferry crossing time in hours (incl. loading/unloading)
FERRY_CROSSING_HOURS = 3.5


def road_distance(org, dst):
    """Approximate road distance in km between depots."""
    return ROAD_DISTANCES.get((org, dst), 300)


def trip_duration_hours(org, dst, is_inter_island=False):
    """Approximate trip duration in hours including ferry crossing if inter-island."""
    dist = road_distance(org, dst)
    speed = 60.0 if dist < 250 else 80.0
    hours = dist / speed
    if is_inter_island:
        hours += FERRY_CROSSING_HOURS
    return round(hours, 1)


# ============================================================
# 承运商
# ============================================================
CARRIERS = [
    "Mainfreight", "Toll NZ", "PBT Transport", "NZ Post", "CourierPost",
    "Big Chill Distribution", "Hooker Pacific", "Dynes Transport",
    "HW Richardson Group", "Fonterra Transport", "Halls Group",
]

# ============================================================
# 货物商品池
# ============================================================
EXPORT_COMMODITIES = [
    ("Bulk milk (tanker)", "040120", (20000, 60000), ["high", "medium"], "tanker", None),
    ("Chilled lamb carcasses", "020422", (40000, 100000), ["VIP", "high"], "refrigerated", (-1.0, 4.0)),
    ("Frozen beef cartons", "020220", (30000, 80000), ["high"], "refrigerated", (-18.0, -15.0)),
    ("Live mussels (bagged)", "030731", (12000, 35000), ["high"], "refrigerated", (0.0, 4.0)),
    ("Kiwifruit export bins", "081050", (15000, 40000), ["high"], "refrigerated", (0.0, 1.0)),
    ("Fresh apples export cartons", "080810", (10000, 25000), ["medium"], "refrigerated", (0.0, 4.0)),
    ("Radiata pine logs", "440311", (8000, 20000), ["medium"], "flatbed", None),
    ("Sawn timber packs", "440711", (10000, 30000), ["medium"], "flatbed", None),
    ("Wool bales", "510111", (12000, 30000), ["medium"], "flatbed", None),
    ("Milk powder (bagged)", "040221", (25000, 70000), ["high"], "box_van", None),
    ("Cheese blocks", "040610", (15000, 40000), ["medium"], "refrigerated", (0.0, 8.0)),
    ("Manuka honey drums", "040900", (20000, 60000), ["high"], "box_van", None),
    ("Wine cases (export)", "220421", (8000, 25000), ["medium"], "box_van", None),
]

IMPORT_COMMODITIES = [
    ("Containerised retail goods", "990000", (20000, 60000), ["medium", "low"], "semi_trailer", None),
    ("Consumer electronics pallets", "854231", (30000, 90000), ["high"], "semi_trailer", None),
    ("Automotive parts (crate)", "870840", (15000, 40000), ["medium"], "semi_trailer", None),
    ("Construction materials", "730890", (10000, 30000), ["medium"], "flatbed", None),
    ("Structural steel beams", "730810", (15000, 45000), ["medium"], "flatbed", None),
    ("Packaged food products", "210390", (12000, 35000), ["medium"], "box_van", None),
    ("Industrial chemicals (DGR3)", "350691", (10000, 30000), ["medium"], "tanker", None),
    ("Agricultural machinery", "843359", (30000, 80000), ["high"], "low_loader", None),
    ("Pharmaceuticals (cold chain)", "300241", (60000, 150000), ["VIP"], "refrigerated", (2.0, 8.0)),
    ("Fresh produce (import)", "071490", (8000, 20000), ["low"], "refrigerated", (5.0, 15.0)),
]

DOMESTIC_COMMODITIES = [
    ("General freight (mixed pallets)", "990000", (10000, 30000), ["medium"], "semi_trailer", None),
    ("Chilled dairy products", "040310", (6000, 20000), ["medium"], "refrigerated", (0.0, 4.0)),
    ("Supermarket grocery restock", "990000", (10000, 25000), ["medium"], "semi_trailer", None),
    ("Beverage distribution stock", "220210", (8000, 20000), ["medium"], "box_van", None),
    ("Fresh salmon fillets", "030213", (15000, 35000), ["high"], "refrigerated", (0.0, 2.0)),
    ("Medical supplies and equipment", "901831", (25000, 60000), ["high"], "box_van", None),
    ("Machine spare parts (urgent)", "848390", (20000, 50000), ["VIP"], "box_van", None),
    ("Retail store stock", "990000", (10000, 25000), ["medium"], "semi_trailer", None),
    ("Courier parcels (line-haul)", "990000", (5000, 15000), ["low"], "semi_trailer", None),
    ("Fertiliser bags", "310520", (8000, 20000), ["medium"], "flatbed", None),
    ("Fuel delivery (tanker)", "271019", (15000, 40000), ["medium"], "tanker", None),
    ("Seafood (Pacific oysters)", "030711", (12000, 30000), ["medium"], "refrigerated", (0.0, 4.0)),
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
    ("Rocket Lab", "high"), ("Southern DHB", "high"), ("Pacific Fresh Foods", "medium"),
    ("Comvita", "medium"),
]

DELAY_REASONS = [
    ("congestion", 0.30), ("weather", 0.25), ("road_closure", 0.12), ("breakdown", 0.12),
    ("ferry", 0.08), ("driver_hours", 0.08), ("accident", 0.05),
]


def generate_depots(db):
    """Generate NZ road freight depot data."""
    for code, name, city, region, island, hub, congestion in NZ_DEPOTS:
        if not db.query(Depot).filter(Depot.depot_code == code).first():
            db.add(Depot(
                depot_code=code, name=name, city=city, region=region,
                island=island, is_hub=hub, congestion_level=congestion,
                weather=random.choice(WEATHER_POOL)
            ))
    db.commit()


# ============================================================
# 静态 seed 模板 - representative snapshot for first-run demo
# ============================================================
TRIP_TEMPLATES = [
    dict(tn="MF-AK-CH-0042", carrier="Mainfreight", vt="semi_trailer", org="AKL", dst="CHC",
         inter_island=True, delay=45, reason="ferry"),
    dict(tn="TL-AK-WL-0117", carrier="Toll NZ", vt="semi_trailer", org="AKL", dst="WLG",
         inter_island=False, delay=0, reason=None),
    dict(tn="BD-AK-HL-0033", carrier="Big Chill Distribution", vt="refrigerated", org="AKL", dst="HLZ",
         inter_island=False, delay=0, reason=None),
    dict(tn="MF-CH-DU-0088", carrier="Mainfreight", vt="semi_trailer", org="CHC", dst="DUD",
         inter_island=False, delay=90, reason="road_closure"),
    dict(tn="FT-HL-TR-0210", carrier="Fonterra Transport", vt="tanker", org="HLZ", dst="TRG",
         inter_island=False, delay=0, reason=None),
    dict(tn="PB-CH-GB-0015", carrier="PBT Transport", vt="flatbed", org="CHC", dst="GBM",
         inter_island=False, delay=120, reason="weather"),
    dict(tn="HP-AK-DU-0051", carrier="Hooker Pacific", vt="b_double", org="AKL", dst="DUD",
         inter_island=True, delay=0, reason=None),
    dict(tn="DY-WL-CH-0099", carrier="Dynes Transport", vt="semi_trailer", org="WLG", dst="CHC",
         inter_island=True, delay=180, reason="ferry"),
]

CONSIGNMENT_PROFILES = [
    # 跨岛 - 乳品到基督城
    dict(route="inter_island", org="AKL", dst="CHC", trip="MF-AK-CH-0042", pieces=26,
         weight=2400.0, vol=16.0, desc="Chilled dairy products", hs="040310", value=22000,
         tier="high", customer="Goodman Fielder", service="standard", priority="normal",
         temp_min=0.0, temp_max=4.0, sla_h=36, shipper="Goodman Fielder Auckland",
         consignee="Countdown DC Christchurch"),
    # 北岛干线 - 一般货物到惠灵顿
    dict(route="line_haul", org="AKL", dst="WLG", trip="TL-AK-WL-0117", pieces=18,
         weight=1800.0, vol=13.0, desc="General freight (mixed pallets)", hs="990000", value=18000,
         tier="medium", customer="Mainfreight", service="standard", priority="normal",
         temp_min=None, temp_max=None, sla_h=24, shipper="Mainfreight Auckland",
         consignee="Mainfreight Wellington"),
    # 金三角 - 冷链食品
    dict(route="regional", org="AKL", dst="HLZ", trip="BD-AK-HL-0033", pieces=12,
         weight=900.0, vol=7.0, desc="Chilled dairy products", hs="040310", value=9500,
         tier="medium", customer="Goodman Fielder", service="standard", priority="normal",
         temp_min=0.0, temp_max=4.0, sla_h=12, shipper="Goodman Fielder Auckland",
         consignee="Foodstuffs Hamilton DC"),
    # 南岛 - 道路封闭延误
    dict(route="line_haul", org="CHC", dst="DUD", trip="MF-CH-DU-0088", pieces=20,
         weight=2000.0, vol=14.0, desc="General freight (mixed pallets)", hs="990000", value=16000,
         tier="medium", customer="Foodstuffs NZ", service="standard", priority="normal",
         temp_min=None, temp_max=None, sla_h=20, shipper="Foodstuffs Christchurch",
         consignee="Foodstuffs Dunedin DC"),
    # 罐车 - 乳品
    dict(route="regional", org="HLZ", dst="TRG", trip="FT-HL-TR-0210", pieces=1,
         weight=25000.0, vol=28.0, desc="Bulk milk (tanker)", hs="040120", value=35000,
         tier="high", customer="Fonterra", service="standard", priority="high",
         temp_min=2.0, temp_max=6.0, sla_h=10, shipper="Fonterra Waitoa",
         consignee="Fonterra Tauranga Port"),
    # 木材 - 西海岸天气延误
    dict(route="regional", org="CHC", dst="GBM", trip="PB-CH-GB-0015", pieces=14,
         weight=12000.0, vol=40.0, desc="Sawn timber packs", hs="440711", value=14000,
         tier="medium", customer="Fletcher Building", service="standard", priority="normal",
         temp_min=None, temp_max=None, sla_h=30, shipper="Fletcher Building Christchurch",
         consignee="Fletcher Building Greymouth"),
    # 跨岛 - 冷链医药物流
    dict(route="inter_island", org="AKL", dst="DUD", trip="HP-AK-DU-0051", pieces=6,
         weight=400.0, vol=3.0, desc="Pharmaceuticals (cold chain)", hs="300241", value=110000,
         tier="VIP", customer="Pharmac NZ", service="express", priority="critical",
         temp_min=2.0, temp_max=8.0, sla_h=28, shipper="Pharmac Auckland",
         consignee="Southern DHB Dunedin"),
    # 跨岛 - 渡轮延误
    dict(route="inter_island", org="WLG", dst="CHC", trip="DY-WL-CH-0099", pieces=16,
         weight=1500.0, vol=11.0, desc="Supermarket grocery restock", hs="990000", value=13000,
         tier="medium", customer="Countdown Supermarkets", service="standard", priority="normal",
         temp_min=None, temp_max=None, sla_h=22, shipper="Countdown Wellington DC",
         consignee="Countdown Christchurch DC"),
]


def _trip(tpl):
    now = NOW + timedelta(hours=random.uniform(-8, 6))
    dur = trip_duration_hours(tpl["org"], tpl["dst"], tpl["inter_island"])
    return now, now + timedelta(hours=dur)


def generate_trips(db):
    """Generate representative road trips with delay injections."""
    for tpl in TRIP_TEMPLATES:
        if db.query(RoadTrip).filter(RoadTrip.trip_number == tpl["tn"]).first():
            continue
        sched_dep, sched_arr = _trip(tpl)
        dist = road_distance(tpl["org"], tpl["dst"])
        cap = _vehicle_capacity(tpl["vt"])
        trip = RoadTrip(
            trip_number=tpl["tn"], carrier=tpl["carrier"], vehicle_type=tpl["vt"],
            origin_depot=tpl["org"], destination_depot=tpl["dst"],
            is_inter_island=tpl["inter_island"],
            scheduled_departure=sched_dep, scheduled_arrival=sched_arr,
            delay_minutes=tpl["delay"], delay_reason_code=tpl["reason"],
            status="delayed" if tpl["delay"] else ("in_transit" if sched_dep < NOW else "scheduled"),
            distance_km=dist, capacity_kg=cap,
            loaded_kg=int(cap * random.uniform(0.55, 0.95)),
            driver_name=f"Driver {random.randint(100, 999)}",
            driver_hours_remaining=random.uniform(4, 13),
            trip_date=sched_dep,
        )
        trip.loaded_pct = round(trip.loaded_kg / cap * 100, 1)
        db.add(trip)
    db.commit()


def _vehicle_capacity(vt):
    caps = {"box_van": 4500, "semi_trailer": 22000, "b_double": 30000,
            "refrigerated": 20000, "tanker": 26000, "flatbed": 24000, "low_loader": 32000}
    return caps.get(vt, 15000)


def generate_consignments(db):
    """Generate representative consignments with events and exceptions."""
    seq = 1
    for prof in CONSIGNMENT_PROFILES:
        trip = db.query(RoadTrip).filter(RoadTrip.trip_number == prof["trip"]).first()
        if not trip:
            continue

        cn = f"RD-{50000000 + seq:08d}"
        sla = trip.scheduled_departure + timedelta(hours=prof["sla_h"])

        cons = RoadConsignment(
            consignment_number=cn, trip_number=trip.trip_number,
            route_type=prof["route"], origin_depot=prof["org"], destination_depot=prof["dst"],
            pieces=prof["pieces"], gross_weight_kg=prof["weight"], volume_cbm=prof["vol"],
            commodity_code=prof["hs"], commodity_desc=prof["desc"],
            shipper_name=prof["shipper"], consignee_name=prof["consignee"],
            customer_name=prof["customer"], customer_tier=prof["tier"],
            declared_value_nzd=prof["value"], service_level=prof["service"],
            priority=prof["priority"],
            sla_tier={"VIP": "gold", "high": "gold", "medium": "silver", "low": "bronze"}[prof["tier"]],
            temp_required_c=prof["temp_min"], temp_min_c=prof["temp_min"], temp_max_c=prof["temp_max"],
            current_status="booked", current_location=prof["org"],
            scheduled_delivery=trip.scheduled_arrival + timedelta(hours=2),
            estimated_delivery=trip.scheduled_arrival + timedelta(hours=2),
            sla_deadline=sla,
        )
        db.add(cons)
        db.flush()

        _generate_tracking_events(db, cons, trip, prof, seq)
        _generate_exceptions(db, cons, trip, prof, seq)
        seq += 1
    db.commit()


def _generate_tracking_events(db, cons, trip, prof, seq):
    """Generate POD milestone chain for a consignment."""
    dep = trip.scheduled_departure
    arr = trip.scheduled_arrival
    eff_arr = arr + timedelta(minutes=trip.delay_minutes or 0)
    milestones = [
        ("PUP", "Consignment picked up", cons.origin_depot, dep - timedelta(hours=4), None),
        ("LOAD", "Loaded onto vehicle", cons.origin_depot, dep - timedelta(hours=2), None),
        ("DEP", "Vehicle departed", cons.origin_depot, dep, None),
    ]
    if trip.is_inter_island:
        ferry_ts = dep + timedelta(hours=trip_duration_hours(cons.origin_depot, "WLG") if cons.origin_depot != "WLG" else 1)
        milestones.append(("FERRY", "Cook Strait ferry crossing", "WLG", ferry_ts, None))
    milestones.append(("ARR", "Vehicle arrived", cons.destination_depot, eff_arr, None))
    milestones.append(("UNLD", "Cargo unloaded", cons.destination_depot, eff_arr + timedelta(hours=1), None))
    milestones.append(("POD", "Proof of delivery signed", cons.destination_depot, eff_arr + timedelta(hours=2), None))

    latest = None
    for idx, (code, desc, loc, ts, reason) in enumerate(milestones):
        if ts > NOW:
            break
        db.add(RoadTrackingEvent(
            event_id=f"EVT-RD-{seq:04d}-{idx:02d}",
            consignment_number=cons.consignment_number,
            event_code=code, event_desc=desc, location=loc,
            timestamp=ts, source="tms",
            reason_code=reason, message=f"TMS: {trip.trip_number} {code} {loc}"
        ))
        latest = code
    if latest:
        cons.current_status = latest
        cons.current_location = cons.destination_depot if latest in ("ARR", "UNLD", "POD") else cons.origin_depot


def _generate_exceptions(db, cons, trip, prof, seq):
    """Generate realistic exceptions for selected consignments."""
    reason = trip.delay_reason_code
    if not reason:
        return
    exc_type, root_cause, diagnosis, confidence, recovery, delay_h = {
        "ferry": ("ferry_delay", "Cook Strait ferry sailing cancelled due to strong winds",
                  "MetService issued gale warning for Cook Strait. Interislander cancelled 3 sailings. "
                  "Consignment re-booked on next sailing +3h.", 0.92, ["wait", "reroute"], 3.0),
        "road_closure": ("road_closure", "SH1 closed due to slip near Oamaru",
                         "NZTA reports SH1 closed southbound after heavy rain caused a slip. "
                         "Detour via inland route adds 90 minutes.", 0.90, ["reroute", "wait"], 1.5),
        "weather": ("delay", "Snow on Arthur's Pass / Otira Gorge",
                    "Winter snow showers closing passes to chains-only. Trip delayed awaiting road crew.",
                    0.88, ["wait", "reroute"], 2.0),
    }.get(reason, ("delay", f"Trip delayed: {reason}",
                   f"Operational delay ({reason}) on {trip.trip_number}. Revised ETA updated.", 0.85,
                   ["wait"], 1.0))

    sla_breach = delay_h - 2.0
    score = calculate_risk_score(
        cargo_value=cons.declared_value_nzd,
        customer_tier=cons.customer_tier,
        sla_breach_hours=sla_breach,
        exception_type="delay" if exc_type in ("ferry_delay", "delay") else exc_type
    )
    risk_level = categorize_risk(score)
    severity = calculate_severity(score, sla_breach, exc_type)

    _cls = classifier.classify(root_cause or "")
    db.add(RoadException(
        exception_id=f"EXC-RD-{seq:04d}",
        consignment_number=cons.consignment_number,
        exception_type=exc_type, severity=severity, risk_level=risk_level,
        risk_score=score, detected_at=NOW - timedelta(minutes=random.randint(5, 60)),
        root_cause=root_cause, ai_diagnosis=diagnosis, ai_confidence=confidence,
        status="diagnosed" if risk_level == "low" else "pending_approval",
        requires_human_approval=risk_level != "low",
        recovery_options=json.dumps(recovery),
        delay_hours=delay_h,
        business_section=_cls["business_section"],
        classification_confidence=_cls["classification_confidence"],
        classification_decision=_cls["classification_decision"],
    ))


def clear_road_freight_tables(db):
    """Clear all road freight tables."""
    db.query(RoadException).delete()
    db.query(RoadTrackingEvent).delete()
    db.query(RoadConsignment).delete()
    db.query(RoadTrip).delete()
    db.query(Depot).delete()
    db.commit()


def seed_road_freight(clear=False):
    """Main entry point."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if clear:
            print("Clearing road freight tables...")
            clear_road_freight_tables(db)

        print("Generating depots...")
        generate_depots(db)
        print("Generating trips...")
        generate_trips(db)
        print("Generating consignments, events and exceptions...")
        generate_consignments(db)

        depots = db.query(Depot).count()
        trips = db.query(RoadTrip).count()
        cons = db.query(RoadConsignment).count()
        events = db.query(RoadTrackingEvent).count()
        exceptions = db.query(RoadException).count()
        print("\nRoad freight data seeded successfully!")
        print(f"  Depots:       {depots}")
        print(f"  Trips:        {trips}")
        print(f"  Consignments: {cons}")
        print(f"  Events:       {events}")
        print(f"  Exceptions:   {exceptions}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding road freight data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_flag = "--clear" in sys.argv
    seed_road_freight(clear=clear_flag)

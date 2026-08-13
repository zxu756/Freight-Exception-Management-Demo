"""
Air cargo seed data simulator for NZ domestic and international air freight.
空运货物模拟数据生成器 - 新西兰国内与国际空运货物

Generates a realistic snapshot of Southern Freight air cargo operations:
- Airports: NZ domestic network + international gateways
- Flights: passenger belly + dedicated freighters (today's schedule)
- Waybills: exports (dairy, seafood, meat, wine, honey), imports (e-commerce,
  pharma, electronics), domestic (general freight, time-critical parts)
- Tracking events: Cargo IMP milestone chains
- Customs/MPI inspections: NZ biosecurity checks
- Exceptions: flight delay, offload, temp excursion, customs hold, misroute

Usage:
    python air_cargo_seed.py          # seed default dataset
    python air_cargo_seed.py --clear  # clear air cargo tables only
"""
import json
import random
import sys
from datetime import datetime, timedelta, timezone

from database import engine, Base, SessionLocal
from air_cargo_models import (
    Airport, AirFlight, AirWaybill, AirTrackingEvent, AirCustomsInspection, AirException
)
from risk_calculator import calculate_risk_score, categorize_risk, calculate_severity
from event_classifier import classifier

random.seed(42)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# 机场数据 - NZ domestic network + international gateways
# ============================================================
NZ_AIRPORTS = [
    # (iata, name, city, is_gateway, curfew, congestion)
    ("AKL", "Auckland International Airport", "Auckland", True, None, 3),
    ("CHC", "Christchurch International Airport", "Christchurch", True, "23:00-06:00", 3),
    ("WLG", "Wellington International Airport", "Wellington", True, "23:00-06:00", 2),
    ("ZQN", "Queenstown Airport", "Queenstown", True, "22:00-06:00", 2),
    ("DUD", "Dunedin Airport", "Dunedin", False, None, 1),
    ("NSN", "Nelson Airport", "Nelson", False, None, 2),
    ("NPE", "Hawke's Bay Airport", "Napier", False, None, 1),
    ("HLZ", "Hamilton Airport", "Hamilton", False, None, 1),
    ("TRG", "Tauranga Airport", "Tauranga", False, None, 1),
    ("PMR", "Palmerston North Airport", "Palmerston North", False, None, 1),
    ("NPL", "New Plymouth Airport", "New Plymouth", False, None, 1),
    ("GIS", "Gisborne Airport", "Gisborne", False, None, 1),
    ("IVC", "Invercargill Airport", "Invercargill", False, None, 1),
    ("ROT", "Rotorua Airport", "Rotorua", False, None, 1),
]

INTL_AIRPORTS = [
    # (iata, name, city, country)
    ("SYD", "Sydney Kingsford Smith Airport", "Sydney", "Australia"),
    ("MEL", "Melbourne Airport", "Melbourne", "Australia"),
    ("BNE", "Brisbane Airport", "Brisbane", "Australia"),
    ("PVG", "Shanghai Pudong International Airport", "Shanghai", "China"),
    ("CAN", "Guangzhou Baiyun International Airport", "Guangzhou", "China"),
    ("HKG", "Hong Kong International Airport", "Hong Kong", "China"),
    ("SIN", "Singapore Changi Airport", "Singapore", "Singapore"),
    ("NRT", "Narita International Airport", "Tokyo", "Japan"),
    ("ICN", "Incheon International Airport", "Seoul", "South Korea"),
    ("LAX", "Los Angeles International Airport", "Los Angeles", "USA"),
    ("SFO", "San Francisco International Airport", "San Francisco", "USA"),
    ("NAN", "Nadi International Airport", "Nadi", "Fiji"),
    ("RAR", "Rarotonga International Airport", "Rarotonga", "Cook Islands"),
    ("APW", "Faleolo International Airport", "Apia", "Samoa"),
    ("TBU", "Fua'amotu International Airport", "Nuku'alofa", "Tonga"),
    ("DXB", "Dubai International Airport", "Dubai", "UAE"),
]

WEATHER_POOL = [
    "Clear, 12C, light NW wind",
    "Overcast, 9C, moderate S wind",
    "Rain showers, 8C, strong SW wind",
    "Fog patches, 5C, calm",
    "Fine, 15C, light breeze",
    "Gusty northerlies, 11C",
    "Snow showers nearby, 2C",
]

# ============================================================
# 航班数据 - today's schedule
# ============================================================
FLIGHT_TEMPLATES = [
    # Domestic (Air NZ / Parcelair / Airwork)
    dict(fn="NZ401", airline="Air New Zealand Cargo", ac="B777-300ER", freighter=False, org="AKL", dst="CHC", cap=12000),
    dict(fn="NZ447", airline="Air New Zealand Cargo", ac="A320neo", freighter=False, org="AKL", dst="WLG", cap=4500),
    dict(fn="NZ503", airline="Air New Zealand Cargo", ac="A320neo", freighter=False, org="CHC", dst="WLG", cap=4500),
    dict(fn="NZ565", airline="Air New Zealand Cargo", ac="ATR72-600", freighter=False, org="CHC", dst="DUD", cap=1200),
    dict(fn="PA301", airline="Parcelair", ac="B737-400F", freighter=True, org="AKL", dst="CHC", cap=18000),
    dict(fn="PA302", airline="Parcelair", ac="B737-400F", freighter=True, org="CHC", dst="AKL", cap=18000),
    dict(fn="AWK77", airline="Airwork", ac="B737-400F", freighter=True, org="AKL", dst="NPE", cap=16000),
    # International exports
    dict(fn="NZ87", airline="Air New Zealand Cargo", ac="B787-9", freighter=False, org="AKL", dst="PVG", cap=15000),
    dict(fn="NZ1", airline="Air New Zealand Cargo", ac="B787-9", freighter=False, org="AKL", dst="LAX", cap=15000),
    dict(fn="SQ282", airline="Singapore Airlines Cargo", ac="A350-900", freighter=False, org="AKL", dst="SIN", cap=13000),
    dict(fn="CX198", airline="Cathay Pacific Cargo", ac="A350-1000", freighter=False, org="AKL", dst="HKG", cap=14000),
    dict(fn="5Y8834", airline="Atlas Air", ac="B747-8F", freighter=True, org="AKL", dst="LAX", cap=115000),
    dict(fn="CZ306", airline="China Southern Cargo", ac="A330-300", freighter=False, org="CHC", dst="CAN", cap=11000),
    dict(fn="QF142", airline="Qantas Freight", ac="B737-800", freighter=False, org="AKL", dst="SYD", cap=5000),
    dict(fn="EK449", airline="Emirates SkyCargo", ac="A380-800", freighter=False, org="AKL", dst="DXB", cap=16000),
    # International imports
    dict(fn="NZ88", airline="Air New Zealand Cargo", ac="B787-9", freighter=False, org="PVG", dst="AKL", cap=15000),
    dict(fn="NZ2", airline="Air New Zealand Cargo", ac="B787-9", freighter=False, org="LAX", dst="AKL", cap=15000),
    dict(fn="SQ281", airline="Singapore Airlines Cargo", ac="A350-900", freighter=False, org="SIN", dst="AKL", cap=13000),
    dict(fn="CX197", airline="Cathay Pacific Cargo", ac="A350-1000", freighter=False, org="HKG", dst="AKL", cap=14000),
    dict(fn="QF143", airline="Qantas Freight", ac="B737-800", freighter=False, org="SYD", dst="AKL", cap=5000),
    dict(fn="NZ953", airline="Air New Zealand Cargo", ac="A320neo", freighter=False, org="NAN", dst="AKL", cap=4000),
]

# Pre-defined delay injections (flight_number -> (delay_minutes, reason_code, new_status))
FLIGHT_DELAYS = {
    "NZ447": (55, "weather", "delayed"),          # WLG fog
    "CZ306": (90, "congestion", "delayed"),       # CHC export backlog
    "5Y8834": (150, "technical", "delayed"),      # freighter technical issue
    "QF142": (35, "weather", "delayed"),          # Sydney storms
}

# ============================================================
# 运单模板 - realistic NZ cargo profiles (August 2026, winter)
# ============================================================
def _flt(t): return NOW + timedelta(hours=t)

WAYBILL_PROFILES = [
    # ---- 国际出口 (international exports) ----
    # 海产品龙虾出口中国
    dict(route="international", org="AKL", dst="PVG", flight="NZ87", pieces=8,
         weight=420.0, vol=3.2, chargeable=640.0, desc="Live rock lobster",
         hs="030632", value=45000, tier="VIP", customer="Fiordland Lobster Company",
         service="express", priority="critical", shc="PER", temp_min=2.0, temp_max=8.0,
         expiry_h=30, sla_h=18, shipper="Fiordland Lobster Company", consignee="Shanghai Fresh Seafood Import"),
    # 乳制品出口新加坡
    dict(route="international", org="AKL", dst="SIN", flight="SQ282", pieces=12,
         weight=980.0, vol=6.5, chargeable=1300.0, desc="Premium infant formula",
         hs="040221", value=62000, tier="high", customer="Fonterra",
         service="standard", priority="high", shc="PER", temp_min=2.0, temp_max=25.0,
         expiry_h=200, sla_h=36, shipper="Fonterra Co-operative", consignee="NTUC FairPrice"),
    # 羊肉出口洛杉矶（全货机）
    dict(route="international", org="AKL", dst="LAX", flight="5Y8834", pieces=24,
         weight=2100.0, vol=14.0, chargeable=2800.0, desc="Chilled prime lamb cuts",
         hs="020422", value=88000, tier="VIP", customer="Silver Fern Farms",
         service="standard", priority="high", shc="PER", temp_min=-1.0, temp_max=4.0,
         expiry_h=90, sla_h=48, shipper="Silver Fern Farms", consignee="Pacific Fresh Foods"),
    # 奇异果尾季出口中国
    dict(route="international", org="AKL", dst="PVG", flight="NZ87", pieces=10,
         weight=750.0, vol=5.0, chargeable=1000.0, desc="Zespri SunGold kiwifruit",
         hs="081050", value=28000, tier="high", customer="Zespri International",
         service="standard", priority="normal", shc="PER", temp_min=0.0, temp_max=1.0,
         expiry_h=120, sla_h=40, shipper="Zespri International", consignee="Shanghai Fruit Wholesale"),
    # 蜂蜜出口香港
    dict(route="international", org="AKL", dst="HKG", flight="CX198", pieces=5,
         weight=320.0, vol=2.2, chargeable=440.0, desc="Manuka honey MGO 830+",
         hs="040900", value=35000, tier="high", customer="Manuka Health",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=365*24, sla_h=36, shipper="Manuka Health NZ", consignee="Watsons HK"),
    # 葡萄酒出口悉尼
    dict(route="international", org="AKL", dst="SYD", flight="QF142", pieces=6,
         weight=480.0, vol=3.0, chargeable=600.0, desc="Marlborough Sauvignon Blanc",
         hs="220421", value=12000, tier="medium", customer="Cloudy Bay Vineyards",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=365*24, sla_h=28, shipper="Cloudy Bay Vineyards", consignee="Dan Murphy's"),
    # 樱桃苗/园艺产品出口广州
    dict(route="international", org="CHC", dst="CAN", flight="CZ306", pieces=14,
         weight=1100.0, vol=8.0, chargeable=1600.0, desc="Horticulture plant cuttings",
         hs="060210", value=32000, tier="high", customer="Plant & Food Research",
         service="standard", priority="high", shc="PER", temp_min=4.0, temp_max=15.0,
         expiry_h=72, sla_h=42, shipper="Plant & Food Research", consignee="Guangzhou Nursery Co"),
    # 医疗设备出口迪拜
    dict(route="international", org="AKL", dst="DXB", flight="EK449", pieces=3,
         weight=180.0, vol=1.5, chargeable=300.0, desc="Medical diagnostic equipment",
         hs="901890", value=95000, tier="VIP", customer="Fisher & Paykel Healthcare",
         service="express", priority="critical", shc="VAL", temp_min=None, temp_max=None,
         expiry_h=None, sla_h=48, shipper="Fisher & Paykel Healthcare", consignee="MedCare Gulf"),
    # 航空零部件出口悉尼（AOG加急）
    dict(route="international", org="AKL", dst="SYD", flight="QF142", pieces=2,
         weight=90.0, vol=0.8, chargeable=160.0, desc="Aircraft engine AOG spare part",
         hs="841191", value=58000, tier="high", customer="Air New Zealand Engineering",
         service="express", priority="critical", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=12, shipper="Air NZ Engineering", consignee="Qantas MRO Sydney"),

    # ---- 国际进口 (international imports) ----
    # 医药进口（温控）
    dict(route="international", org="SIN", dst="AKL", flight="SQ281", pieces=4,
         weight=240.0, vol=1.8, chargeable=360.0, desc="Temperature-sensitive vaccines",
         hs="300241", value=120000, tier="VIP", customer="Pharmac NZ",
         service="express", priority="critical", shc="PHR", temp_min=2.0, temp_max=8.0,
         expiry_h=60, sla_h=20, shipper="GSK Singapore", consignee="Pharmac Distribution Centre"),
    # 电商包裹进口（拼装货）
    dict(route="international", org="PVG", dst="AKL", flight="NZ88", pieces=65,
         weight=850.0, vol=9.5, chargeable=1900.0, desc="E-commerce parcels (consolidated)",
         hs="990000", value=45000, tier="medium", customer="NZ Post International",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=72, hawb=True, shipper="Cainiao Network", consignee="NZ Post"),
    # 电子产品进口
    dict(route="international", org="HKG", dst="AKL", flight="CX197", pieces=18,
         weight=540.0, vol=4.2, chargeable=840.0, desc="Consumer electronics components",
         hs="854231", value=76000, tier="high", customer="Fisher & Paykel Appliances",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=48, shipper="Foxconn HK", consignee="Fisher & Paykel Auckland"),
    # 食品进口（MPI高风险查验对象）
    dict(route="international", org="HKG", dst="AKL", flight="CX197", pieces=20,
         weight=900.0, vol=7.0, chargeable=1400.0, desc="Packaged Asian food products",
         hs="210390", value=28000, tier="medium", customer="Foodstuffs NZ",
         service="standard", priority="normal", shc="PER", temp_min=None, temp_max=25.0,
         expiry_h=500, sla_h=60, shipper="Lee Kum Kee HK", consignee="Foodstuffs Distribution"),
    # 汽车零部件进口
    dict(route="international", org="SYD", dst="AKL", flight="QF143", pieces=7,
         weight=520.0, vol=3.6, chargeable=720.0, desc="Automotive transmission parts",
         hs="870840", value=34000, tier="medium", customer="Toyota NZ",
         service="standard", priority="high", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=30, shipper="Toyota Australia", consignee="Toyota NZ Auckland"),
    # 太平洋岛国农产品进口
    dict(route="international", org="NAN", dst="AKL", flight="NZ953", pieces=30,
         weight=1500.0, vol=10.0, chargeable=2000.0, desc="Fresh tropical produce (taro, papaya)",
         hs="071490", value=9000, tier="low", customer="Pacific Produce Imports",
         service="standard", priority="normal", shc="PER", temp_min=5.0, temp_max=15.0,
         expiry_h=96, sla_h=36, shipper="Fiji Produce Exporters", consignee="Pacific Produce Imports"),
    # 危险品化工进口（合规申报）
    dict(route="international", org="SIN", dst="AKL", flight="SQ281", pieces=6,
         weight=300.0, vol=2.0, chargeable=400.0, desc="Industrial adhesive (DGR Class 3)",
         hs="350691", value=15000, tier="medium", customer="Fletcher Building",
         service="standard", priority="normal", shc="DGR", dg_class="3", un_number="UN1133",
         temp_min=None, temp_max=None, expiry_h=None, sla_h=48, shipper="Henkel Singapore", consignee="Fletcher Building"),

    # ---- 国内 (domestic) ----
    dict(route="domestic", org="AKL", dst="CHC", flight="PA301", pieces=22,
         weight=1600.0, vol=11.0, chargeable=2200.0, desc="General freight (mixed pallets)",
         hs="990000", value=18000, tier="medium", customer="Mainfreight",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=24, shipper="Mainfreight Auckland", consignee="Mainfreight Christchurch"),
    dict(route="domestic", org="AKL", dst="CHC", flight="NZ401", pieces=8,
         weight=380.0, vol=2.6, chargeable=520.0, desc="Chilled dairy products",
         hs="040310", value=9500, tier="medium", customer="Goodman Fielder",
         service="standard", priority="normal", shc="PER", temp_min=0.0, temp_max=4.0,
         expiry_h=168, sla_h=24, shipper="Goodman Fielder Auckland", consignee="Countdown DC Christchurch"),
    dict(route="domestic", org="AKL", dst="WLG", flight="NZ447", pieces=5,
         weight=160.0, vol=1.2, chargeable=240.0, desc="Legal documents and contracts",
         hs="490199", value=8000, tier="high", customer="Russell McVeagh",
         service="express", priority="critical", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=8, shipper="Russell McVeagh Auckland", consignee="Russell McVeagh Wellington"),
    dict(route="domestic", org="CHC", dst="WLG", flight="NZ503", pieces=12,
         weight=700.0, vol=5.0, chargeable=1000.0, desc="Fresh salmon fillets",
         hs="030213", value=26000, tier="high", customer="Mount Cook Alpine Salmon",
         service="express", priority="high", shc="PER", temp_min=0.0, temp_max=2.0,
         expiry_h=48, sla_h=10, shipper="Alpine Salmon Christchurch", consignee="Moore Wilson's Wellington"),
    dict(route="domestic", org="CHC", dst="DUD", flight="NZ565", pieces=10,
         weight=600.0, vol=4.0, chargeable=800.0, desc="Medical supplies and equipment",
         hs="901831", value=42000, tier="high", customer="Southern DHB",
         service="express", priority="critical", shc="VAL", temp_min=None, temp_max=None,
         expiry_h=None, sla_h=12, shipper="CDHB Logistics", consignee="Dunedin Hospital"),
    dict(route="domestic", org="AKL", dst="NPE", flight="AWK77", pieces=16,
         weight=1100.0, vol=8.0, chargeable=1600.0, desc="Beverage distribution stock",
         hs="220210", value=14000, tier="medium", customer="Coca-Cola Amatil NZ",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=180*24, sla_h=30, shipper="Coca-Cola Auckland", consignee="Coca-Cola Hawke's Bay"),
    dict(route="domestic", org="CHC", dst="AKL", flight="PA302", pieces=25,
         weight=1800.0, vol=12.0, chargeable=2400.0, desc="South Island courier parcels",
         hs="990000", value=15000, tier="low", customer="NZ Post",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=24, shipper="NZ Post Christchurch", consignee="NZ Post Auckland"),
    dict(route="domestic", org="AKL", dst="CHC", flight="NZ401", pieces=3,
         weight=120.0, vol=0.9, chargeable=180.0, desc="Machine spare parts (urgent)",
         hs="848390", value=36000, tier="VIP", customer="Fonterra",
         service="express", priority="critical", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=10, shipper="Fonterra Auckland", consignee="Fonterra Clandeboye Plant"),

    # ---- 中转 (transshipment) ----
    dict(route="transshipment", org="CHC", dst="LAX", flight="CZ306", transit=["CAN"],
         pieces=6, weight=420.0, vol=3.0, chargeable=600.0, desc="Frozen seafood (mussel products)",
         hs="030732", value=30000, tier="high", customer="Sanford Limited",
         service="standard", priority="high", shc="PER", temp_min=-18.0, temp_max=-15.0,
         expiry_h=180*24, sla_h=72, shipper="Sanford Christchurch", consignee="US Seafood Importers LA"),
    dict(route="transshipment", org="WLG", dst="PVG", flight="NZ447", transit=["AKL"],
         pieces=4, weight=280.0, vol=2.0, chargeable=400.0, desc="Wool fibre samples",
         hs="510111", value=11000, tier="medium", customer="Wools of New Zealand",
         service="standard", priority="normal", shc=None, temp_min=None, temp_max=None,
         expiry_h=None, sla_h=60, shipper="Wools of NZ Wellington", consignee="Shanghai Textile Co"),
]


def generate_airports(db):
    """Generate NZ domestic and international airport data."""
    for iata, name, city, gateway, curfew, congestion in NZ_AIRPORTS:
        if not db.query(Airport).filter(Airport.iata_code == iata).first():
            db.add(Airport(
                iata_code=iata, name=name, city=city, country="New Zealand",
                region="nz_domestic", is_nz_gateway=gateway,
                curfew_hours=curfew, congestion_level=congestion,
                weather=random.choice(WEATHER_POOL)
            ))
    for iata, name, city, country in INTL_AIRPORTS:
        if not db.query(Airport).filter(Airport.iata_code == iata).first():
            db.add(Airport(
                iata_code=iata, name=name, city=city, country=country,
                region="international", is_nz_gateway=False,
                curfew_hours=None, congestion_level=random.randint(1, 3),
                weather=random.choice(WEATHER_POOL)
            ))
    db.commit()


def flight_duration(org, dst):
    """Approximate flight duration in hours between airports."""
    durations = {
        ("AKL", "CHC"): 1.4, ("CHC", "AKL"): 1.4, ("AKL", "WLG"): 1.1,
        ("WLG", "AKL"): 1.1, ("CHC", "WLG"): 0.9, ("WLG", "CHC"): 0.9,
        ("CHC", "DUD"): 0.9, ("DUD", "CHC"): 0.9, ("AKL", "NPE"): 1.0,
        ("AKL", "SYD"): 3.4, ("SYD", "AKL"): 3.0, ("AKL", "PVG"): 12.2,
        ("PVG", "AKL"): 11.2, ("AKL", "LAX"): 12.0, ("LAX", "AKL"): 13.0,
        ("AKL", "SIN"): 10.7, ("SIN", "AKL"): 10.0, ("AKL", "HKG"): 11.4,
        ("HKG", "AKL"): 10.6, ("CHC", "CAN"): 11.8, ("CAN", "CHC"): 11.0,
        ("AKL", "DXB"): 17.0, ("DXB", "AKL"): 16.0, ("AKL", "NAN"): 3.0,
        ("NAN", "AKL"): 2.9,
    }
    return durations.get((org, dst), 6.0)


def generate_flights(db):
    """Generate today's flight schedule with delay injections."""
    for tpl in FLIGHT_TEMPLATES:
        if db.query(AirFlight).filter(AirFlight.flight_number == tpl["fn"]).first():
            continue
        sched_dep = NOW + timedelta(hours=random.uniform(-6, 8))
        dur = flight_duration(tpl["org"], tpl["dst"])
        sched_arr = sched_dep + timedelta(hours=dur)
        loaded_kg = int(tpl["cap"] * random.uniform(0.55, 0.95))
        flight = AirFlight(
            flight_number=tpl["fn"], airline=tpl["airline"],
            aircraft_type=tpl["ac"], is_freighter=tpl["freighter"],
            origin_airport=tpl["org"], destination_airport=tpl["dst"],
            scheduled_departure=sched_dep, scheduled_arrival=sched_arr,
            capacity_kg=tpl["cap"], loaded_kg=loaded_kg,
            loaded_pct=round(loaded_kg / tpl["cap"] * 100, 1),
            flight_date=NOW, status="scheduled"
        )
        if tpl["fn"] in FLIGHT_DELAYS:
            delay, reason, status = FLIGHT_DELAYS[tpl["fn"]]
            flight.delay_minutes = delay
            flight.delay_reason_code = reason
            flight.status = status
            flight.scheduled_arrival = sched_arr + timedelta(minutes=delay)
        elif sched_dep < NOW:
            flight.status = "departed"
            flight.actual_departure = sched_dep + timedelta(minutes=random.randint(0, 10))
            if sched_arr < NOW:
                flight.status = "landed"
                flight.actual_arrival = sched_arr
        db.add(flight)
    db.commit()


def generate_waybills(db):
    """Generate waybills with tracking events, inspections and exceptions."""
    seq = 1
    for prof in WAYBILL_PROFILES:
        flight = db.query(AirFlight).filter(AirFlight.flight_number == prof["flight"]).first()
        if not flight:
            continue

        awb = f"086-{80000000 + seq:08d}"
        hawb = None
        if prof.get("hawb"):
            hawb = f"086-{90000000 + seq:08d}"

        dep_dt = flight.scheduled_departure - timedelta(hours=3)
        sla = dep_dt + timedelta(hours=prof["sla_h"])

        shc = prof.get("shc")
        dg_class = prof.get("dg_class")
        un_number = prof.get("un_number")
        temp_min = prof.get("temp_min")
        temp_max = prof.get("temp_max")
        expiry = None
        if prof.get("expiry_h"):
            expiry = NOW + timedelta(hours=prof["expiry_h"])

        waybill = AirWaybill(
            awb_number=awb, hawb_number=hawb, route_type=prof["route"],
            origin_airport=prof["org"], destination_airport=prof["dst"],
            transit_points=json.dumps(prof.get("transit", [])),
            flight_number=flight.flight_number,
            pieces=prof["pieces"], gross_weight_kg=prof["weight"],
            volume_cbm=prof["vol"], chargeable_weight_kg=prof["chargeable"],
            commodity_code=prof["hs"], commodity_desc=prof["desc"],
            shipper_name=prof["shipper"], consignee_name=prof["consignee"],
            customer_name=prof["customer"], customer_tier=prof["tier"],
            declared_value_nzd=prof["value"], service_level=prof["service"],
            priority=prof["priority"],
            sla_tier={"VIP": "gold", "high": "gold", "medium": "silver", "low": "bronze"}[prof["tier"]],
            special_handling_codes=shc, dg_class=dg_class, un_number=un_number,
            temp_required_c=temp_min if (temp_min is not None and prof.get("shc") == "PER") else None,
            temp_min_c=temp_min, temp_max_c=temp_max,
            expiry_date=expiry,
            current_status="booked", current_location=prof["org"],
            scheduled_delivery=flight.scheduled_arrival + timedelta(hours=4),
            estimated_delivery=flight.scheduled_arrival + timedelta(hours=4),
            sla_deadline=sla,
        )
        db.add(waybill)
        db.flush()

        _generate_tracking_events(db, waybill, flight, prof, seq)
        _generate_inspections(db, waybill, prof, seq)
        _generate_exceptions(db, waybill, flight, prof, seq)

        seq += 1
    db.commit()


def _generate_tracking_events(db, waybill, flight, prof, seq):
    """Generate Cargo IMP milestone chain for a waybill."""
    milestones = [
        ("FNA", "Air waybill created", waybill.origin_airport, flight.scheduled_departure - timedelta(hours=10), None),
        ("BKD", "Booking confirmed", waybill.origin_airport, flight.scheduled_departure - timedelta(hours=9), None),
        ("RCS", "Cargo received at terminal", waybill.origin_airport, flight.scheduled_departure - timedelta(hours=5), None),
    ]
    if waybill.transit_points and waybill.transit_points != "[]":
        transit = json.loads(waybill.transit_points)[0]
        milestones.append(("DEP", "Flight departed", waybill.origin_airport,
                           flight.scheduled_departure - timedelta(minutes=0), None))
        milestones.append(("ARR", "Flight arrived at transit", transit,
                           flight.scheduled_arrival + timedelta(hours=1), None))
        milestones.append(("RCS", "Cargo transferred to connecting flight", transit,
                           flight.scheduled_arrival + timedelta(hours=3), None))
    else:
        milestones.append(("DEP", "Flight departed", waybill.origin_airport,
                           flight.scheduled_departure, None))
        milestones.append(("ARR", "Flight arrived", waybill.destination_airport,
                           flight.scheduled_arrival, None))

    if waybill.route_type != "domestic":
        milestones.append(("MNF", "Manifest submitted to customs", waybill.destination_airport,
                           flight.scheduled_arrival + timedelta(minutes=20), None))
        milestones.append(("CCD", "Customs cleared", waybill.destination_airport,
                           flight.scheduled_arrival + timedelta(hours=2), None))
        milestones.append(("NFD", "Notify for delivery", waybill.destination_airport,
                           flight.scheduled_arrival + timedelta(hours=3), None))
    milestones.append(("DLV", "Delivered to consignee", waybill.destination_airport,
                       flight.scheduled_arrival + timedelta(hours=4), None))

    # Only generate events up to "now" to simulate live tracking
    for idx, (code, desc, loc, ts, reason) in enumerate(milestones):
        if ts > NOW:
            break
        event = AirTrackingEvent(
            event_id=f"EVT-AIR-{seq:04d}-{idx:02d}",
            awb_number=waybill.awb_number,
            event_code=code, event_desc=desc, location=loc,
            timestamp=ts, source="carrier_api",
            reason_code=reason,
            message=f"Carrier: {waybill.flight_number} {code} {loc}"
        )
        db.add(event)

    # Update waybill current status to latest generated event
    if milestones and db.query(AirTrackingEvent).filter(
            AirTrackingEvent.awb_number == waybill.awb_number).first():
        latest_code = None
        for code, desc, loc, ts, reason in milestones:
            if ts <= NOW:
                latest_code = code
        if latest_code:
            waybill.current_status = latest_code
            for code, desc, loc, ts, reason in milestones:
                if ts <= NOW and code == "DEP":
                    waybill.current_location = waybill.destination_airport
                elif ts <= NOW:
                    waybill.current_location = loc


def _generate_inspections(db, waybill, prof, seq):
    """Generate customs/MPI inspections for imports and food exports."""
    needs_mpi = (
        waybill.route_type != "domestic"
        and (prof.get("hs", "").startswith(("03", "04", "05", "07", "08", "20", "21"))
             or "food" in prof["desc"].lower()
             or "produce" in prof["desc"].lower()
             or "lobster" in prof["desc"].lower()
             or "seafood" in prof["desc"].lower())
    )
    if not needs_mpi:
        return

    inspection = AirCustomsInspection(
        inspection_id=f"INS-AIR-{seq:04d}",
        awb_number=waybill.awb_number,
        inspection_type=random.choice(["mpi_biosecurity", "customs_xray", "mpi_physical"]),
        agency="MPI" if random.random() > 0.3 else "NZ_Customs",
        status="released",
        initiated_at=waybill.sla_deadline - timedelta(hours=6),
        released_at=waybill.sla_deadline - timedelta(hours=3),
        finding="No biosecurity risk material found"
    )
    db.add(inspection)


def _generate_exceptions(db, waybill, flight, prof, seq):
    """Generate realistic exceptions for selected waybills."""
    fn = flight.flight_number
    sla_breach_hours = 0.0
    exc_type = None
    root_cause = None
    diagnosis = None
    confidence = None
    delay_hours = 0.0
    recovery = []

    # WLG fog -> domestic express documents delayed, truck substitution
    if fn == "NZ447" and waybill.route_type == "domestic":
        exc_type = "delay"
        delay_hours = 1.2
        root_cause = "Fog at Wellington Airport reducing arrival capacity"
        diagnosis = ("METAR shows 200m visibility at WLG from 05:30Z. ATC ground delay "
                     "programme in place. Flight NZ447 delayed 55 minutes. "
                     "SLA buffer 4h - minor breach expected.")
        confidence = 0.96
        recovery = ["wait", "truck_substitution"]
    # Freighter technical -> lamb to LAX delayed, cold chain at risk
    elif fn == "5Y8834":
        exc_type = "delay"
        delay_hours = 2.5
        root_cause = "B747-8F technical fault - engine bleed air system"
        diagnosis = ("Maintenance log shows #2 engine bleed air fault. Aircraft grounded "
                     "2.5 hours pending part replacement. Chilled lamb shipment monitored - "
                     "cool store holding -1C, within tolerance.")
        confidence = 0.91
        recovery = ["wait", "rebook_next_flight"]
    # CHC export congestion -> horticulture cuttings delayed
    elif fn == "CZ306":
        exc_type = "delay"
        delay_hours = 1.5
        root_cause = "CHC export cargo congestion - seasonal uplift demand"
        diagnosis = ("CHC cargo terminal operating at 92% utilisation. ULD build queue "
                     "delayed CZ306 departure 90 minutes. Plant cuttings held in 8C cool store.")
        confidence = 0.89
        recovery = ["wait", "upgrade_priority"]
    # Pharma temp excursion during transit
    elif prof.get("shc") == "PHR" and prof.get("temp_min") is not None:
        exc_type = "temp_excursion"
        delay_hours = 0.0
        root_cause = "Temperature excursion above 8C during ULD staging"
        diagnosis = ("Temperature logger shows 9.4C for 47 minutes during ULD staging at SIN. "
                     "Vaccine manufacturer stability data supports short excursion. "
                     "Recommending expedited release and customer notification.")
        confidence = 0.88
        recovery = ["wait", "upgrade_priority", "rebook_next_flight"]
        waybill.temp_excursion_alert = True
    # Imported food MPI biosecurity hold
    elif prof.get("hs", "").startswith(("07", "21")) or "Packaged Asian food" in prof["desc"]:
        exc_type = "customs_hold"
        delay_hours = 6.0
        root_cause = "MPI biosecurity inspection hold"
        diagnosis = ("MPI selected consignment for biosecurity screening due to food product "
                     "declaration. Inspection scheduled. Estimated release +6h. "
                     "Historical pattern: 92% of similar holds release without finding.")
        confidence = 0.93
        recovery = ["wait", "upgrade_priority"]
    # Live lobster - flight delay risk
    elif "lobster" in prof["desc"].lower():
        exc_type = "delay"
        delay_hours = 0.8
        root_cause = "PVG slot congestion causing departure delay"
        diagnosis = ("PVG ATC slot window moved back 45 minutes. Live lobster in active "
                     "temperature control 4C. Mortalily risk increases after 24h transit. "
                     "Monitor and notify customer of revised ETA.")
        confidence = 0.85
        recovery = ["wait", "upgrade_priority", "express_courier"]

    if exc_type is None:
        return

    sla_breach = delay_hours - 4.0
    score = calculate_risk_score(
        cargo_value=waybill.declared_value_nzd,
        customer_tier=waybill.customer_tier,
        sla_breach_hours=sla_breach,
        exception_type="customs_hold" if exc_type == "customs_hold" else exc_type
    )
    risk_level = categorize_risk(score)
    severity = calculate_severity(score, sla_breach, exc_type)

    _cls = classifier.classify(root_cause or "")
    exc = AirException(
        exception_id=f"EXC-AIR-{seq:04d}",
        awb_number=waybill.awb_number,
        exception_type=exc_type, severity=severity, risk_level=risk_level,
        risk_score=score, detected_at=NOW - timedelta(minutes=random.randint(5, 60)),
        root_cause=root_cause, ai_diagnosis=diagnosis, ai_confidence=confidence,
        status="diagnosed" if risk_level == "low" else "pending_approval",
        requires_human_approval=risk_level != "low",
        recovery_options=json.dumps(recovery),
        delay_hours=delay_hours,
        business_section=_cls["business_section"],
        classification_confidence=_cls["classification_confidence"],
        classification_decision=_cls["classification_decision"],
    )
    db.add(exc)


def clear_air_cargo_tables(db):
    """Clear all air cargo tables."""
    db.query(AirException).delete()
    db.query(AirCustomsInspection).delete()
    db.query(AirTrackingEvent).delete()
    db.query(AirWaybill).delete()
    db.query(AirFlight).delete()
    db.query(Airport).delete()
    db.commit()


def seed_air_cargo(clear=False):
    """Main entry point."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if clear:
            print("Clearing air cargo tables...")
            clear_air_cargo_tables(db)

        print("Generating airports...")
        generate_airports(db)

        print("Generating flights...")
        generate_flights(db)

        print("Generating waybills, tracking events and exceptions...")
        generate_waybills(db)

        waybills = db.query(AirWaybill).count()
        flights = db.query(AirFlight).count()
        events = db.query(AirTrackingEvent).count()
        exceptions = db.query(AirException).count()
        inspections = db.query(AirCustomsInspection).count()
        airports = db.query(Airport).count()

        print("\nAir cargo data seeded successfully!")
        print(f"  Airports:   {airports}")
        print(f"  Flights:    {flights}")
        print(f"  Waybills:   {waybills}")
        print(f"  Events:     {events}")
        print(f"  Inspections:{inspections}")
        print(f"  Exceptions: {exceptions}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding air cargo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_flag = "--clear" in sys.argv
    seed_air_cargo(clear=clear_flag)

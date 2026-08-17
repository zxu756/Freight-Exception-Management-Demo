"""
Rail freight seed data - NZ rail stations, corridors and commodities.
铁路货运种子数据：新西兰车站、线路走廊与货物品类。
"""
import random

from rail_freight_models import RailStation, RailSegment
from customer_models import CUSTOMER_MASTER

CUSTOMERS = CUSTOMER_MASTER  # 复用统一客户目录

RAIL_STATIONS = [
    ("AKL", "Auckland Freight Terminal", "Auckland", "auckland", "north", True),
    ("HLZ", "Hamilton Freight Hub", "Hamilton", "waikato", "north", True),
    ("TRG", "Tauranga Rail Yard", "Tauranga", "bay_of_plenty", "north", False),
    ("MTM", "Mount Maunganui Terminal", "Mount Maunganui", "bay_of_plenty", "north", True),
    ("NPL", "New Plymouth Yard", "New Plymouth", "taranaki", "north", False),
    ("PNM", "Palmerston North Hub", "Palmerston North", "manawatu", "north", True),
    ("WGN", "Wellington Freight Terminal", "Wellington", "wellington", "north", True),
    ("CHC", "Christchurch Rail Hub", "Christchurch", "canterbury", "south", True),
    ("DUD", "Dunedin Freight Yard", "Dunedin", "otago", "south", False),
    ("IVC", "Invercargill Terminal", "Invercargill", "southland", "south", False),
]

# 线路走廊：(org, dst, 每日班次, 距离km, 运营方) — 双向都开
ROUTE_PAIRS = [
    ("AKL", "HLZ", 12, 125, "KiwiRail"),
    ("AKL", "TRG", 10, 210, "KiwiRail"),
    ("HLZ", "TRG", 8, 110, "Pacific Rail"),
    ("HLZ", "MTM", 10, 115, "KiwiRail"),
    ("AKL", "PNM", 8, 500, "KiwiRail"),
    ("PNM", "WGN", 14, 140, "KiwiRail"),
    ("PNM", "NPL", 4, 230, "Coastal Bulk Rail"),
    ("AKL", "WGN", 4, 680, "KiwiRail"),
    ("WGN", "CHC", 6, 470, "Interislander Rail", True),   # 铁路渡轮
    ("CHC", "DUD", 8, 360, "KiwiRail"),
    ("DUD", "IVC", 4, 210, "KiwiRail"),
    ("CHC", "IVC", 2, 570, "Coastal Bulk Rail"),
]

RAIL_ROUTES = []
for _o, _d, _f, _km, _op, *_rest in ROUTE_PAIRS:
    _ferry = bool(_rest and _rest[0])
    RAIL_ROUTES.append((_o, _d, _f, _km, _op, _ferry))
    RAIL_ROUTES.append((_d, _o, _f, _km, _op, _ferry))

RAIL_COMMODITIES = [
    ("040221", "Milk powder (bulk)"), ("440711", "Sawn timber packs"),
    ("270112", "Coal (bulk wagons)"), ("310210", "Fertiliser (bulk)"),
    ("720810", "Steel coil / plate"), ("220421", "Wine (containerised)"),
    ("480100", "Newsprint rolls"), ("020442", "Frozen lamb cartons"),
    ("870899", "Vehicle parts (intermodal)"), ("990000", "General freight (containers)"),
]

RAIL_DELAY_REASONS = [
    ("track_closure", 0.18), ("mechanical", 0.22), ("weather", 0.20),
    ("signal", 0.14), ("congestion", 0.14), ("crew", 0.08), ("ferry", 0.04),
]

# 线路级延误 profile：山地/沿海线路天气更敏感，渡轮线路受大风影响
RAIL_ROUTE_DELAY_PROFILES = {
    ("WGN", "CHC"): [("ferry", 0.45), ("weather", 0.35), ("mechanical", 0.10), ("crew", 0.10)],
    ("CHC", "WGN"): [("ferry", 0.45), ("weather", 0.35), ("mechanical", 0.10), ("crew", 0.10)],
    ("AKL", "PNM"): [("weather", 0.30), ("mechanical", 0.25), ("track_closure", 0.20), ("signal", 0.15), ("congestion", 0.10)],
    ("PNM", "AKL"): [("weather", 0.30), ("mechanical", 0.25), ("track_closure", 0.20), ("signal", 0.15), ("congestion", 0.10)],
    ("PNM", "NPL"): [("weather", 0.40), ("track_closure", 0.30), ("mechanical", 0.20), ("signal", 0.10)],
    ("NPL", "PNM"): [("weather", 0.40), ("track_closure", 0.30), ("mechanical", 0.20), ("signal", 0.10)],
    ("CHC", "IVC"): [("weather", 0.35), ("track_closure", 0.25), ("mechanical", 0.20), ("signal", 0.20)],
    ("IVC", "CHC"): [("weather", 0.35), ("track_closure", 0.25), ("mechanical", 0.20), ("signal", 0.20)],
    ("AKL", "WGN"): [("weather", 0.30), ("mechanical", 0.25), ("track_closure", 0.20), ("signal", 0.15), ("congestion", 0.10)],
    ("WGN", "AKL"): [("weather", 0.30), ("mechanical", 0.25), ("track_closure", 0.20), ("signal", 0.15), ("congestion", 0.10)],
}


def get_rail_delay_reasons(org, dst):
    return RAIL_ROUTE_DELAY_PROFILES.get((org, dst), RAIL_DELAY_REASONS)


def generate_rail_stations(db):
    """Idempotent station master data."""
    for code, name, city, region, island, hub in RAIL_STATIONS:
        if not db.query(RailStation).filter(RailStation.station_code == code).first():
            db.add(RailStation(station_code=code, name=name, city=city, region=region, island=island, is_hub=hub))
    db.commit()


def generate_rail_segments(db):
    """Idempotent segment master data (one per directed route)."""
    for org, dst, _f, _km, _op, _ferry in RAIL_ROUTES:
        if not db.query(RailSegment).filter(RailSegment.origin == org, RailSegment.destination == dst).first():
            db.add(RailSegment(origin=org, destination=dst, condition="clear", speed_factor=1.0, description="线路畅通"))
    db.commit()

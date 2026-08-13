"""
Sea freight seed data for NZ port container operations.
海运货物模拟数据生成器 - 新西兰港口集装箱作业

Port and vessel schedule data come from PortConnect (real). Container cargo,
tracking events and exceptions are generated against the real vessel visits.

Usage:
    python sea_freight_seed.py          # seed default dataset
    python sea_freight_seed.py --clear  # clear sea freight tables only
"""
import json
import random
import sys
from datetime import datetime, timedelta, timezone

from database import engine, Base, SessionLocal
from sea_freight_models import (
    SeaPort, VesselVisit, SeaContainer, SeaTrackingEvent, SeaException
)
from risk_calculator import calculate_risk_score, categorize_risk, calculate_severity
from event_classifier import classifier

random.seed(42)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# 港口数据 - NZ ports (from PortConnect)
# ============================================================
NZ_PORTS = [
    # (code, name, city, congestion)
    ("NZAKL", "Port of Auckland", "Auckland", 4),
    ("NZTRG", "Port of Tauranga", "Tauranga", 4),
    ("NZWLG", "CentrePort Wellington", "Wellington", 2),
    ("NZLYT", "Lyttelton Port Company", "Christchurch", 3),
    ("NZTIU", "Timaru Container Terminal", "Timaru", 2),
]

# 承运商 operator 代码 -> 名称 (from real PortConnect data)
OPERATOR_NAMES = {
    "ANNU": "ANL", "MAEU": "Maersk", "COSU": "COSCO", "MSCU": "MSC",
    "CMAU": "CMA CGM", "OOCL": "OOCL", "ONEY": "Ocean Network Express",
    "MOLU": "MOL", "NPDL": "Pacific Direct Line", "OCNU": "Oceanic Navigation",
    "WILU": "Wilhelmsen", "PACU": "Pacific Coastal", "MSK": "Maersk",
    "TOYO": "Toyofuji Shipping", "PFL": "Pacific Forum Line",
}

# ============================================================
# 集装箱货物池
# ============================================================
EXPORT_COMMODITIES = [
    ("Chilled lamb cuts", "020422", (60000, 180000), ["VIP", "high"], "RF", ( -1.0, 4.0)),
    ("Frozen beef cartons", "020220", (50000, 150000), ["high"], "RF", (-18.0, -15.0)),
    ("Dairy - whole milk powder", "040221", (45000, 120000), ["VIP", "high"], "GP", None),
    ("Cheese blocks", "040610", (30000, 80000), ["medium"], "RF", (0.0, 8.0)),
    ("Kiwifruit export trays", "081050", (25000, 60000), ["high"], "RF", (0.0, 1.0)),
    ("Apple export cartons", "080810", (18000, 45000), ["medium"], "RF", (0.0, 4.0)),
    ("Frozen seafood (mussels)", "030732", (30000, 70000), ["high"], "RF", (-18.0, -15.0)),
    ("Sawn timber bundles", "440711", (20000, 50000), ["medium"], "GP", None),
    ("Radiata pine logs", "440311", (15000, 40000), ["medium"], "GP", None),
    ("Wine (bottled)", "220421", (25000, 60000), ["medium"], "GP", None),
    ("Manuka honey drums", "040900", (35000, 90000), ["high"], "GP", None),
    ("Wool bales", "510111", (20000, 45000), ["medium"], "GP", None),
    ("Casein and protein powders", "350110", (40000, 100000), ["high"], "GP", None),
]

IMPORT_COMMODITIES = [
    ("E-commerce parcels (LCL)", "990000", (30000, 80000), ["medium", "low"], "GP", None),
    ("Consumer electronics", "854231", (60000, 150000), ["high"], "GP", None),
    ("Automotive parts", "870840", (30000, 70000), ["medium"], "GP", None),
    ("Construction machinery", "842952", (60000, 140000), ["medium"], "OT", None),
    ("Steel coils", "720827", (35000, 80000), ["medium"], "GP", None),
    ("Packaged food products", "210390", (25000, 60000), ["medium"], "GP", None),
    ("Industrial chemicals (DGR)", "350691", (20000, 50000), ["medium"], "GP", None),
    ("Pharmaceuticals (cold chain)", "300241", (100000, 250000), ["VIP"], "RF", (2.0, 8.0)),
    ("Medical equipment", "901890", (80000, 200000), ["VIP"], "GP", None),
    ("Fertiliser", "310520", (25000, 60000), ["medium"], "GP", None),
    ("Furniture and fittings", "940360", (30000, 70000), ["medium"], "HC", None),
    ("Plastic raw materials", "390210", (25000, 55000), ["low"], "GP", None),
]

CUSTOMERS = [
    ("Fonterra", "VIP"), ("Silver Fern Farms", "VIP"), ("Zespri International", "high"),
    ("Fisher & Paykel Healthcare", "VIP"), ("Fisher & Paykel Appliances", "high"),
    ("Sanford Limited", "high"), ("Sealord Group", "high"),
    ("Manuka Health", "high"), ("Cloudy Bay Vineyards", "medium"),
    ("Wools of New Zealand", "medium"), ("Mainfreight", "medium"),
    ("Foodstuffs NZ", "medium"), ("Countdown Supermarkets", "high"),
    ("NZ Post", "low"), ("Toyota NZ", "medium"), ("Fletcher Building", "medium"),
    ("Goodman Fielder", "medium"), ("Pharmac NZ", "VIP"),
    ("Kmart NZ", "low"), ("The Warehouse Group", "low"), ("Briscoe Group", "medium"),
    ("PlaceMakers", "medium"), ("Steel & Tube", "medium"),
    ("Pacific Fresh Foods", "medium"), ("Comvita", "medium"),
]

DELAY_REASONS = [
    ("weather", 0.25), ("port_congestion", 0.35), ("mechanical", 0.10),
    ("berth_unavailable", 0.15), ("labour", 0.10), ("covid_staffing", 0.05),
]


def generate_ports(db):
    """Generate NZ port master data."""
    for code, name, city, congestion in NZ_PORTS:
        if not db.query(SeaPort).filter(SeaPort.port_code == code).first():
            db.add(SeaPort(
                port_code=code, name=name, city=city, country="New Zealand",
                is_nz_port=True, congestion_level=congestion
            ))
    db.commit()


# ============================================================
# 静态 seed 模板 - representative snapshot for first-run demo
# ============================================================
CONTAINER_PROFILES = [
    dict(cn="MSCU5524682", vessel="MSC Amsterdam", voyage="V2024006", port="NZAKL",
         direction="import", size="40HC", ctype="RF", weight=23500, desc="Pharmaceuticals (cold chain)",
         hs="300241", value=180000, tier="VIP", customer="Pharmac NZ", temp=(2.0, 8.0),
         status="customs_hold", customs=True, bio=False),
    dict(cn="MAEU2154665", vessel="ANL Whangarei", voyage="V2024004", port="NZLYT",
         direction="import", size="40FT", ctype="GP", weight=22000, desc="Consumer electronics",
         hs="854231", value=95000, tier="high", customer="Fisher & Paykel Appliances", temp=None,
         status="discharged", customs=True, bio=False),
    dict(cn="CMAU4715861", vessel="Tasman Trader", voyage="V2024003", port="NZTRG",
         direction="export", size="20FT", ctype="RF", weight=18000, desc="Chilled lamb cuts",
         hs="020422", value=120000, tier="VIP", customer="Silver Fern Farms", temp=(-1.0, 4.0),
         status="at_sea", customs=False, bio=False),
    dict(cn="CSLU5524683", vessel="Southern Star", voyage="V2024000", port="NZWLG",
         direction="import", size="20FT", ctype="GP", weight=17500, desc="Packaged food products",
         hs="210390", value=32000, tier="medium", customer="Foodstuffs NZ", temp=None,
         status="customs_hold", customs=False, bio=False),
    dict(cn="OOCU8852341", vessel="Tasman Trader", voyage="V2024003", port="NZTRG",
         direction="export", size="40FT", ctype="GP", weight=26000, desc="Dairy - whole milk powder",
         hs="040221", value=78000, tier="high", customer="Fonterra", temp=None,
         status="at_sea", customs=False, bio=False),
    dict(cn="TLLU4417792", vessel="ANL Whangarei", voyage="V2024004", port="NZLYT",
         direction="import", size="40FT", ctype="HC", weight=24000, desc="Furniture and fittings",
         hs="940360", value=45000, tier="medium", customer="Briscoe Group", temp=None,
         status="available", customs=True, bio=True),
]


def generate_vessel_visits_from_snapshot(db, limit=None):
    """Load real vessel visits from the PortConnect local snapshot."""
    from portconnect_client import load_local_snapshot
    visits = load_local_snapshot()
    if limit:
        visits = visits[:limit]
    seen = {r[0] for r in db.query(VesselVisit.vessel_visit_id).all()}
    for v in visits:
        vid = (v.get("vesselVisitReference") or "|".join([
            v.get("vesselName", ""),
            v.get("inboundVoyage") or "",
            v.get("outboundVoyage") or "",
            v.get("portCode", ""),
            v.get("arrivalDatetime") or "",
        ]))
        if vid in seen:
            continue
        seen.add(vid)
        arr = _parse_dt(v.get("arrivalDatetime"))
        dep = _parse_dt(v.get("departureDatetime"))
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
            arrival_datetime=arr,
            departure_datetime=dep,
            last_updated=_parse_dt(v.get("lastUpdatedDateTime")),
        ))
    db.commit()


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def generate_containers(db):
    """Generate representative containers with events and exceptions."""
    visits = db.query(VesselVisit).filter(VesselVisit.vessel_type == "COMMERCIAL").all()
    if not visits:
        return
    seq = 1
    for prof in CONTAINER_PROFILES:
        visit = next((v for v in visits if v.vessel_name == prof["vessel"]), visits[0])
        if db.query(SeaContainer).filter(SeaContainer.container_number == prof["cn"]).first():
            continue
        container = SeaContainer(
            container_number=prof["cn"], vessel_visit_id=visit.vessel_visit_id,
            direction=prof["direction"], size=prof["size"], container_type=prof["ctype"],
            gross_weight_kg=prof["weight"], commodity_code=prof["hs"], commodity_desc=prof["desc"],
            customer_name=prof["customer"], customer_tier=prof["tier"],
            declared_value_nzd=prof["value"],
            temp_min_c=prof["temp"][0] if prof["temp"] else None,
            temp_max_c=prof["temp"][1] if prof["temp"] else None,
            current_status=prof["status"],
            customs_cleared=prof["customs"], biosecurity_cleared=prof["bio"],
            scheduled_delivery=(visit.arrival_datetime or NOW) + timedelta(hours=48),
            sla_deadline=(visit.arrival_datetime or NOW) + timedelta(hours=72),
        )
        db.add(container)
        db.flush()

        _generate_container_events(db, container, prof, seq)
        _generate_container_exceptions(db, container, prof, seq)
        seq += 1
    db.commit()


def _generate_container_events(db, container, prof, seq):
    """Generate POD milestone chain for a container based on its status."""
    port = prof["port"]
    base = NOW - timedelta(hours=seq * 6)
    milestones = [
        ("VAD", "Vessel arrived", port, base - timedelta(hours=12)),
        ("DIS", "Container discharged", port, base - timedelta(hours=8)),
    ]
    if prof["status"] == "customs_hold":
        milestones.append(("CHD", "Customs hold placed", port, base - timedelta(hours=6)))
    elif prof["status"] in ("available", "gate_out", "delivered"):
        milestones.append(("AVC", "Container available for collection", port, base - timedelta(hours=4)))
    if prof["status"] == "delivered":
        milestones.append(("GTO", "Container gate out", port, base - timedelta(hours=2)))
        milestones.append(("DLV", "Container delivered", port, base - timedelta(hours=1)))
    for idx, (code, desc, loc, ts) in enumerate(milestones):
        db.add(SeaTrackingEvent(
            event_id=f"EVT-RD-{seq:04d}-{idx:02d}",
            container_number=container.container_number,
            event_code=code, event_desc=desc, location=loc,
            timestamp=ts, source="portconnect",
            message=f"PortConnect: {code} {loc}"
        ))


def _generate_container_exceptions(db, container, prof, seq):
    """Generate exceptions for selected containers (customs_hold profiles)."""
    if prof["status"] != "customs_hold":
        return
    delay_hours = 24.0
    sla_breach = delay_hours - 4.0
    score = calculate_risk_score(
        cargo_value=container.declared_value_nzd,
        customer_tier=container.customer_tier,
        sla_breach_hours=sla_breach,
        exception_type="customs_hold"
    )
    risk_level = categorize_risk(score)
    severity = calculate_severity(score, sla_breach, "customs_hold")
    _cls = classifier.classify("NZ Customs inspection hold")
    db.add(SeaException(
        exception_id=f"EXC-RD-{seq:04d}",
        container_number=container.container_number,
        exception_type="customs_hold", severity=severity, risk_level=risk_level,
        risk_score=score, detected_at=NOW - timedelta(hours=seq),
        root_cause="NZ Customs inspection hold",
        ai_diagnosis="Customs selected container for inspection. Historical pattern: 88% release without finding.",
        ai_confidence=0.92,
        status="pending_approval", requires_human_approval=risk_level != "low",
        recovery_options=json.dumps(["wait", "expedite_documentation"]),
        delay_hours=delay_hours,
        business_section=_cls["business_section"],
        classification_confidence=_cls["classification_confidence"],
        classification_decision=_cls["classification_decision"],
        exception_category="Customs Hold",
        root_cause_category="documentation-compliance",
    ))


def clear_sea_freight_tables(db):
    """Clear all sea freight tables."""
    db.query(SeaException).delete()
    db.query(SeaTrackingEvent).delete()
    db.query(SeaContainer).delete()
    db.query(VesselVisit).delete()
    db.query(SeaPort).delete()
    db.commit()


def seed_sea_freight(clear=False):
    """Main entry point."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if clear:
            print("Clearing sea freight tables...")
            clear_sea_freight_tables(db)

        print("Generating ports...")
        generate_ports(db)
        print("Loading vessel visits from PortConnect snapshot...")
        generate_vessel_visits_from_snapshot(db)
        print("Generating containers...")
        generate_containers(db)

        ports = db.query(SeaPort).count()
        visits = db.query(VesselVisit).count()
        containers = db.query(SeaContainer).count()
        print("\nSea freight data seeded successfully!")
        print(f"  Ports:          {ports}")
        print(f"  Vessel visits:  {visits}")
        print(f"  Containers:     {containers}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding sea freight data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_flag = "--clear" in sys.argv
    seed_sea_freight(clear=clear_flag)

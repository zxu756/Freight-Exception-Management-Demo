"""
Multi-modal shipment graph - links import cargo across sea/air -> road legs.

Fourth pillar of the world core. When import cargo arrives at a NZ port (sea)
or airport (air), a road drayage leg is generated to move it inland. ShipmentLink
records every leg of one through-shipment, so delays cascade end to end.
"""
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime

from database import Base


class ShipmentLink(Base):
    """One leg of a through-shipment (sea/air first leg, road drayage second leg)."""
    __tablename__ = "shipment_links"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String(50), nullable=False, index=True)
    leg_index = Column(Integer, nullable=False)
    mode = Column(String(10), nullable=False)  # 'sea' | 'air' | 'road'
    reference = Column(String(40), nullable=False, index=True)  # container/awb/consignment number
    origin_code = Column(String(10), nullable=False)
    destination_code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# port code -> connecting road city code
PORT_CITY = {"NZAKL": "AKL", "NZTRG": "TRG", "NZWLG": "WLG", "NZLYT": "CHC", "NZTIU": "TIM"}

# NZ airport codes (all also map 1:1 to road depot codes)
NZ_AIRPORT_CODES = {"AKL", "CHC", "WLG", "ZQN", "DUD", "NSN", "NPE", "HLZ", "TRG", "PMR", "NPL", "GIS", "IVC", "ROT"}

_NORTH = {"AKL", "HLZ", "TRG", "ROT", "GIS", "NPE", "NPL", "PMR", "WLG", "WHA", "TAI"}
_SOUTH = {"PIC", "NSN", "BLH", "GBM", "CHC", "TIM", "OAM", "DUD", "ZQN", "IVC"}


def _island(code):
    if code in _NORTH:
        return "north"
    if code in _SOUTH:
        return "south"
    return None


def _unique_number(prefix):
    """Unique reference (uuid-based; distinct prefix avoids simulator collisions)."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def choose_inland_destination(db, origin_code):
    """Pick an inland depot for drayage, preferring the same island."""
    from road_freight_models import Depot
    depots = [d.depot_code for d in db.query(Depot).all()]
    island = _island(origin_code)
    candidates = [c for c in depots if c != origin_code and (island is None or _island(c) == island)]
    if not candidates:
        candidates = [c for c in depots if c != origin_code]
    return random.choice(candidates) if candidates else origin_code


def create_road_drayage(db, source_mode, source_ref, origin_code, commodity,
                       customer, tier, value, weight_kg, ready_at):
    """Create a road drayage leg for import cargo arriving by sea/air, and link both legs.

    The road leg's schedule is derived from `ready_at` (the sea/air arrival time),
    so a delay on the first leg automatically cascades into the second leg.
    """
    from road_freight_models import RoadTrip, RoadConsignment, RoadTrackingEvent
    from road_freight_seed import road_distance, trip_duration_hours

    # idempotency: don't double-create for the same source cargo
    existing = db.query(ShipmentLink).filter(ShipmentLink.reference == source_ref).first()
    if existing:
        return existing.shipment_id

    dest = choose_inland_destination(db, origin_code)
    shipment_id = f"SHIP-{source_mode.upper()}-{source_ref}"
    trip_number = _unique_number("DR-")
    cons_number = _unique_number("DC-")

    dep = ready_at + timedelta(hours=2)  # port/airport handover buffer
    inter = _island(origin_code) != _island(dest)
    dur_hours = trip_duration_hours(origin_code, dest, inter)
    arr = dep + timedelta(hours=dur_hours)
    dist = road_distance(origin_code, dest)

    trip = RoadTrip(
        trip_number=trip_number, carrier="Southern Freight Drayage", vehicle_type="semi_trailer",
        origin_depot=origin_code, destination_depot=dest, is_inter_island=inter,
        scheduled_departure=dep, scheduled_arrival=arr, status="scheduled",
        distance_km=dist, capacity_kg=22000,
        loaded_kg=int(min(weight_kg or 5000, 22000)), trip_date=dep,
    )
    db.add(trip)

    cons = RoadConsignment(
        consignment_number=cons_number, trip_number=trip_number, route_type="regional",
        origin_depot=origin_code, destination_depot=dest,
        pieces=1, gross_weight_kg=float(weight_kg or 5000), volume_cbm=12.0,
        commodity_desc=commodity or "General freight", shipper_name="", consignee_name="",
        customer_name=customer or "Unknown", customer_tier=tier or "medium",
        declared_value_nzd=float(value or 10000), service_level="standard",
        priority="normal", sla_tier="silver",
        current_status="booked", current_location=origin_code,
        scheduled_delivery=arr, sla_deadline=arr,
    )
    db.add(cons)

    db.add(RoadTrackingEvent(event_id=_unique_number("EVT-DR"), consignment_number=cons_number,
                            event_code="PUP", event_desc="Drayage pickup scheduled",
                            location=origin_code, timestamp=dep, source="tms"))
    db.add(RoadTrackingEvent(event_id=_unique_number("EVT-DR"), consignment_number=cons_number,
                            event_code="DEP", event_desc="Vehicle departed",
                            location=origin_code, timestamp=dep, source="carrier_api"))

    # link the two legs
    db.add(ShipmentLink(shipment_id=shipment_id, leg_index=1, mode=source_mode, reference=source_ref,
                        origin_code="origin", destination_code=origin_code))
    db.add(ShipmentLink(shipment_id=shipment_id, leg_index=2, mode="road", reference=cons_number,
                        origin_code=origin_code, destination_code=dest))
    db.flush()
    return shipment_id


def get_shipments(db, limit=50):
    """Group shipment links into through-shipment chains (newest first)."""
    links = db.query(ShipmentLink).order_by(ShipmentLink.shipment_id, ShipmentLink.leg_index).all()
    grouped = {}
    for l in links:
        grouped.setdefault(l.shipment_id, []).append(l)
    out = []
    for sid, legs in grouped.items():
        out.append({
            "shipment_id": sid,
            "legs": [{
                "leg_index": l.leg_index, "mode": l.mode, "reference": l.reference,
                "origin": l.origin_code, "destination": l.destination_code,
            } for l in legs],
        })
    out.sort(key=lambda s: s["shipment_id"], reverse=True)
    return out[:limit]

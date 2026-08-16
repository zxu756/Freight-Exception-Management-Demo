"""
Rail freight domain models - KiwiRail-style rail simulation (Scenario 4: road, rail and sea).
铁路货运模型（Scenario 4 要求 road, rail and sea）

- RailStation: 铁路车站/货场
- RailSegment: 线路区间实时状态（clear/slow/restricted/closed）
- RailService: 班列（train_number）
- RailConsignment + RailConsignmentLine: 托运单与票级（LTL 拼车）
- RailTrackingEvent: 追踪事件（RCL/DPT/INT/ARR/POD/DLY）
- RailException: 异常（含 P0-P2 字段：触发事件/检测延迟/实际执行结果）
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class RailStation(Base):
    """Rail station / freight yard."""
    __tablename__ = "rail_stations"

    id = Column(Integer, primary_key=True, index=True)
    station_code = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    island = Column(String(10), nullable=False)  # north / south
    is_hub = Column(Boolean, default=False)


class RailSegment(Base):
    """Live track condition for a route segment (实时线路状态)."""
    __tablename__ = "rail_segments"

    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    condition = Column(String(20), nullable=False, default="clear")  # clear/slow/restricted/closed
    speed_factor = Column(Float, nullable=False, default=1.0)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class RailService(Base):
    """A scheduled freight train service."""
    __tablename__ = "rail_services"

    id = Column(Integer, primary_key=True, index=True)
    train_number = Column(String(20), unique=True, nullable=False, index=True)
    operator = Column(String(50), nullable=False)
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    is_inter_island = Column(Boolean, default=False)  # 经库克海峡铁路渡轮
    scheduled_departure = Column(DateTime, nullable=False)
    scheduled_arrival = Column(DateTime, nullable=False)
    actual_departure = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="scheduled")
    # scheduled / loading / in_transit / delayed / arrived / cancelled
    delay_minutes = Column(Integer, default=0)
    delay_reason_code = Column(String(50), nullable=True)
    distance_km = Column(Float, default=0.0)
    capacity_t = Column(Integer, default=1200)
    loaded_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    consignments = relationship("RailConsignment", back_populates="train")


class RailConsignment(Base):
    """One rail consignment (a batch of wagons); LTL 时可含多票。"""
    __tablename__ = "rail_consignments"

    id = Column(Integer, primary_key=True, index=True)
    consignment_number = Column(String(20), unique=True, nullable=False, index=True)
    train_number = Column(String(20), ForeignKey("rail_services.train_number"), nullable=False, index=True)
    route_type = Column(String(20), nullable=False)  # intermodal / bulk / general
    is_ltl = Column(Boolean, default=False)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    commodity_code = Column(String(20), nullable=True)
    commodity_desc = Column(Text, nullable=False)
    pieces = Column(Integer, default=1)
    gross_weight_kg = Column(Float, nullable=False)
    declared_value_nzd = Column(Float, nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_tier = Column(String(20), nullable=False)
    service_level = Column(String(20), nullable=False)
    priority = Column(String(20), default="normal")
    sla_tier = Column(String(20), nullable=False)
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    temp_excursion_alert = Column(Boolean, default=False)
    current_status = Column(String(20), nullable=False, default="booked")
    # booked / loaded / departed / in_transit / arrived / delivered
    current_location = Column(String(3), nullable=True)
    scheduled_delivery = Column(DateTime, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    sla_deadline = Column(DateTime, nullable=True)
    sla_grace_deadline = Column(DateTime, nullable=True)
    is_sla_breached = Column(Boolean, default=False)
    breach_type = Column(String(20), nullable=True)
    sla_penalty_nzd = Column(Float, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    train = relationship("RailService", back_populates="consignments")
    events = relationship("RailTrackingEvent", back_populates="consignment")
    exceptions = relationship("RailException", back_populates="consignment")
    cargo_lines = relationship("RailConsignmentLine", back_populates="consignment")


class RailConsignmentLine(Base):
    """Ticket-level line inside a rail consignment (mirrors road/sea/air)."""
    __tablename__ = "rail_consignment_lines"

    id = Column(Integer, primary_key=True, index=True)
    consignment_number = Column(String(20), ForeignKey("rail_consignments.consignment_number"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)  # 1-based 票号
    commodity_code = Column(String(20), nullable=True)
    commodity_desc = Column(Text, nullable=False)
    shipper_name = Column(String(200), nullable=False)
    consignee_name = Column(String(200), nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_tier = Column(String(20), nullable=False)
    declared_value_nzd = Column(Float, nullable=False)
    pieces = Column(Integer, default=1)
    gross_weight_kg = Column(Float, nullable=False)
    service_level = Column(String(20), nullable=False)
    sla_tier = Column(String(20), nullable=False)
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    scheduled_delivery = Column(DateTime, nullable=True)
    sla_deadline = Column(DateTime, nullable=True)
    sla_grace_deadline = Column(DateTime, nullable=True)
    is_sla_breached = Column(Boolean, default=False)
    breach_type = Column(String(20), nullable=True)
    sla_penalty_nzd = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    consignment = relationship("RailConsignment", back_populates="cargo_lines")


class RailTrackingEvent(Base):
    """Rail tracking milestones: RCL 收运, DPT 发车, INT 途中检查点, ARR 到达, POD 交付, DLY 延误。"""
    __tablename__ = "rail_tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    consignment_number = Column(String(20), ForeignKey("rail_consignments.consignment_number"), nullable=False, index=True)
    event_code = Column(String(10), nullable=False)
    event_desc = Column(String(200), nullable=False)
    location = Column(String(3), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False, default="kiwirail_api")
    reason_code = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    consignment = relationship("RailConsignment", back_populates="events")


class RailException(Base):
    """Rail exception aligned with the common exception engine (incl. P0-P2 columns)."""
    __tablename__ = "rail_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String(50), unique=True, nullable=False, index=True)
    consignment_number = Column(String(20), ForeignKey("rail_consignments.consignment_number"), nullable=False, index=True)
    consignment_line_id = Column(Integer, ForeignKey("rail_consignment_lines.id"), nullable=True, index=True)
    exception_type = Column(String(50), nullable=False)
    # rail_delay / track_closure / mechanical_failure / weather_delay / signal_failure / predicted_anomaly
    severity = Column(String(20), nullable=False)
    risk_level = Column(String(20), nullable=False)
    risk_score = Column(Integer, nullable=False)
    detected_at = Column(DateTime, nullable=False)
    root_cause = Column(Text, nullable=True)
    ai_diagnosis = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    status = Column(String(50), nullable=False)
    requires_human_approval = Column(Boolean, default=False)
    recovery_options = Column(Text, nullable=True)
    delay_hours = Column(Float, default=0.0)
    business_section = Column(String(50), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    classification_decision = Column(String(20), nullable=True)
    ood_score = Column(Float, nullable=True)
    is_ood = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)
    anomaly_reason = Column(String(100), nullable=True)
    exception_category = Column(String(50), nullable=True)
    root_cause_category = Column(String(50), nullable=True)
    predicted_downstream_impact = Column(Text, nullable=True)
    recovery_cost = Column(Float, nullable=True)
    recommended_action = Column(String(50), nullable=True)
    recommendation_reason = Column(Text, nullable=True)
    sla_clock_paused = Column(Boolean, default=False)
    pause_reason = Column(String(20), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    trigger_event_id = Column(String(50), nullable=True)
    detection_latency_minutes = Column(Float, nullable=True)
    actual_action = Column(String(50), nullable=True)
    actual_cost = Column(Float, nullable=True)
    actual_recovery_hours = Column(Float, nullable=True)
    # EVT-006 / MON-005：处置与结案（误报/重复/关闭/重开）
    disposition = Column(String(20), nullable=True)  # confirmed/false_positive/duplicate/data_issue
    disposition_note = Column(Text, nullable=True)
    disposition_by = Column(String(100), nullable=True)
    disposition_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_evidence = Column(Text, nullable=True)
    reopen_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    consignment = relationship("RailConsignment", back_populates="exceptions")
    consignment_line = relationship("RailConsignmentLine")

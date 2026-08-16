"""
Road freight domain models for NZ domestic road freight simulation.
陆运货物领域模型 - 新西兰国内公路货运模拟

Covers line-haul (trunk) and regional trucking across the North and South
Islands, including inter-island Cook Strait ferry crossings (Ro-Ro).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Depot(Base):
    """
    Freight depot / distribution centre master data.
    分拨中心 / 物流中心主数据
    """
    __tablename__ = "road_depots"

    id = Column(Integer, primary_key=True, index=True)
    depot_code = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    region = Column(String(60), nullable=False)
    island = Column(String(10), nullable=False)  # 'north', 'south'
    is_hub = Column(Boolean, default=False)  # 主要分拨枢纽
    congestion_level = Column(Integer, default=1)  # 1-5 拥堵等级
    weather = Column(String(100), nullable=True)  # 当前天气快照


class RoadTrip(Base):
    """
    Road transport task (truck trip) - the equivalent of a flight.
    公路运输任务（卡车行程）- 相当于航班
    """
    __tablename__ = "road_trips"

    id = Column(Integer, primary_key=True, index=True)
    trip_number = Column(String(12), unique=True, nullable=False, index=True)
    carrier = Column(String(100), nullable=False)
    vehicle_type = Column(String(30), nullable=False)
    # 'box_van', 'semi_trailer', 'b_double', 'refrigerated', 'tanker', 'flatbed', 'low_loader'
    origin_depot = Column(String(3), ForeignKey("road_depots.depot_code"), nullable=False)
    destination_depot = Column(String(3), ForeignKey("road_depots.depot_code"), nullable=False)
    is_inter_island = Column(Boolean, default=False)  # 是否跨库克海峡（经渡轮）
    scheduled_departure = Column(DateTime, nullable=False)
    scheduled_arrival = Column(DateTime, nullable=False)
    actual_departure = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="scheduled")
    # 'scheduled', 'loading', 'in_transit', 'delayed', 'arrived', 'cancelled', 'diverted'
    delay_minutes = Column(Integer, default=0)
    delay_reason_code = Column(String(50), nullable=True)
    # 'congestion', 'weather', 'road_closure', 'breakdown', 'ferry', 'driver_hours', 'accident'
    distance_km = Column(Float, nullable=False)
    capacity_kg = Column(Integer, nullable=False)
    loaded_kg = Column(Integer, default=0)
    loaded_pct = Column(Float, default=0.0)
    driver_name = Column(String(100), nullable=True)
    driver_hours_remaining = Column(Float, default=13.0)  # 司机剩余工时（logbook 规则）
    trip_date = Column(DateTime, nullable=False)

    origin = relationship("Depot", foreign_keys=[origin_depot])
    destination = relationship("Depot", foreign_keys=[destination_depot])
    consignments = relationship("RoadConsignment", back_populates="trip")


class RoadConsignment(Base):
    """
    Road consignment (shipment note) - the core road shipment record.
    陆运货物托运单 - 核心货物记录
    """
    __tablename__ = "road_consignments"

    id = Column(Integer, primary_key=True, index=True)
    consignment_number = Column(String(20), unique=True, nullable=False, index=True)
    trip_number = Column(String(12), ForeignKey("road_trips.trip_number"), nullable=True)
    route_type = Column(String(20), nullable=False)  # 'line_haul', 'regional', 'inter_island'
    origin_depot = Column(String(3), ForeignKey("road_depots.depot_code"), nullable=False)
    destination_depot = Column(String(3), ForeignKey("road_depots.depot_code"), nullable=False)

    # Cargo details
    pieces = Column(Integer, nullable=False)
    gross_weight_kg = Column(Float, nullable=False)
    volume_cbm = Column(Float, nullable=False)
    commodity_code = Column(String(20), nullable=True)  # HS code
    commodity_desc = Column(Text, nullable=False)
    shipper_name = Column(String(200), nullable=False)
    consignee_name = Column(String(200), nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_tier = Column(String(20), nullable=False)  # 'VIP', 'high', 'medium', 'low'

    # Commercial
    declared_value_nzd = Column(Float, nullable=False)
    service_level = Column(String(20), nullable=False)  # 'same_day', 'express', 'standard'
    priority = Column(String(20), nullable=False, default='normal')  # 'normal', 'high', 'critical'
    sla_tier = Column(String(20), nullable=False, default='silver')  # 'gold', 'silver', 'bronze'
    is_ltl = Column(Boolean, default=False)  # 拼装：托运单内多票货（各票独立货主/SLA）

    # Special handling
    temp_required_c = Column(Float, nullable=True)
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    temp_excursion_alert = Column(Boolean, default=False)
    dg_class = Column(String(10), nullable=True)
    un_number = Column(String(10), nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    # Status & SLA
    current_status = Column(String(30), nullable=False, default='booked')
    current_location = Column(String(3), nullable=True)
    scheduled_delivery = Column(DateTime, nullable=False)
    estimated_delivery = Column(DateTime, nullable=True)
    sla_deadline = Column(DateTime, nullable=False)
    sla_grace_deadline = Column(DateTime, nullable=True)  # 宽限截止
    is_sla_breached = Column(Boolean, default=False)  # 是否 SLA 违约
    breach_type = Column(String(20), nullable=True)  # 'excused' / 'unexcused'
    sla_penalty_nzd = Column(Float, nullable=True)  # 违约金（NZD）
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    trip = relationship("RoadTrip", back_populates="consignments")
    origin = relationship("Depot", foreign_keys=[origin_depot])
    destination = relationship("Depot", foreign_keys=[destination_depot])
    events = relationship("RoadTrackingEvent", back_populates="consignment")
    exceptions = relationship("RoadException", back_populates="consignment")
    cargo_lines = relationship("ConsignmentLine", back_populates="consignment")


class ConsignmentLine(Base):
    """
    Consignment line - one LTL shipment inside a consolidated road consignment.

    Each line has its own commodity, customer, value and SLA commitment
    (mirrors CargoLine in sea freight / HouseWaybill in air freight).
    """
    __tablename__ = "consignment_lines"

    id = Column(Integer, primary_key=True, index=True)
    consignment_number = Column(String(20), ForeignKey("road_consignments.consignment_number"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)  # 1-based 票号
    commodity_code = Column(String(20), nullable=True)  # HS code
    commodity_desc = Column(Text, nullable=False)
    shipper_name = Column(String(200), nullable=False)
    consignee_name = Column(String(200), nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_tier = Column(String(20), nullable=False)  # 'VIP', 'high', 'medium', 'low'
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

    consignment = relationship("RoadConsignment", back_populates="cargo_lines")


class RoadTrackingEvent(Base):
    """
    Road freight tracking milestone events (proof-of-delivery chain).
    陆运货物追踪事件（POD 签收链路里程碑）
    """
    __tablename__ = "road_tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    consignment_number = Column(String(20), ForeignKey("road_consignments.consignment_number"), nullable=False, index=True)
    event_code = Column(String(10), nullable=False)
    # PUP 提货, LOAD 装车, DEP 发车, CKP 途中检查点, ARR 到达,
    # FERRY 渡轮航段, UNLD 卸货, POD 签收/交付完成, DLY 延误通告
    event_desc = Column(String(200), nullable=False)
    location = Column(String(3), nullable=True)  # depot code
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False, default='carrier_api')  # 'carrier_api', 'tms', 'ferry_api'
    reason_code = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    consignment = relationship("RoadConsignment", back_populates="events")


class RoadException(Base):
    """
    Road freight exception model aligned with the main exception engine.
    陆运异常模型（与主异常引擎对齐）
    """
    __tablename__ = "road_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String(50), unique=True, nullable=False, index=True)
    consignment_number = Column(String(20), ForeignKey("road_consignments.consignment_number"), nullable=False, index=True)
    consignment_line_id = Column(Integer, ForeignKey("consignment_lines.id"), nullable=True, index=True)  # 票级异常归属
    exception_type = Column(String(50), nullable=False)
    # 'delay', 'road_closure', 'breakdown', 'accident', 'driver_hours', 'temp_excursion', 'ferry_delay', 'overweight'
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    risk_level = Column(String(20), nullable=False)  # 'low', 'medium', 'high'
    risk_score = Column(Integer, nullable=False)  # 0-100
    detected_at = Column(DateTime, nullable=False)
    root_cause = Column(Text, nullable=True)
    ai_diagnosis = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    status = Column(String(50), nullable=False)
    # 'detected', 'diagnosed', 'pending_approval', 'resolved', 'escalated'
    requires_human_approval = Column(Boolean, default=False)
    recovery_options = Column(Text, nullable=True)  # JSON array
    # wait, reroute, substitute_vehicle, dispatch_second_driver, express_courier
    delay_hours = Column(Float, default=0.0)
    # ML 语义分类结果（业务板块 + 置信度 + 复核决策）
    business_section = Column(String(50), nullable=True)  # 6 个业务板块之一
    classification_confidence = Column(Float, nullable=True)  # 语义分类置信度 margin
    classification_decision = Column(String(20), nullable=True)  # 'automatic' / 'human_review' / 'ood'
    ood_score = Column(Float, nullable=True)  # 分布外分数（越高越分布外）
    is_ood = Column(Boolean, default=False)  # 是否分布外（全新异常模式）
    anomaly_score = Column(Float, nullable=True)  # 预测性异常分数（dwell-time 偏离度）
    anomaly_reason = Column(String(100), nullable=True)  # 如 dwell_DEP_ARR_exceeded_p95
    exception_category = Column(String(50), nullable=True)  # 8 类权威异常分类
    root_cause_category = Column(String(50), nullable=True)  # 10 类根因类别
    predicted_downstream_impact = Column(Text, nullable=True)  # 预测下游影响（异常链）
    recovery_cost = Column(Float, nullable=True)  # 恢复成本（NZD）
    recommended_action = Column(String(50), nullable=True)  # AI 选中的最佳恢复行动
    recommendation_reason = Column(Text, nullable=True)  # 推荐理由
    sla_clock_paused = Column(Boolean, default=False)  # 客户义务未履行，SLA 时钟暂停
    pause_reason = Column(String(20), nullable=True)  # 暂停原因（CU-01~CU-10）
    resolved_at = Column(DateTime, nullable=True)
    # Scenario 4 P0/P1：触发事件关联 + 检测延迟 + 实际执行结果
    trigger_event_id = Column(String(50), nullable=True)  # 触发该异常的那条追踪事件
    detection_latency_minutes = Column(Float, nullable=True)  # 触发事件 → 检测 的分钟数
    actual_action = Column(String(50), nullable=True)  # 协调员最终执行的恢复行动
    actual_cost = Column(Float, nullable=True)  # 实际恢复成本 NZD
    actual_recovery_hours = Column(Float, nullable=True)  # 实际挽回小时数
    created_at = Column(DateTime, default=datetime.utcnow)

    consignment = relationship("RoadConsignment", back_populates="exceptions")
    consignment_line = relationship("ConsignmentLine")


class RoadSegment(Base):
    """
    Live road condition for a route segment (实时路况).
    路段实时路况 - clear/slow/congested/closed，影响通行时间
    """
    __tablename__ = "road_segments"

    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String(3), nullable=False, index=True)  # depot code
    destination = Column(String(3), nullable=False, index=True)
    condition = Column(String(20), nullable=False, default="clear")  # 'clear', 'slow', 'congested', 'closed'
    speed_factor = Column(Float, nullable=False, default=1.0)  # 通行速度系数
    description = Column(Text, nullable=True)  # 路况说明 / 实时通报
    updated_at = Column(DateTime, default=datetime.utcnow)

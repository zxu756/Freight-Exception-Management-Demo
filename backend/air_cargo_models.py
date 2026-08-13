"""
Air cargo domain models for NZ domestic and international air freight simulation.
空运货物领域模型 - 新西兰国内与国际空运货物模拟
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Airport(Base):
    """
    Airport master data model.
    机场主数据
    """
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)
    iata_code = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    region = Column(String(30), nullable=False)  # 'nz_domestic', 'international'
    is_nz_gateway = Column(Boolean, default=False)  # 国际门户机场
    curfew_hours = Column(String(30), nullable=True)  # e.g. "22:30-06:00" 宵禁时段
    congestion_level = Column(Integer, default=1)  # 1-5 拥堵等级
    weather = Column(String(100), nullable=True)  # 当前天气快照


class AirFlight(Base):
    """
    Flight schedule model (passenger belly + dedicated freighter).
    航班模型（客机腹舱 + 全货机）
    """
    __tablename__ = "air_flights"

    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String(10), unique=True, nullable=False, index=True)
    airline = Column(String(100), nullable=False)
    aircraft_type = Column(String(50), nullable=False)  # B777-300ER, A320neo, ATR72-600, B737-400F
    is_freighter = Column(Boolean, default=False)
    origin_airport = Column(String(3), ForeignKey("airports.iata_code"), nullable=False)
    destination_airport = Column(String(3), ForeignKey("airports.iata_code"), nullable=False)
    scheduled_departure = Column(DateTime, nullable=False)
    scheduled_arrival = Column(DateTime, nullable=False)
    actual_departure = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="scheduled")
    # 'scheduled', 'boarding', 'departed', 'landed', 'delayed', 'cancelled', 'diverted'
    delay_minutes = Column(Integer, default=0)
    delay_reason_code = Column(String(50), nullable=True)
    # 'weather', 'technical', 'volcanic_ash', 'congestion', 'crew', 'security'
    capacity_kg = Column(Integer, nullable=False)
    loaded_kg = Column(Integer, default=0)
    loaded_pct = Column(Float, default=0.0)
    flight_date = Column(DateTime, nullable=False)

    origin = relationship("Airport", foreign_keys=[origin_airport])
    destination = relationship("Airport", foreign_keys=[destination_airport])
    waybills = relationship("AirWaybill", back_populates="flight")


class AirWaybill(Base):
    """
    Air waybill model - the core air shipment record.
    空运运单 - 核心货物记录
    """
    __tablename__ = "air_waybills"

    id = Column(Integer, primary_key=True, index=True)
    awb_number = Column(String(15), unique=True, nullable=False, index=True)  # "086-12345678"
    hawb_number = Column(String(15), nullable=True)  # 分运单号（拼装货）
    route_type = Column(String(20), nullable=False)  # 'domestic', 'international', 'transshipment'
    origin_airport = Column(String(3), ForeignKey("airports.iata_code"), nullable=False)
    destination_airport = Column(String(3), ForeignKey("airports.iata_code"), nullable=False)
    transit_points = Column(Text, nullable=True)  # JSON array of IATA codes 中转点
    flight_number = Column(String(10), ForeignKey("air_flights.flight_number"), nullable=True)

    # Cargo details
    pieces = Column(Integer, nullable=False)
    gross_weight_kg = Column(Float, nullable=False)
    volume_cbm = Column(Float, nullable=False)
    chargeable_weight_kg = Column(Float, nullable=False)
    commodity_code = Column(String(20), nullable=True)  # HS code
    commodity_desc = Column(Text, nullable=False)
    shipper_name = Column(String(200), nullable=False)
    consignee_name = Column(String(200), nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_tier = Column(String(20), nullable=False)  # 'VIP', 'high', 'medium', 'low'

    # Commercial
    declared_value_nzd = Column(Float, nullable=False)
    service_level = Column(String(20), nullable=False)  # 'express', 'standard', 'charter'
    priority = Column(String(20), nullable=False, default='normal')  # 'normal', 'high', 'critical'
    sla_tier = Column(String(20), nullable=False, default='silver')  # 'gold', 'silver', 'bronze'

    # Special handling
    special_handling_codes = Column(String(100), nullable=True)  # 'PER,PHR,VAL,DGR,AVI' comma separated
    dg_class = Column(String(10), nullable=True)  # 危险品类别
    un_number = Column(String(10), nullable=True)  # UN编号
    temp_required_c = Column(Float, nullable=True)  # 温控要求（摄氏度）
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    temp_excursion_alert = Column(Boolean, default=False)  # 温度超标告警
    expiry_date = Column(DateTime, nullable=True)  # 有效期（生鲜）

    # Status & SLA
    current_status = Column(String(30), nullable=False, default='booked')  # Cargo IMP milestone
    current_location = Column(String(3), nullable=True)  # IATA airport code
    scheduled_delivery = Column(DateTime, nullable=False)
    estimated_delivery = Column(DateTime, nullable=True)  # 更新后的预计送达
    sla_deadline = Column(DateTime, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    flight = relationship("AirFlight", back_populates="waybills")
    origin = relationship("Airport", foreign_keys=[origin_airport])
    destination = relationship("Airport", foreign_keys=[destination_airport])
    events = relationship("AirTrackingEvent", back_populates="waybill")
    inspections = relationship("AirCustomsInspection", back_populates="waybill")
    exceptions = relationship("AirException", back_populates="waybill")


class AirTrackingEvent(Base):
    """
    Cargo IMP standard milestone events for air cargo tracking.
    空运货物追踪事件（Cargo IMP 标准里程碑）
    """
    __tablename__ = "air_tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    awb_number = Column(String(15), ForeignKey("air_waybills.awb_number"), nullable=False, index=True)
    event_code = Column(String(10), nullable=False)
    # FNA 已创建, BKD 订舱确认, RCS 货物入库, DEP 起飞, ARR 到达,
    # MNF 舱单报海关, CDZ 海关扣留, CCD 海关放行, NFD 可提货通知,
    # OFF 卸货, AWD 到达仓库, DLV 派送完成
    event_desc = Column(String(200), nullable=False)
    location = Column(String(3), nullable=True)  # IATA airport code
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False, default='carrier_api')  # 'carrier_api', 'airport_api', 'customs_api'
    reason_code = Column(String(50), nullable=True)  # 延误原因码
    message = Column(Text, nullable=True)  # 承运商原始消息（供根因诊断）
    created_at = Column(DateTime, default=datetime.utcnow)

    waybill = relationship("AirWaybill", back_populates="events")


class AirCustomsInspection(Base):
    """
    Customs / MPI biosecurity inspection model (NZ specific).
    海关/MPI生物安全检查（新西兰特色）
    """
    __tablename__ = "air_customs_inspections"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(String(50), unique=True, nullable=False, index=True)
    awb_number = Column(String(15), ForeignKey("air_waybills.awb_number"), nullable=False, index=True)
    inspection_type = Column(String(30), nullable=False)
    # 'customs_xray', 'mpi_biosecurity', 'mpi_physical', 'document_check'
    agency = Column(String(30), nullable=False)  # 'NZ_Customs', 'MPI', 'CBP', 'ABF', 'China_Customs'
    status = Column(String(30), nullable=False, default='pending')
    # 'pending', 'under_review', 'released', 'hold', 'condemned'
    initiated_at = Column(DateTime, nullable=False)
    released_at = Column(DateTime, nullable=True)
    finding = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    waybill = relationship("AirWaybill", back_populates="inspections")


class AirException(Base):
    """
    Air cargo exception model aligned with the main exception engine.
    空运异常模型（与主异常引擎对齐）
    """
    __tablename__ = "air_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String(50), unique=True, nullable=False, index=True)
    awb_number = Column(String(15), ForeignKey("air_waybills.awb_number"), nullable=False, index=True)
    exception_type = Column(String(50), nullable=False)
    # 'delay', 'offload', 'diversion', 'customs_hold', 'damage', 'misroute', 'temp_excursion'
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    risk_level = Column(String(20), nullable=False)  # 'low', 'medium', 'high'
    risk_score = Column(Integer, nullable=False)  # 0-100
    detected_at = Column(DateTime, nullable=False)
    root_cause = Column(Text, nullable=True)
    ai_diagnosis = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)  # 0.00 - 1.00
    status = Column(String(50), nullable=False)
    # 'detected', 'diagnosed', 'pending_approval', 'resolved', 'escalated'
    requires_human_approval = Column(Boolean, default=False)
    recovery_options = Column(Text, nullable=True)  # JSON array of recovery options
    # rebook_next_flight, upgrade_priority, truck_substitution, express_courier, wait
    delay_hours = Column(Float, default=0.0)
    # ML 语义分类结果（业务板块 + 置信度 + 复核决策）
    business_section = Column(String(50), nullable=True)  # 6 个业务板块之一
    classification_confidence = Column(Float, nullable=True)  # 语义分类置信度 margin
    classification_decision = Column(String(20), nullable=True)  # 'automatic' / 'human_review' / 'ood'
    ood_score = Column(Float, nullable=True)  # 分布外分数（越高越分布外）
    is_ood = Column(Boolean, default=False)  # 是否分布外（全新异常模式）
    anomaly_score = Column(Float, nullable=True)  # 预测性异常分数（dwell-time 偏离度）
    anomaly_reason = Column(String(100), nullable=True)  # 如 dwell_DEP_ARR_exceeded_p95
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    waybill = relationship("AirWaybill", back_populates="exceptions")

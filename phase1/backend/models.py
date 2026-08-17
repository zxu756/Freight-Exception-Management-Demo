"""Data models for Phase 1 - Sea freight only."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from database import Base


class Port(Base):
    __tablename__ = "ports"
    id = Column(Integer, primary_key=True, index=True)
    port_code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False)


class Vessel(Base):
    __tablename__ = "vessels"
    id = Column(Integer, primary_key=True, index=True)
    vessel_id = Column(String(50), unique=True, nullable=False)
    vessel_name = Column(String(100), nullable=False)
    operator = Column(String(100), nullable=True)


class Container(Base):
    __tablename__ = "containers"
    id = Column(Integer, primary_key=True, index=True)
    container_number = Column(String(20), unique=True, nullable=False)
    vessel_id = Column(String(50), nullable=True)
    port_code = Column(String(10), nullable=True)
    status = Column(String(20), nullable=False, default="at_port")
    customer_name = Column(String(100), nullable=True)
    customer_tier = Column(String(20), nullable=True, default="medium")
    commodity_desc = Column(String(200), nullable=True)
    declared_value_nzd = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, nullable=False)
    container_number = Column(String(20), nullable=False)
    event_code = Column(String(10), nullable=False)
    event_desc = Column(String(200), nullable=False)
    location = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False, default="simulator")


class Exception(Base):
    __tablename__ = "exceptions"
    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String(50), unique=True, nullable=False)
    container_number = Column(String(20), nullable=False)
    exception_type = Column(String(30), nullable=False)
    severity = Column(String(10), nullable=False, default="medium")
    risk_score = Column(Integer, nullable=False, default=50)
    status = Column(String(20), nullable=False, default="detected")
    root_cause = Column(Text, nullable=True)
    ai_diagnosis = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    recommended_action = Column(String(50), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(50), unique=True, nullable=False)
    exception_id = Column(String(50), nullable=False)
    customer_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(20), nullable=False, default="email")
    status = Column(String(20), nullable=False, default="pending")
    phase = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(String(50), unique=True, nullable=False)
    exception_id = Column(String(50), nullable=False)
    decided_by = Column(String(100), nullable=False)
    decision = Column(String(20), nullable=False)
    chosen_action = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

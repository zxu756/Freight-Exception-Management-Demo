"""
SQLAlchemy ORM models for the Freight Exception Management System.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Shipment(Base):
    """
    Freight shipment order model.
    """
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_name = Column(String(200), nullable=False)
    customer_tier = Column(String(20), nullable=False)  # 'VIP', 'high', 'medium', 'low'
    cargo_description = Column(Text, nullable=False)
    cargo_value = Column(Float, nullable=False)
    origin = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)
    transport_mode = Column(String(50), nullable=False)  # 'road', 'rail', 'sea', 'air'
    scheduled_pickup = Column(DateTime, nullable=False)
    scheduled_delivery = Column(DateTime, nullable=False)
    sla_deadline = Column(DateTime, nullable=False)
    sla_buffer_hours = Column(Integer, nullable=False)
    current_status = Column(String(50), nullable=False)
    current_eta = Column(DateTime, nullable=True)
    container_id = Column(String(50), nullable=True)
    vehicle_id = Column(String(50), nullable=True)
    special_requirements = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exceptions = relationship("Exception", back_populates="shipment")
    events = relationship("Event", back_populates="shipment")


class Exception(Base):
    """
    Freight exception model.
    """
    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String(50), unique=True, nullable=False, index=True)
    shipment_id = Column(String(50), ForeignKey("shipments.shipment_id"), nullable=False)
    exception_type = Column(String(50), nullable=False)  # 'delay', 'damage', 'misroute', 'customs_hold'
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    risk_level = Column(String(20), nullable=False)  # 'low', 'medium', 'high'
    detected_at = Column(DateTime, nullable=False)
    root_cause = Column(Text, nullable=True)
    ai_diagnosis = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)  # 0.00 to 1.00
    status = Column(String(50), nullable=False)  # 'detected', 'diagnosed', 'pending_approval', etc.
    requires_human_approval = Column(Boolean, default=False)
    assigned_to = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_time_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    shipment = relationship("Shipment", back_populates="exceptions")
    events = relationship("Event", back_populates="exception")
    decisions = relationship("Decision", back_populates="exception")
    notifications = relationship("Notification", back_populates="exception")


class Event(Base):
    """
    Tracking and system event model.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    shipment_id = Column(String(50), ForeignKey("shipments.shipment_id"), nullable=True)
    exception_id = Column(String(50), ForeignKey("exceptions.exception_id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    event_source = Column(String(100), nullable=False)  # 'carrier_api', 'port_api', etc.
    event_data = Column(Text, nullable=True)  # JSON string
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    shipment = relationship("Shipment", back_populates="events")
    exception = relationship("Exception", back_populates="events")


class Decision(Base):
    """
    AI recommendation and human decision model.
    """
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(String(50), unique=True, nullable=False, index=True)
    exception_id = Column(String(50), ForeignKey("exceptions.exception_id"), nullable=False)
    decision_type = Column(String(50), nullable=False)  # 'auto_resolve', 'recommend', 'escalate'
    options = Column(Text, nullable=False)  # JSON string of options array
    recommended_option = Column(String(10), nullable=True)
    recommendation_reasoning = Column(Text, nullable=True)
    human_decision = Column(String(10), nullable=True)
    human_decision_by = Column(String(100), nullable=True)
    human_decision_at = Column(DateTime, nullable=True)
    decision_outcome = Column(String(50), nullable=True)  # 'accepted', 'modified', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    exception = relationship("Exception", back_populates="decisions")


class Notification(Base):
    """
    Customer and internal notification model.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(50), unique=True, nullable=False, index=True)
    exception_id = Column(String(50), ForeignKey("exceptions.exception_id"), nullable=False)
    recipient_type = Column(String(50), nullable=False)  # 'customer', 'coordinator', 'team'
    recipient = Column(String(200), nullable=False)
    channel = Column(String(50), nullable=False)  # 'email', 'sms', 'system'
    subject = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)  # 'sent', 'delivered', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    exception = relationship("Exception", back_populates="notifications")

"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Shipment Schemas
class ShipmentBase(BaseModel):
    shipment_id: str
    customer_name: str
    customer_tier: str
    cargo_description: str
    cargo_value: float
    origin: str
    destination: str
    transport_mode: str
    scheduled_pickup: datetime
    scheduled_delivery: datetime
    sla_deadline: datetime
    sla_buffer_hours: int
    current_status: str
    current_eta: Optional[datetime] = None
    container_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    special_requirements: Optional[str] = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentResponse(ShipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Exception Schemas
class ExceptionBase(BaseModel):
    exception_id: str
    shipment_id: str
    exception_type: str
    severity: str
    risk_level: str
    detected_at: datetime
    root_cause: Optional[str] = None
    ai_diagnosis: Optional[str] = None
    ai_confidence: Optional[float] = None
    status: str
    requires_human_approval: bool = False
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_time_minutes: Optional[int] = None


class ExceptionCreate(ExceptionBase):
    pass


class ExceptionResponse(ExceptionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Decision Schemas
class DecisionOption(BaseModel):
    option_id: str
    description: str
    cost: float
    new_eta: datetime
    sla_impact: str
    risk: str
    utility_score: Optional[float] = None


class DecisionBase(BaseModel):
    decision_id: str
    exception_id: str
    decision_type: str
    options: List[DecisionOption]
    recommended_option: Optional[str] = None
    recommendation_reasoning: Optional[str] = None


class DecisionCreate(DecisionBase):
    pass


class DecisionResponse(DecisionBase):
    id: int
    human_decision: Optional[str] = None
    human_decision_by: Optional[str] = None
    human_decision_at: Optional[datetime] = None
    decision_outcome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Approval Request
class ApprovalRequest(BaseModel):
    decision: str
    notes: Optional[str] = None
    approved_by: str


# Notification Schemas
class NotificationBase(BaseModel):
    notification_id: str
    exception_id: str
    recipient_type: str
    recipient: str
    channel: str
    subject: Optional[str] = None
    message: str
    sent_at: datetime
    status: str


class NotificationResponse(NotificationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Event Schemas
class EventBase(BaseModel):
    event_id: str
    shipment_id: Optional[str] = None
    exception_id: Optional[str] = None
    event_type: str
    event_source: str
    event_data: Optional[str] = None
    timestamp: datetime


class EventResponse(EventBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Demo Control Schemas
class DemoStartRequest(BaseModel):
    mode: str = Field(..., pattern="^(auto|step|interactive)$")


class DemoControlResponse(BaseModel):
    success: bool
    message: str
    mode: Optional[str] = None


# API Response Wrapper
class APIResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[dict] = None

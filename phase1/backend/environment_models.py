"""
Environmental event models - the trigger source for freight delays.
环境事件模型 - 货运延误的触发源

Instead of injecting a random delay reason at task-creation time, delays are
now triggered by environmental events (heavy rain, road closure, port
congestion, accident) that occur at a location and affect cargo passing
through it. Each event carries a factual description (路况信息) used to
confirm the "suspected delay" before it becomes a real delay.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from database import Base


class EnvironmentEvent(Base):
    """A location-based environmental event that can delay passing cargo."""
    __tablename__ = "environment_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(30), nullable=False, index=True)
    # 'weather', 'road_closure', 'port_congestion', 'accident', 'fog', 'snow', 'ferry_cancelled'
    mode = Column(String(10), nullable=False, index=True)  # 'sea', 'road', 'air'
    location = Column(String(20), nullable=False, index=True)  # city/port/airport code
    severity = Column(String(10), nullable=False)  # 'minor', 'moderate', 'severe'
    description = Column(Text, nullable=False)  # 事实描述 / 路况信息
    started_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    # 实际开始影响班次的时刻（缓冲期后）。雪/雨等需要累积，一开始不封路，
    # 过了 impact_at 才真正造成延误；impact_at 之前是"预测期"。
    impact_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def is_active(self, now):
        return self.started_at <= now <= self.ends_at

    @property
    def is_impacting(self, now):
        """已过缓冲期，正在实际影响班次。"""
        impact = self.impact_at or self.started_at
        return impact <= now <= self.ends_at


# 各运输方式的事件类型 → 延误原因码
EVENT_TYPE_TO_REASON = {
    "weather": "weather",
    "fog": "weather",
    "snow": "weather",
    "road_closure": "road_closure",
    "port_congestion": "port_congestion",
    "accident": "accident",
    "ferry_cancelled": "ferry",
}

# 严重度 → 延误时长（分钟）
SEVERITY_DELAY_MINUTES = {
    "minor": (15, 60),
    "moderate": (60, 240),
    "severe": (240, 720),
}

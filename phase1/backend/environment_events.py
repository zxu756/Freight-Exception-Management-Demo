"""
Environmental event generator and lookup.
环境事件生成器与查询

Events are generated continuously by the simulators and live at specific
locations. When a task's route passes through a location with an active event,
the cargo is flagged as "suspected delay" with the event's factual description
(路况信息) before being confirmed as a real delay.
"""
import random
from datetime import timedelta

from environment_models import EnvironmentEvent

# 各运输方式的事件类型 → 事实描述模板（路况信息）
EVENT_TEMPLATES = {
    "road": {
        "weather": "暴雨导致 {loc} 地区道路能见度低，通行缓慢",
        "road_closure": "SH1 {loc} 附近发生滑坡，道路封闭",
        "accident": "{loc} 附近发生交通事故，车道封闭",
    },
    "air": {
        "weather": "{loc} 机场遭遇暴雨，航班起降受限",
        "fog": "{loc} 机场大雾，能见度低于起降标准",
        "snow": "{loc} 机场积雪，跑道清理中",
    },
    "sea": {
        "port_congestion": "{loc} 港口拥堵，船舶排队等待靠泊",
        "weather": "{loc} 港区大风，船舶靠泊暂停",
        "ferry_cancelled": "{loc} 库克海峡大风，渡轮停航",
    },
    "rail": {
        "weather": "{loc} 铁路沿线暴雨，限速运行",
        "track_closure": "{loc} 铁路线路封闭，班列停运绕行",
        "signal": "{loc} 铁路信号故障，限速运行",
        "mechanical": "{loc} 铁路机车故障，班列延误",
    },
}

# 各运输方式的地点（用于随机生成事件）
ROAD_LOCATIONS = ["AKL", "HLZ", "TRG", "WLG", "CHC", "GBM", "DUD", "ZQN", "NPE", "NPL"]
AIR_LOCATIONS = ["AKL", "CHC", "WLG", "ZQN", "DUD", "NSN", "NPE", "HLZ", "TRG", "IVC"]
SEA_LOCATIONS = ["NZAKL", "NZTRG", "NZWLG", "NZLYT", "NZTIU"]
RAIL_LOCATIONS = ["AKL", "HLZ", "TRG", "MTM", "NPL", "PNM", "WGN", "CHC", "DUD", "IVC"]


def generate_event(db, mode, location, now):
    """Generate a random environmental event at a location."""
    templates = EVENT_TEMPLATES.get(mode)
    if not templates:
        return None
    event_type = random.choice(list(templates.keys()))
    severity = random.choices(["minor", "moderate", "severe"], weights=[0.4, 0.4, 0.2])[0]
    description = templates[event_type].format(loc=location)
    duration_hours = random.choice([2, 3, 4, 6, 8, 12, 18, 24, 36, 48])
    event = EnvironmentEvent(
        event_type=event_type, mode=mode, location=location,
        severity=severity, description=description,
        started_at=now, ends_at=now + timedelta(hours=duration_hours),
    )
    db.add(event)
    return event


def get_active_events(db, mode, location, now):
    """Return active environmental events at a location."""
    return db.query(EnvironmentEvent).filter(
        EnvironmentEvent.mode == mode,
        EnvironmentEvent.location == location,
        EnvironmentEvent.started_at <= now,
        EnvironmentEvent.ends_at >= now,
    ).all()


def get_active_events_for_route(db, mode, locations, now):
    """Return active events affecting any of the given route locations."""
    if not locations:
        return []
    return db.query(EnvironmentEvent).filter(
        EnvironmentEvent.mode == mode,
        EnvironmentEvent.location.in_(locations),
        EnvironmentEvent.started_at <= now,
        EnvironmentEvent.ends_at >= now,
    ).all()

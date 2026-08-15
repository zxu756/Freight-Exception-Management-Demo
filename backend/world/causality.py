"""
Causality engine - turns world state (weather) into domain events, and
propagates effects across transport modes.

Third pillar of the world core. Converts the deterministic world weather into
the EnvironmentEvents the three simulators already consume, so the causal chain
weather -> delay -> exception -> notification holds end to end.
"""
import time as _time
from datetime import timedelta

from environment_events import AIR_LOCATIONS, ROAD_LOCATIONS, SEA_LOCATIONS
from environment_models import EnvironmentEvent
from database import SessionLocal, WRITE_LOCK
from world.weather import weather_engine

LOCATIONS_BY_MODE = {"air": AIR_LOCATIONS, "road": ROAD_LOCATIONS, "sea": SEA_LOCATIONS}

# weather condition -> per-mode event_type (None = no operational event)
WEATHER_EVENT_TYPE = {
    "fog":        {"air": "fog", "road": "weather", "sea": None},
    "snow":       {"air": "snow", "road": "weather", "sea": None},
    "storm":      {"air": "weather", "road": "weather", "sea": "weather"},
    "heavy_rain": {"air": "weather", "road": "weather", "sea": "weather"},
    "rain":       {"air": "weather", "road": "weather", "sea": "weather"},
    "showers":    {"air": "weather", "road": "weather", "sea": None},
    "windy":      {"air": "weather", "road": None, "sea": "weather"},
}

# 天气类型 → 缓冲期（小时范围）：事件从"开始"到"实际影响班次"之间的预测窗口。
# 雪需要累积、大雨需要积水，缓冲较长；雾/阵雨来得快，缓冲较短。
WEATHER_BUFFER_HOURS = {
    "snow": (4.0, 12.0),
    "heavy_rain": (3.0, 8.0),
    "storm": (2.0, 6.0),
    "rain": (1.0, 3.0),
    "showers": (1.0, 2.0),
    "windy": (1.0, 3.0),
    "fog": (1.0, 3.0),
}


def weather_buffer_hours(condition, intensity):
    """缓冲期时长：强度越高，达到影响阈值越快（缓冲越短）。"""
    lo, hi = WEATHER_BUFFER_HOURS.get(condition, (0.0, 0.0))
    if lo == 0.0 and hi == 0.0:
        return 0.0
    span = hi - lo
    return round(lo + span * (1.0 - float(intensity)), 1)


# port code -> display city (for human-readable sea descriptions)
PORT_CITY = {"NZAKL": "奥克兰", "NZTRG": "陶朗加", "NZWLG": "惠灵顿", "NZLYT": "利特尔顿", "NZTIU": "提马鲁"}
# port code -> connecting road city code (for sea->road drayage propagation)
PORT_TO_ROAD_CITY = {"NZAKL": "AKL", "NZTRG": "TRG", "NZWLG": "WLG", "NZLYT": "CHC", "NZTIU": "TIM"}


def build_description(mode, loc, weather):
    cond = weather["condition"]
    label = weather["condition_label"]
    vis = weather["visibility_km"]
    wind = weather["wind_knots"]
    if mode == "air":
        if cond == "fog":
            return f"{loc} 机场大雾，能见度仅 {vis}km，低于起降标准"
        if cond == "snow":
            return f"{loc} 机场降雪，跑道清理中"
        if cond in ("storm", "heavy_rain", "rain", "showers"):
            return f"{loc} 机场{label}，航班起降受限"
        if cond == "windy":
            return f"{loc} 机场大风 {wind}kt，航班起降受限"
    if mode == "road":
        if cond == "fog":
            return f"{loc} 大雾，能见度 {vis}km，通行缓慢"
        if cond == "snow":
            return f"{loc} 降雪，道路湿滑需减速"
        if cond in ("storm", "heavy_rain"):
            return f"{loc} {label}，道路通行受阻"
        if cond in ("rain", "showers"):
            return f"{loc} {label}，通行缓慢"
    if mode == "sea":
        city = PORT_CITY.get(loc, loc)
        if cond in ("storm", "windy"):
            return f"{city}港区大风 {wind}kt，船舶靠泊暂停"
        if cond == "heavy_rain":
            return f"{city}港区大雨，作业放缓"
        if cond == "rain":
            return f"{city}港区降雨，作业放缓"
    return f"{loc} {label}"


def weather_events_for_mode(db, mode, now, active_events=None):
    active_events = active_events or {}
    events = []
    for loc in LOCATIONS_BY_MODE[mode]:
        w = weather_engine.weather_at(db, loc, now)
        impact = weather_engine.impact_for_mode(mode, w)
        if impact["level"] == "clear":
            continue
        ev_type = WEATHER_EVENT_TYPE.get(w["condition"], {}).get(mode)
        if not ev_type:
            continue
        existing = active_events.get(loc, [])
        if any(e["event_type"] == ev_type and e["ends_at"] >= now for e in existing):
            continue
        severity = "severe" if impact["level"] == "severe" else "moderate"
        buffer_h = weather_buffer_hours(w["condition"], w["intensity"])
        active_h = max(4, int(round(w["intensity"] * 16)))  # 影响持续期
        impact_at = now + timedelta(hours=buffer_h)
        event = EnvironmentEvent(
            event_type=ev_type, mode=mode, location=loc,
            severity=severity, description=build_description(mode, loc, w),
            started_at=now, ends_at=impact_at + timedelta(hours=active_h),
            impact_at=impact_at,
        )
        events.append((loc, event))
    return events


_last_predict_real = 0.0


def propagate_world(now):
    global _last_predict_real
    with WRITE_LOCK:
        db = SessionLocal()
        try:
            # 预测引擎：每 10 真实秒运行一次（降低写锁竞争，又足够及时）
            if _time.monotonic() - _last_predict_real >= 10.0:
                from world.predict import predict_impacts, cleanup_predictions
                predict_impacts(db, now)
                cleanup_predictions(db, now)
                db.commit()
                _last_predict_real = _time.monotonic()

            # 跨模式：港口严重天气（已过缓冲期）→ 陆运集疏运
            active = db.query(EnvironmentEvent).filter(
                EnvironmentEvent.mode == "sea",
                EnvironmentEvent.started_at <= now,
                EnvironmentEvent.ends_at >= now,
                EnvironmentEvent.impact_at <= now,
                EnvironmentEvent.severity == "severe",
            ).all()
            if not active:
                return
            from road_freight_simulator import simulator as road_sim
            for ev in active:
                city = PORT_TO_ROAD_CITY.get(ev.location)
                if not city:
                    continue
                existing = road_sim._active_events.get(city, [])
                if any(e["event_type"] == "weather" and e["ends_at"] >= now for e in existing):
                    continue
                road_sim._active_events.setdefault(city, []).append({
                    "event_type": "weather", "severity": "moderate",
                    "description": f"{PORT_CITY.get(ev.location, ev.location)}港受天气影响，{city} 集疏运公路通行放缓",
                    "ends_at": ev.ends_at,
                    "impact_at": now,
                })
            road_sim._update_road_conditions(db)
        finally:
            db.close()


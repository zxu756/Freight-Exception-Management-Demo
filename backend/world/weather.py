"""
World Weather Engine - regional, evolving, god-controllable weather.

The second pillar of the world-simulation core. Weather is a *deterministic*
function of (sim time, region): same sim time + region -> same weather, so it is
replay-friendly and needs no driver thread - it simply follows the WorldClock.

God overrides ("make Queenstown foggy") are persisted in the weather_overrides
table and layered on top of the base weather.

Medium granularity: one weather state per NZ region. Every city/airport/depot/
port code resolves to a region, and location-level overrides are supported.
"""
import math
import random
import zlib
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime

from database import Base

# ---------------------------------------------------------------------------
# Canonical conditions + Chinese labels (UI uses these)
# ---------------------------------------------------------------------------
CONDITIONS = ["clear", "cloudy", "showers", "rain", "heavy_rain", "storm", "fog", "snow", "windy"]

CONDITION_LABELS = {
    "clear": "晴", "cloudy": "多云", "showers": "阵雨", "rain": "雨",
    "heavy_rain": "大雨", "storm": "暴风雨", "fog": "大雾", "snow": "降雪", "windy": "大风",
}

# ---------------------------------------------------------------------------
# Regions: name -> climate profile.
# weights: base probability of each condition; temp: (winter_min, summer_max) C;
# wind_base: typical wind in knots.
# ---------------------------------------------------------------------------
REGIONS = {
    "northland":      {"name": "Northland",            "cities": ["WHA"],                        "weights": {"clear": .30, "cloudy": .28, "showers": .25, "rain": .12, "heavy_rain": .03, "storm": .02}, "temp": (10, 24), "wind_base": 10},
    "auckland":       {"name": "Auckland",             "cities": ["AKL"],                        "weights": {"clear": .30, "cloudy": .30, "showers": .25, "rain": .10, "heavy_rain": .03, "storm": .02}, "temp": (9, 23),  "wind_base": 10},
    "waikato":        {"name": "Waikato",              "cities": ["HLZ", "TAI"],                 "weights": {"clear": .28, "cloudy": .28, "showers": .22, "rain": .10, "fog": .10, "heavy_rain": .02}, "temp": (6, 24),  "wind_base": 9},
    "bay_of_plenty":  {"name": "Bay of Plenty",        "cities": ["TRG", "ROT"],                 "weights": {"clear": .40, "cloudy": .30, "showers": .20, "rain": .07, "storm": .02, "heavy_rain": .01}, "temp": (7, 24),  "wind_base": 9},
    "gisborne":       {"name": "Gisborne",             "cities": ["GIS"],                        "weights": {"clear": .40, "cloudy": .30, "showers": .18, "rain": .10, "heavy_rain": .02}, "temp": (6, 24),  "wind_base": 9},
    "hawkes_bay":     {"name": "Hawke's Bay",          "cities": ["NPE"],                        "weights": {"clear": .42, "cloudy": .28, "showers": .18, "rain": .10, "heavy_rain": .02}, "temp": (5, 25),  "wind_base": 9},
    "taranaki":       {"name": "Taranaki",             "cities": ["NPL"],                        "weights": {"clear": .20, "cloudy": .25, "showers": .30, "rain": .15, "heavy_rain": .06, "storm": .03, "windy": .01}, "temp": (7, 21),  "wind_base": 14},
    "manawatu":       {"name": "Manawatu",             "cities": ["PMR"],                        "weights": {"clear": .25, "cloudy": .28, "showers": .25, "rain": .12, "windy": .05, "storm": .03, "heavy_rain": .02}, "temp": (6, 22),  "wind_base": 14},
    "wellington":     {"name": "Wellington",           "cities": ["WLG"],                        "weights": {"clear": .20, "cloudy": .25, "showers": .25, "rain": .12, "windy": .12, "storm": .04, "heavy_rain": .02}, "temp": (7, 20),  "wind_base": 22},
    "top_of_south":   {"name": "Nelson / Marlborough", "cities": ["PIC", "BLH", "NSN"],          "weights": {"clear": .40, "cloudy": .30, "showers": .18, "rain": .10, "heavy_rain": .02}, "temp": (5, 23),  "wind_base": 10},
    "west_coast":     {"name": "West Coast",           "cities": ["GBM"],                        "weights": {"clear": .10, "cloudy": .20, "showers": .30, "rain": .20, "heavy_rain": .12, "storm": .08}, "temp": (5, 19),  "wind_base": 12},
    "canterbury":     {"name": "Canterbury",           "cities": ["CHC", "TIM", "OAM"],          "weights": {"clear": .32, "cloudy": .28, "showers": .18, "rain": .12, "fog": .04, "snow": .02, "heavy_rain": .02, "storm": .02}, "temp": (2, 23),  "wind_base": 12},
    "central_otago":  {"name": "Central Otago",        "cities": ["ZQN"],                        "weights": {"clear": .30, "cloudy": .22, "showers": .12, "rain": .06, "fog": .12, "snow": .14, "heavy_rain": .02, "storm": .02}, "temp": (-2, 22), "wind_base": 8},
    "otago":          {"name": "Otago",                "cities": ["DUD"],                        "weights": {"clear": .28, "cloudy": .28, "showers": .20, "rain": .14, "snow": .04, "fog": .04, "heavy_rain": .02}, "temp": (3, 20),  "wind_base": 10},
    "southland":      {"name": "Southland",            "cities": ["IVC"],                        "weights": {"clear": .22, "cloudy": .28, "showers": .25, "rain": .15, "snow": .04, "heavy_rain": .04, "storm": .02}, "temp": (2, 19),  "wind_base": 12},
}

# city/airport/depot code -> region
LOCATION_REGION = {}
for _region, _profile in REGIONS.items():
    for _c in _profile["cities"]:
        LOCATION_REGION[_c] = _region

# port code -> region
PORT_REGION = {
    "NZAKL": "auckland",
    "NZTRG": "bay_of_plenty",
    "NZWLG": "wellington",
    "NZLYT": "canterbury",   # Lyttelton serves Christchurch
    "NZTIU": "canterbury",   # Timaru
}


def region_of(code: str) -> str:
    """Resolve any location code (city/airport/depot/port) to its region slug."""
    if code in LOCATION_REGION:
        return LOCATION_REGION[code]
    if code in PORT_REGION:
        return PORT_REGION[code]
    return "auckland"  # safe default


# ---------------------------------------------------------------------------
# Persisted god overrides
# ---------------------------------------------------------------------------
class WeatherOverride(Base):
    __tablename__ = "weather_overrides"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(10), nullable=False)   # 'region' | 'location'
    target = Column(String(20), nullable=False, index=True)
    condition = Column(String(20), nullable=False)
    intensity = Column(Float, nullable=False, default=1.0)
    started_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)


# ---------------------------------------------------------------------------
# Deterministic weather engine
# ---------------------------------------------------------------------------
CONDITION_TEMP_OFFSET = {
    "clear": 2.0, "cloudy": 1.0, "showers": 0.0, "rain": -1.0, "heavy_rain": -2.0,
    "storm": -3.0, "fog": 0.0, "snow": -4.0, "windy": 0.0,
}
CONDITION_WIND_OFFSET = {
    "clear": 0, "cloudy": 2, "showers": 5, "rain": 8, "heavy_rain": 12,
    "storm": 25, "fog": 0, "snow": 5, "windy": 20,
}
CONDITION_VISIBILITY_KM = {
    "clear": 40.0, "cloudy": 35.0, "showers": 15.0, "rain": 8.0, "heavy_rain": 3.0,
    "storm": 2.0, "fog": 0.4, "snow": 1.0, "windy": 25.0,
}
CONDITION_PRECIP_MMH = {
    "clear": 0.0, "cloudy": 0.0, "showers": 0.6, "rain": 2.0, "heavy_rain": 8.0,
    "storm": 12.0, "fog": 0.0, "snow": 3.0, "windy": 0.0,
}


class WeatherEngine:
    """Deterministic regional weather model + god overrides."""

    EPOCH = datetime(2026, 8, 1, 0, 0, 0)

    def __init__(self):
        self._episode_cache = {}  # region -> [ {condition,intensity,start_hour,end_hour} ]

    # -- region / location resolution -------------------------
    def region_of(self, code):
        return region_of(code)

    def all_regions(self):
        return list(REGIONS.keys())

    def all_locations(self):
        codes = list(LOCATION_REGION.keys()) + list(PORT_REGION.keys())
        return codes

    # -- deterministic episode walk ---------------------------
    @staticmethod
    def _seed(region):
        return zlib.crc32(region.encode("utf-8"))

    @staticmethod
    def _weighted(rng, weights):
        items = list(weights.items())
        total = sum(w for _, w in items)
        r = rng.random() * total
        acc = 0.0
        for cond, w in items:
            acc += w
            if r <= acc:
                return cond
        return items[-1][0]

    def _episodes(self, region, max_hour):
        cached = self._episode_cache.get(region)
        if cached and cached[-1]["end_hour"] >= max_hour:
            return cached

        profile = REGIONS[region]
        rng = random.Random(self._seed(region))
        episodes = []
        hour = 0
        cond = self._weighted(rng, profile["weights"])
        while hour < max_hour:
            dur = rng.randint(4, 48)
            intensity = round(rng.uniform(0.35, 1.0), 2)
            episodes.append({"condition": cond, "intensity": intensity, "start_hour": hour, "end_hour": hour + dur})
            hour += dur
            # persistence: ~50% chance the next episode keeps the same condition
            if rng.random() >= 0.5:
                cond = self._weighted(rng, profile["weights"])
        self._episode_cache[region] = episodes
        return episodes

    def _base_condition(self, region, now):
        hour_index = int((now - self.EPOCH).total_seconds() // 3600)
        eps = self._episodes(region, max(hour_index, 1))
        for e in eps:
            if e["start_hour"] <= hour_index < e["end_hour"]:
                return e["condition"], e["intensity"]
        return "clear", 1.0

    def _temperature(self, region, condition, now):
        wmin, wmax = REGIONS[region]["temp"]
        # seasonal: peak summer ~Feb (month 2), peak winter ~Aug (month 8)
        seasonal = math.cos(2 * math.pi * (now.month - 2) / 12.0)
        base = (wmin + wmax) / 2.0 + (wmax - wmin) / 2.0 * (0.5 + 0.5 * seasonal)
        # mild diurnal swing: warmest ~14:00, coolest ~02:00
        diurnal = 3.0 * math.cos(2 * math.pi * (now.hour - 14) / 24.0)
        return round(base + diurnal + CONDITION_TEMP_OFFSET.get(condition, 0.0), 1)

    # -- derived weather dict ---------------------------------
    def _weather_dict(self, code, region, condition, intensity, now, overridden=False):
        return {
            "code": code,
            "region": region,
            "region_name": REGIONS[region]["name"],
            "condition": condition,
            "condition_label": CONDITION_LABELS.get(condition, condition),
            "intensity": intensity,
            "temperature_c": self._temperature(region, condition, now),
            "wind_knots": round(REGIONS[region]["wind_base"] + CONDITION_WIND_OFFSET.get(condition, 0) * intensity, 1),
            "visibility_km": round(CONDITION_VISIBILITY_KM.get(condition, 30.0) * (1.0 if condition != "fog" else 1.0), 1),
            "precip_mm_per_h": round(CONDITION_PRECIP_MMH.get(condition, 0.0) * intensity, 2),
            "overridden": overridden,
        }

    # -- public API -------------------------------------------
    def weather_at(self, db, code, now):
        """Resolved weather for a location code (city/airport/depot/port)."""
        region = region_of(code)
        # location-level override wins over region-level
        if db is not None:
            ov = self._active_override(db, "location", code, now) or self._active_override(db, "region", region, now)
            if ov:
                return self._weather_dict(code, region, ov.condition, ov.intensity, now, overridden=True)
        cond, intensity = self._base_condition(region, now)
        return self._weather_dict(code, region, cond, intensity, now)

    def overview(self, db, now):
        """One weather snapshot for every region + every location."""
        regions = []
        for region in REGIONS:
            cond, intensity = self._base_condition(region, now)
            ov = self._active_override(db, "region", region, now) if db else None
            if ov:
                cond, intensity = ov.condition, ov.intensity
            regions.append(self._weather_dict(region, region, cond, intensity, now, overridden=bool(ov)))

        locations = [self.weather_at(db, code, now) for code in self.all_locations()]
        return {"now": now.isoformat(), "regions": regions, "locations": locations}

    # -- god overrides ----------------------------------------
    @staticmethod
    def _active_override(db, target_type, target, now):
        return (db.query(WeatherOverride)
                .filter(WeatherOverride.target_type == target_type,
                        WeatherOverride.target == target,
                        WeatherOverride.started_at <= now,
                        WeatherOverride.ends_at >= now)
                .order_by(WeatherOverride.id.desc())
                .first())

    def set_override(self, db, target, condition, intensity, hours, now):
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition: {condition}")
        target_type = "region" if target in REGIONS else "location"
        from datetime import timedelta
        ov = WeatherOverride(
            target_type=target_type,
            target=target,
            condition=condition,
            intensity=float(intensity),
            started_at=now,
            ends_at=now + timedelta(hours=float(hours)),
        )
        db.add(ov)
        db.commit()
        return ov

    def list_overrides(self, db, now):
        rows = db.query(WeatherOverride).filter(
            WeatherOverride.ends_at >= now,
        ).order_by(WeatherOverride.id.desc()).all()
        return [
            {
                "target_type": r.target_type, "target": r.target,
                "condition": r.condition, "condition_label": CONDITION_LABELS.get(r.condition, r.condition),
                "intensity": r.intensity,
                "ends_at": r.ends_at.isoformat(),
            }
            for r in rows
        ]

    def clear_overrides(self, db, target=None):
        q = db.query(WeatherOverride)
        if target:
            q = q.filter(WeatherOverride.target == target)
        n = q.delete()
        db.commit()
        return n

    # -- operational impact (bridge to the causality engine) --
    def impact_for_mode(self, mode, weather):
        """Return how current weather impacts a transport mode.

        level: 'clear' | 'caution' | 'severe'  (phase 3 wires these into delays)
        """
        cond = weather["condition"]
        if mode == "air":
            if cond == "fog":
                return {"level": "severe", "reason": "低能见度，航班起降受限"}
            if cond in ("snow", "storm"):
                return {"level": "severe", "reason": "恶劣天气，航班延误/取消"}
            if cond in ("heavy_rain", "windy"):
                return {"level": "caution", "reason": "天气影响，航班可能延误"}
        elif mode == "road":
            if cond == "storm":
                return {"level": "severe", "reason": "暴雨，道路通行受阻"}
            if cond == "snow":
                return {"level": "severe", "reason": "降雪，道路湿滑需减速"}
            if cond in ("heavy_rain", "fog"):
                return {"level": "caution", "reason": "天气影响，通行缓慢"}
        elif mode == "sea":
            if cond in ("storm", "windy"):
                return {"level": "severe", "reason": "大风，船舶靠泊暂停"}
            if cond == "heavy_rain":
                return {"level": "caution", "reason": "港区大雨，作业放缓"}
        elif mode == "rail":
            if cond in ("storm", "heavy_rain", "snow"):
                return {"level": "severe", "reason": "恶劣天气，线路封闭风险，班列停运/绕行"}
            if cond in ("rain", "windy", "fog"):
                return {"level": "caution", "reason": "天气影响，班列限速运行"}
        return {"level": "clear", "reason": "天气正常"}


# Singleton used across the backend.
weather_engine = WeatherEngine()

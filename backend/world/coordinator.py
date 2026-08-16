"""
World Simulator coordinator - one thread drives all three domain engines in
lock-step on the shared world clock, then runs cross-domain propagation.

This is the single tick loop of the digital twin. Each tick:
  1. read the world clock once,
  2. apply that same instant to every engine's sim_now and tick them,
  3. run cross-domain causality propagation.
"""
import threading
import time
from datetime import timedelta

from config import settings
from world.clock import world_clock

TICK_SECONDS = 5.0
MAINTENANCE_INTERVAL = timedelta(hours=12)  # 每 12 模拟小时刷新一次绩效/指标快照


class WorldSimulator:
    """Single-threaded coordinator over the air/road/sea engines."""

    def __init__(self):
        self.clock = world_clock
        self.engines = []
        self.running = False
        self._stop_event = threading.Event()
        self._thread = None
        self._last_maintenance = None

    def start(self):
        if self.running:
            return
        from air_cargo_simulator import simulator as air
        from road_freight_simulator import simulator as road
        from sea_freight_simulator import simulator as sea

        self.engines = []
        if settings.air_sim_enabled:
            air.start()
            self.engines.append(air)
        if settings.road_sim_enabled:
            road.start()
            self.engines.append(road)
        if settings.sea_sim_enabled:
            sea.start()
            self.engines.append(sea)

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="world-sim", daemon=True)
        self._thread.start()
        print(f"[world] coordinator started with {len(self.engines)} engines")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        for e in self.engines:
            e.stop()
        print("[world] coordinator stopped")

    def _run(self):
        while not self._stop_event.is_set():
            t0 = time.monotonic()
            if not self.clock.paused:
                now = self.clock.now
                for e in self.engines:
                    e.sim_now = now
                    try:
                        e.tick()
                    except Exception as ex:
                        print(f"[world] {type(e).__name__} tick error: {ex}")
                try:
                    self.propagate(now)
                except Exception as ex:
                    print(f"[world] propagate error: {ex}")
                # 定期维护：承运人绩效、历史风险预测、KPI 指标快照（P1/P2）
                if self._last_maintenance is None or now - self._last_maintenance >= MAINTENANCE_INTERVAL:
                    try:
                        from database import SessionLocal
                        from world.maintenance import maintenance
                        _db = SessionLocal()
                        try:
                            maintenance(_db, now)
                        finally:
                            _db.close()
                        self._last_maintenance = now
                    except Exception as ex:
                        print(f"[world] maintenance error: {ex}")
            time.sleep(max(0.1, TICK_SECONDS - (time.monotonic() - t0)))

    def propagate(self, now):
        """Cross-domain causality (sea->road, etc.)."""
        from world.causality import propagate_world
        propagate_world(now)


# Singleton used by main.py.
world_sim = WorldSimulator()

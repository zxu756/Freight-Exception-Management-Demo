"""
World Clock - the single time authority for the simulated New Zealand.

All three domain engines (air/road/sea) read time from this clock so the whole
world advances in lock-step. Speed, pause state and the current simulation time
all live here (one world, one clock).

Persistence: the world clock's now and speed are saved to the world_meta table,
so the digital twin *resumes* from where it left off across restarts (like a
persistent game world) instead of resetting to real time.
"""
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy import Column, String, DateTime

from database import Base, SessionLocal, WRITE_LOCK


class WorldMeta(Base):
    """Simple key-value store for world-level state (clock persistence)."""
    __tablename__ = "world_meta"

    key = Column(String(50), primary_key=True)
    value = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class WorldClock:
    """Single global simulation clock. One thread advances time; everyone reads it."""

    def __init__(self, speed: float = 60.0, tick_seconds: float = 5.0):
        self._now = datetime.utcnow().replace(microsecond=0)
        self._speed = float(speed)
        self._paused = False
        self._tick_seconds = tick_seconds
        self._persist_interval = 30.0  # real seconds between DB saves
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._last_real = time.monotonic()
        self._last_persist = time.monotonic()

    # ----------------------------------------------------------
    # Time
    # ----------------------------------------------------------
    @property
    def now(self) -> datetime:
        with self._lock:
            return self._now

    def set_now(self, dt: datetime):
        """God-mode: jump the world clock to an arbitrary time (and persist it)."""
        with self._lock:
            self._now = dt.replace(microsecond=0)
        self._persist()

    # ----------------------------------------------------------
    # Speed / pause (single shared state for every mode)
    # ----------------------------------------------------------
    @property
    def speed(self) -> float:
        with self._lock:
            return self._speed

    def set_speed(self, speed: float):
        with self._lock:
            self._speed = max(0.0, min(float(speed), 3600.0))
        self._persist()

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    @paused.setter
    def paused(self, value: bool):
        with self._lock:
            self._paused = bool(value)
            if not self._paused:
                # resume: reset the wall-clock anchor so we don't jump forward
                self._last_real = time.monotonic()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    # ----------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------
    def _restore(self):
        """Load persisted clock state (now + speed) on startup, if present."""
        try:
            db = SessionLocal()
            try:
                rows = {m.key: m.value for m in db.query(WorldMeta).all()}
            finally:
                db.close()
            if "clock_now" in rows:
                self._now = datetime.fromisoformat(rows["clock_now"]).replace(microsecond=0)
            if "clock_speed" in rows:
                self._speed = max(0.0, min(float(rows["clock_speed"]), 3600.0))
        except Exception as e:
            print(f"[clock] restore skipped: {e}")

    def _persist(self):
        """Save clock state (now + speed) to the DB.

        Uses a short, independent transaction (no WRITE_LOCK) so a god-mode
        control request never blocks behind the simulators' tick loop - SQLite's
        busy_timeout handles brief write contention, and we retry on failure so
        the clock survives restarts even under high load.
        """
        for attempt in range(3):
            try:
                db = SessionLocal()
                try:
                    for key, val in (("clock_now", self._now.isoformat()), ("clock_speed", str(self._speed))):
                        row = db.query(WorldMeta).filter(WorldMeta.key == key).first()
                        if row:
                            row.value = val
                            row.updated_at = datetime.utcnow()
                        else:
                            db.add(WorldMeta(key=key, value=val))
                    db.commit()
                finally:
                    db.close()
                return
            except Exception as e:
                if attempt == 2:
                    print(f"[clock] persist failed: {e}")
                time.sleep(1.0)

    def _align_to_data(self):
        """Startup: align the clock to the latest data timestamp in the DB.

        If the persisted clock is behind the data (e.g. a persist was lost under
        load), backfill would re-generate overlapping records and crawl. Aligning
        the clock just past the newest data keeps restarts fast and coherent.
        """
        try:
            from sqlalchemy import text
            db = SessionLocal()
            try:
                latest = None
                for table, col in (("air_flights", "scheduled_departure"),
                                   ("road_trips", "scheduled_departure"),
                                   ("sea_containers", "scheduled_delivery")):
                    try:
                        v = db.execute(text(f"SELECT MAX({col}) FROM {table}")).scalar()
                        if v and (latest is None or v > latest):
                            latest = v
                    except Exception:
                        pass
                if latest and self._now < latest:
                    self._now = latest + timedelta(hours=1)
                    print(f"[clock] aligned to data: {self._now.isoformat()}")
            finally:
                db.close()
        except Exception as e:
            print(f"[clock] align failed: {e}")

    # ----------------------------------------------------------
    # Driver thread
    # ----------------------------------------------------------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._restore()
        self._align_to_data()
        self._stop.clear()
        self._last_real = time.monotonic()
        self._last_persist = time.monotonic()
        self._thread = threading.Thread(target=self._run, name="world-clock", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._persist()

    def _run(self):
        while not self._stop.is_set():
            t0 = time.monotonic()
            with self._lock:
                if not self._paused:
                    now_real = time.monotonic()
                    self._now += timedelta(seconds=(now_real - self._last_real) * self._speed)
                    self._last_real = now_real
                else:
                    self._last_real = time.monotonic()
            # periodic persistence (outside the lock)
            if time.monotonic() - self._last_persist > self._persist_interval:
                self._persist()
                self._last_persist = time.monotonic()
            time.sleep(max(0.1, self._tick_seconds - (time.monotonic() - t0)))


# Singleton - the one world clock used across the whole backend.
world_clock = WorldClock()

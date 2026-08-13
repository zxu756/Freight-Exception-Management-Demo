"""
Dwell-time anomaly detection - flags shipment/container dwell times that are
statistically abnormal relative to recent history.

停留时间异常检测 - 标记相对近期历史统计上异常的货物/集装箱停留时间

Statistical baseline approach: for each milestone transition (e.g. container
DIS -> AVC), maintain a sliding window of recent dwell times. When a new dwell
time exceeds the P95 of recent history (or mean + 3 sigma), flag it as a
predicted anomaly. This is the "predict exceptions before they occur" baseline
from Scenario 4, using a simple, explainable statistic instead of a black-box
model.
"""
import threading
from collections import deque

import numpy as np

MIN_HISTORY = 20   # need at least this many observations before flagging
WINDOW = 300       # sliding window size per (mode, transition)
PCT = 95           # percentile threshold


class DwellTimeAnomalyDetector:
    """Tracks dwell-time distributions per (mode, transition) and flags outliers."""

    def __init__(self, window=WINDOW, pct=PCT, min_history=MIN_HISTORY):
        self.window = window
        self.pct = pct
        self.min_history = min_history
        self._history = {}
        self._lock = threading.Lock()

    def observe(self, mode, transition, dwell_hours):
        """
        Record a dwell time and flag it if it is statistically abnormal.

        Args:
            mode: 'sea', 'air' or 'road'
            transition: e.g. 'DIS_AVC'
            dwell_hours: dwell time in hours

        Returns:
            dict with anomaly_score + anomaly_reason if abnormal, else None
        """
        if dwell_hours is None or dwell_hours < 0:
            return None
        with self._lock:
            hist = self._history.setdefault((mode, transition), deque(maxlen=self.window))
            anomaly = None
            if len(hist) >= self.min_history:
                values = list(hist)
                p95 = float(np.percentile(values, self.pct))
                mean = float(np.mean(values))
                std = float(np.std(values))
                threshold = max(p95, mean + 3 * std, 1e-6)
                if dwell_hours > threshold:
                    anomaly = {
                        "anomaly_score": round(dwell_hours / threshold, 3),
                        "anomaly_reason": f"dwell_{transition}_exceeded_p{self.pct}",
                    }
            hist.append(dwell_hours)
            return anomaly

    def stats(self):
        """Return the number of tracked (mode, transition) distributions."""
        with self._lock:
            return {f"{m}_{t}": len(h) for (m, t), h in self._history.items()}


# 全局单例
detector = DwellTimeAnomalyDetector()

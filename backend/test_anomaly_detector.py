"""
Unit tests for the dwell-time anomaly detector.
停留时间异常检测单元测试
"""
from anomaly_detector import DwellTimeAnomalyDetector


def test_no_flag_before_min_history():
    """No anomaly is flagged until enough history has accumulated."""
    d = DwellTimeAnomalyDetector()
    for _ in range(5):
        assert d.observe("sea", "DIS_AVC", 1.0) is None
    assert d.observe("sea", "DIS_AVC", 10.0) is None  # below min_history


def test_flags_outlier_after_enough_history():
    """A dwell time far above recent history is flagged."""
    d = DwellTimeAnomalyDetector()
    for i in range(30):
        assert d.observe("sea", "DIS_AVC", 1.0 + (i % 10) * 0.1) is None
    anomaly = d.observe("sea", "DIS_AVC", 10.0)
    assert anomaly is not None
    assert anomaly["anomaly_score"] > 1.0
    assert "DIS_AVC" in anomaly["anomaly_reason"]


def test_normal_values_not_flagged():
    """Dwell times within the normal range are not flagged."""
    d = DwellTimeAnomalyDetector()
    for i in range(30):
        d.observe("road", "DEP_ARR", 5.0 + (i % 5) * 0.2)
    assert d.observe("road", "DEP_ARR", 5.5) is None


def test_mode_transition_isolation():
    """Different (mode, transition) distributions are tracked independently."""
    d = DwellTimeAnomalyDetector()
    for i in range(30):
        d.observe("sea", "DIS_AVC", 1.0)
    # A large value on a different transition has no history -> not flagged
    assert d.observe("road", "DEP_ARR", 10.0) is None


def test_stats_tracks_distributions():
    d = DwellTimeAnomalyDetector()
    for _ in range(5):
        d.observe("sea", "DIS_AVC", 1.0)
    stats = d.stats()
    assert "sea_DIS_AVC" in stats
    assert stats["sea_DIS_AVC"] == 5

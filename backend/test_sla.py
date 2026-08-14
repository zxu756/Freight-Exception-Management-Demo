"""
Unit tests for SLA policy model and breach determination.
SLA 策略与违约判定单元测试
"""
from datetime import datetime, timedelta

from sla_models import (
    get_policy, determine_breach, evaluate_breach, get_priority,
    map_service_level_to_tier, is_excused, estimate_penalty,
)


def test_get_policy_returns_commitment():
    p = get_policy("sea", "priority")
    assert p["transit_hours"] == 60
    assert p["grace_hours"] == 1
    assert p["penalty_pct"] == 0.05


def test_get_policy_falls_back_to_standard():
    p = get_policy("sea", "unknown")
    assert p["transit_hours"] == 120  # standard fallback


def test_evaluate_breach_on_time():
    dl = datetime(2026, 8, 13, 18, 0)
    assert evaluate_breach(dl - timedelta(hours=2), dl, 2, 0.05, 10000) == (False, None, None)


def test_evaluate_breach_within_grace():
    dl = datetime(2026, 8, 13, 18, 0)
    assert evaluate_breach(dl + timedelta(hours=1), dl, 2, 0.05, 10000) == (False, None, None)


def test_evaluate_breach_formal():
    dl = datetime(2026, 8, 13, 18, 0)
    is_b, btype, penalty = evaluate_breach(dl + timedelta(hours=5), dl, 2, 0.05, 10000)
    assert is_b is True
    assert btype == "unexcused"
    assert penalty == 500.0


def test_evaluate_breach_excused():
    dl = datetime(2026, 8, 13, 18, 0)
    assert evaluate_breach(dl + timedelta(hours=10), dl, 2, 0.05, 10000, excused=True) == (False, "excused", None)


def test_is_excused():
    assert is_excused("customs_hold", None) is True
    assert is_excused("delay", "weather") is True
    assert is_excused("delay", "mechanical") is False


def test_get_priority_promotion():
    assert get_priority("high", "VIP") == "P1"     # high -> P2, VIP promotes to P1
    assert get_priority("medium", "high") == "P2"  # medium -> P3, high promotes to P2
    assert get_priority("low", "low") == "P4"


def test_map_service_level():
    assert map_service_level_to_tier("express") == "priority"
    assert map_service_level_to_tier("same_day") == "priority"
    assert map_service_level_to_tier("standard") == "standard"
    assert map_service_level_to_tier("charter") == "economy"


def test_estimate_penalty():
    assert estimate_penalty(10000, 0.05) == 500.0
    assert estimate_penalty(None, 0.05) == 0.0

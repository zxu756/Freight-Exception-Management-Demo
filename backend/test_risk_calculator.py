"""
Unit tests for risk calculator module.
"""
import pytest
from datetime import datetime, timedelta
from risk_calculator import (
    calculate_risk_score,
    categorize_risk,
    calculate_sla_breach_hours,
    should_auto_resolve,
    should_escalate_to_team,
    calculate_severity
)


def test_calculate_risk_score_low():
    """Test low risk score calculation."""
    score = calculate_risk_score(
        cargo_value=2800,
        customer_tier='medium',
        sla_breach_hours=0,
        exception_type='delay'
    )
    assert score <= 30
    assert categorize_risk(score) == 'low'


def test_calculate_risk_score_medium():
    """Test medium risk score calculation."""
    score = calculate_risk_score(
        cargo_value=28000,
        customer_tier='high',
        sla_breach_hours=2,
        exception_type='delay'
    )
    assert 30 < score <= 60
    assert categorize_risk(score) == 'medium'


def test_calculate_risk_score_high():
    """Test high risk score calculation."""
    score = calculate_risk_score(
        cargo_value=185000,
        customer_tier='VIP',
        sla_breach_hours=0,
        exception_type='damage'
    )
    assert score > 60
    assert categorize_risk(score) == 'high'


def test_calculate_sla_breach_hours():
    """Test SLA breach calculation."""
    now = datetime.utcnow()
    sla_deadline = now + timedelta(hours=10)
    delayed_eta = now + timedelta(hours=12)

    breach_hours = calculate_sla_breach_hours(delayed_eta, sla_deadline)
    assert breach_hours == 2.0


def test_calculate_sla_breach_hours_within():
    """Test SLA breach calculation when within deadline."""
    now = datetime.utcnow()
    sla_deadline = now + timedelta(hours=10)
    delayed_eta = now + timedelta(hours=8)

    breach_hours = calculate_sla_breach_hours(delayed_eta, sla_deadline)
    assert breach_hours == -2.0


def test_should_auto_resolve_low_risk():
    """Test auto-resolve for low risk case."""
    result = should_auto_resolve(
        risk_level='low',
        exception_type='delay',
        cargo_value=2800,
        sla_breach_hours=-2,
        ai_confidence=0.98,
        estimated_cost=0
    )
    assert result is True


def test_should_auto_resolve_high_risk():
    """Test auto-resolve rejected for high risk."""
    result = should_auto_resolve(
        risk_level='high',
        exception_type='damage',
        cargo_value=185000,
        sla_breach_hours=0,
        ai_confidence=0.95,
        estimated_cost=0
    )
    assert result is False


def test_should_auto_resolve_with_cost():
    """Test auto-resolve rejected when costs involved."""
    result = should_auto_resolve(
        risk_level='low',
        exception_type='delay',
        cargo_value=2800,
        sla_breach_hours=-2,
        ai_confidence=0.98,
        estimated_cost=500
    )
    assert result is False


def test_should_escalate_to_team_damage():
    """Test team escalation for high-value damage."""
    result = should_escalate_to_team(
        risk_level='high',
        exception_type='damage',
        cargo_value=185000
    )
    assert result is True


def test_should_escalate_to_team_low_risk():
    """Test no team escalation for low risk."""
    result = should_escalate_to_team(
        risk_level='low',
        exception_type='delay',
        cargo_value=2800
    )
    assert result is False


def test_calculate_severity_low():
    """Test low severity calculation."""
    severity = calculate_severity(
        risk_score=20,
        sla_breach_hours=-2,
        exception_type='delay'
    )
    assert severity == 'low'


def test_calculate_severity_critical_damage():
    """Test critical severity for damage."""
    severity = calculate_severity(
        risk_score=75,
        sla_breach_hours=0,
        exception_type='damage'
    )
    assert severity == 'critical'


def test_calculate_severity_high():
    """Test high severity calculation."""
    severity = calculate_severity(
        risk_score=65,
        sla_breach_hours=15,
        exception_type='delay'
    )
    assert severity == 'high'

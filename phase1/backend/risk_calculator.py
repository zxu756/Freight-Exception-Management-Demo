"""
Risk scoring and categorization logic for freight exceptions.
"""
from datetime import datetime
from typing import Dict, Any


def calculate_risk_score(
    cargo_value: float,
    customer_tier: str,
    sla_breach_hours: float,
    exception_type: str,
    historical_patterns: Dict[str, Any] = None
) -> int:
    """
    Calculate risk score (0-100) based on multiple factors.

    Args:
        cargo_value: Value of the cargo in dollars
        customer_tier: Customer tier ('low', 'medium', 'high', 'VIP')
        sla_breach_hours: Hours of SLA breach (negative if within SLA)
        exception_type: Type of exception ('delay', 'damage', 'misroute', 'customs_hold')
        historical_patterns: Optional historical data

    Returns:
        Risk score from 0 to 100
    """
    score = 0

    # Cargo value component (0-30 points)
    if cargo_value < 5000:
        score += 0
    elif cargo_value < 20000:
        score += 10
    elif cargo_value < 50000:
        score += 20
    else:
        score += 30

    # Customer tier component (0-20 points)
    tier_scores = {
        'low': 0,
        'medium': 5,
        'high': 15,
        'VIP': 20
    }
    score += tier_scores.get(customer_tier, 0)

    # SLA impact component (0-30 points)
    if sla_breach_hours <= 0:  # No breach
        score += 0
    elif sla_breach_hours <= 4:  # Minor breach
        score += 10
    elif sla_breach_hours <= 12:  # Moderate breach
        score += 20
    else:  # Major breach
        score += 30

    # Exception type component (0-20 points)
    type_scores = {
        'delay': 5,
        'misroute': 10,
        'customs_hold': 15,
        'damage': 20
    }
    score += type_scores.get(exception_type, 0)

    return min(score, 100)  # Cap at 100


def categorize_risk(score: int) -> str:
    """
    Categorize risk level based on score.

    Args:
        score: Risk score (0-100)

    Returns:
        Risk level: 'low', 'medium', or 'high'
    """
    if score <= 30:
        return 'low'
    elif score <= 60:
        return 'medium'
    else:
        return 'high'


def calculate_sla_breach_hours(
    delayed_eta: datetime,
    sla_deadline: datetime
) -> float:
    """
    Calculate hours of SLA breach.

    Args:
        delayed_eta: New estimated time of arrival
        sla_deadline: SLA deadline

    Returns:
        Hours of breach (negative if within SLA)
    """
    delta = delayed_eta - sla_deadline
    return delta.total_seconds() / 3600


def should_auto_resolve(
    risk_level: str,
    exception_type: str,
    cargo_value: float,
    sla_breach_hours: float,
    ai_confidence: float,
    estimated_cost: float = 0
) -> bool:
    """
    Determine if an exception can be auto-resolved without human approval.

    Args:
        risk_level: Risk level ('low', 'medium', 'high')
        exception_type: Type of exception
        cargo_value: Value of cargo
        sla_breach_hours: Hours of SLA breach
        ai_confidence: AI diagnosis confidence (0-1)
        estimated_cost: Estimated cost of resolution

    Returns:
        True if can be auto-resolved, False otherwise
    """
    # Never auto-resolve high risk
    if risk_level == 'high':
        return False

    # Never auto-resolve if costs money
    if estimated_cost > 0:
        return False

    # Auto-resolve criteria for low risk
    if risk_level == 'low':
        criteria = [
            cargo_value < 5000,
            sla_breach_hours <= 0,  # Must be within SLA
            exception_type == 'delay',
            ai_confidence >= 0.95
        ]
        return all(criteria)

    # Medium risk: never auto-resolve
    return False


def should_escalate_to_team(
    risk_level: str,
    exception_type: str,
    cargo_value: float
) -> bool:
    """
    Determine if exception should be escalated to a team (not just one coordinator).

    Args:
        risk_level: Risk level
        exception_type: Type of exception
        cargo_value: Value of cargo

    Returns:
        True if should escalate to team, False otherwise
    """
    # Always escalate high-value cargo damage
    if exception_type == 'damage' and cargo_value > 100000:
        return True

    # Escalate high risk with very high value
    if risk_level == 'high' and cargo_value > 150000:
        return True

    return False


def calculate_severity(
    risk_score: int,
    sla_breach_hours: float,
    exception_type: str,
    is_dg: bool = False,
    temp_required: bool = False,
    perishable: bool = False,
) -> str:
    """
    Calculate severity level for exception.

    Args:
        risk_score: Risk score (0-100)
        sla_breach_hours: Hours of SLA breach
        exception_type: Type of exception
        is_dg: Dangerous goods cargo (safety exposure)
        temp_required: Temperature-controlled cargo (cold chain)
        perishable: Perishable cargo (spoilage risk)

    Returns:
        Severity: 'low', 'medium', 'high', or 'critical'
    """
    # 安全暴露：危险品 + 货损/延误/温度 → Critical
    if is_dg and exception_type in ("damage", "delay", "temp_excursion", "lost"):
        return 'critical'

    # 冷链/易腐 + 延误/货损/温度 → Critical（变质风险）
    if (temp_required or perishable) and exception_type in ("damage", "delay", "temp_excursion") and sla_breach_hours > 0:
        return 'critical'

    if exception_type == 'damage' and risk_score >= 70:
        return 'critical'

    if sla_breach_hours > 24 or risk_score >= 80:
        return 'critical'

    if sla_breach_hours > 12 or risk_score >= 60:
        return 'high'

    if sla_breach_hours > 0 or risk_score >= 30:
        return 'medium'

    return 'low'

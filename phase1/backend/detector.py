"""Simple rule-based exception detection."""
from datetime import datetime


EXCEPTION_TYPES = {
    "delay": {"base_risk": 30, "name": "Delay"},
    "damage": {"base_risk": 50, "name": "Damage"},
    "customs_hold": {"base_risk": 40, "name": "Customs Hold"},
    "misroute": {"base_risk": 45, "name": "Misroute"},
}

TIER_BONUS = {"VIP": 20, "high": 15, "medium": 10, "low": 5}


def calculate_risk_score(exception_type, customer_tier="medium", cargo_value=0):
    base = EXCEPTION_TYPES.get(exception_type, {}).get("base_risk", 30)
    score = base + TIER_BONUS.get(customer_tier, 0)
    if cargo_value > 50000:
        score += 20
    elif cargo_value > 20000:
        score += 15
    elif cargo_value > 5000:
        score += 10
    return min(score, 100)


def determine_severity(risk_score):
    if risk_score >= 80:
        return "critical"
    elif risk_score >= 60:
        return "high"
    elif risk_score >= 40:
        return "medium"
    return "low"


def detect_exceptions(container, events):
    exceptions = []
    
    if container.status == "at_port":
        arrival_events = [e for e in events if e.event_code == "ARR"]
        discharge_events = [e for e in events if e.event_code == "DIS"]
        
        if arrival_events and not discharge_events:
            last_arrival = max(arrival_events, key=lambda e: e.timestamp)
            hours = (datetime.utcnow() - last_arrival.timestamp).total_seconds() / 3600
            if hours > 4:
                exceptions.append({
                    "type": "delay",
                    "reason": f"Container at port for {int(hours)} hours without discharge",
                    "delay_hours": hours,
                })
    
    if container.status == "customs_hold":
        exceptions.append({"type": "customs_hold", "reason": "Held by customs"})
    
    return exceptions


def generate_diagnosis(exception_type, reason):
    diagnoses = {
        "delay": {"root_cause": "Port congestion or vessel delay", "confidence": 0.85, "action": "rebook_next_service"},
        "damage": {"root_cause": "Handling damage", "confidence": 0.75, "action": "inspection"},
        "customs_hold": {"root_cause": "Documentation issue", "confidence": 0.90, "action": "submit_documents"},
        "misroute": {"root_cause": "Sorting error", "confidence": 0.80, "action": "corrected_routing"},
    }
    d = diagnoses.get(exception_type, diagnoses["delay"])
    return {
        "root_cause": d["root_cause"],
        "confidence": d["confidence"],
        "recommended_action": d["action"],
        "explanation": f"Analysis indicates: {d['root_cause']}. Recommended: {d['action']}",
    }

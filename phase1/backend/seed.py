"""Seed data for Phase 1."""
import random
from datetime import datetime, timedelta
from database import SessionLocal
from models import Port, Vessel, Container, TrackingEvent, Exception, Notification, Employee


def seed_data():
    db = SessionLocal()
    
    # Check if already seeded
    if db.query(Port).count() > 0:
        db.close()
        return
    
    # Employees
    employees = [
        ("EMP-001", "Sarah Chen", "Operations Coordinator", "sarah.chen@southernfreight.co.nz", "Operations"),
        ("EMP-002", "James Wilson", "Senior Coordinator", "james.wilson@southernfreight.co.nz", "Operations"),
        ("EMP-003", "Emma Thompson", "Operations Manager", "emma.thompson@southernfreight.co.nz", "Management"),
        ("EMP-004", "Michael Brown", "Logistics Specialist", "michael.brown@southernfreight.co.nz", "Operations"),
    ]
    for eid, name, role, email, dept in employees:
        db.add(Employee(employee_id=eid, name=name, role=role, email=email, department=dept))
    
    # Ports
    ports = [
        ("NZAKL", "Auckland", "Auckland"),
        ("NZTRG", "Tauranga", "Tauranga"),
        ("NZWLG", "Wellington", "Wellington"),
        ("NZLYT", "Lyttelton", "Christchurch"),
    ]
    for code, name, city in ports:
        db.add(Port(port_code=code, name=name, city=city))
    
    # Vessels
    vessels = [
        ("VES-001", "MV Auckland Express", "Maersk"),
        ("VES-002", "MV Tauranga Star", "MSC"),
        ("VES-003", "MV Wellington Bay", "CMA CGM"),
    ]
    for vid, name, operator in vessels:
        db.add(Vessel(vessel_id=vid, vessel_name=name, operator=operator))
    
    # Customers
    customers = [
        ("Fonterra", "VIP"), ("Silver Fern Farms", "high"),
        ("Zespri International", "medium"), ("Mainfreight", "low"),
        ("Foodstuffs NZ", "medium"), ("Countdown", "high"),
    ]
    
    # Containers
    statuses = ["at_port", "at_port", "at_port", "customs_hold", "delivered"]
    for i in range(50):
        customer, tier = random.choice(customers)
        db.add(Container(
            container_number=f"MSCU{1000000 + i}",
            vessel_id=random.choice(["VES-001", "VES-002", "VES-003"]),
            port_code=random.choice(["NZAKL", "NZTRG", "NZWLG", "NZLYT"]),
            status=random.choice(statuses),
            customer_name=customer,
            customer_tier=tier,
            commodity_desc=f"General cargo #{i}",
            declared_value_nzd=random.randint(5000, 100000),
        ))
    
    db.commit()
    
    # Tracking events
    containers = db.query(Container).all()
    evt_counter = 1
    for container in containers:
        for j in range(random.randint(2, 4)):
            event_code = ["ARR", "DIS", "CST", "DEL"][j] if j < 4 else "ARR"
            db.add(TrackingEvent(
                event_id=f"EVT-{evt_counter:06d}",
                container_number=container.container_number,
                event_code=event_code,
                event_desc=f"Event {event_code}",
                location=container.port_code,
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                source="simulator",
            ))
            evt_counter += 1
    
    db.commit()
    
    # Exceptions (30% of containers)
    from detector import calculate_risk_score, determine_severity, generate_diagnosis
    exc_counter = 1
    for container in containers:
        if random.random() < 0.3:
            exc_type = random.choice(["delay", "damage", "customs_hold", "misroute"])
            risk_score = calculate_risk_score(exc_type, container.customer_tier, container.declared_value_nzd)
            severity = determine_severity(risk_score)
            diag = generate_diagnosis(exc_type, "Detected")
            
            db.add(Exception(
                exception_id=f"EXC-{exc_counter:06d}",
                container_number=container.container_number,
                exception_type=exc_type,
                severity=severity,
                risk_score=risk_score,
                status="detected",
                root_cause=diag["root_cause"],
                ai_diagnosis=diag["explanation"],
                ai_confidence=diag["confidence"],
                recommended_action=diag["recommended_action"],
                detected_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
            ))
            exc_counter += 1
    
    db.commit()
    db.close()
    print(f"Seeded: 4 ports, 3 vessels, 50 containers, {evt_counter-1} events, {exc_counter-1} exceptions")


if __name__ == "__main__":
    from database import engine, Base
    Base.metadata.create_all(bind=engine)
    seed_data()

"""
Database initialization script with seed data for three demo cases.
"""
from datetime import datetime, timedelta
from database import engine, Base, SessionLocal
from models import Shipment, Exception, Event, Decision, Notification
import json


def init_db():
    """Initialize database and create tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def seed_demo_data():
    """Seed database with three demo case scenarios."""
    db = SessionLocal()

    try:
        # Clear existing data
        print("Clearing existing data...")
        db.query(Notification).delete()
        db.query(Decision).delete()
        db.query(Event).delete()
        db.query(Exception).delete()
        db.query(Shipment).delete()
        db.commit()

        print("Seeding demo data...")

        # === CASE 1: Low Risk - Traffic Delay ===
        case1_shipment = Shipment(
            shipment_id="SF-2024-09001",
            customer_name="Paper Plus",
            customer_tier="medium",
            cargo_description="Office stationery",
            cargo_value=2800.00,
            origin="Auckland",
            destination="Hamilton",
            transport_mode="road",
            scheduled_pickup=datetime.utcnow() - timedelta(hours=16),
            scheduled_delivery=datetime.utcnow() + timedelta(hours=8),
            sla_deadline=datetime.utcnow() + timedelta(hours=20),
            sla_buffer_hours=12,
            current_status="in_transit",
            current_eta=datetime.utcnow() + timedelta(hours=8, minutes=45),
            vehicle_id="TRK-AKL-234",
            created_at=datetime.utcnow() - timedelta(hours=16)
        )
        db.add(case1_shipment)

        # === CASE 2: Medium Risk - Ferry Cancellation ===
        case2_shipment = Shipment(
            shipment_id="SF-2024-09002",
            customer_name="Countdown Supermarkets",
            customer_tier="high",
            cargo_description="Imported food packaging materials",
            cargo_value=28000.00,
            origin="Wellington Port",
            destination="Christchurch Warehouse",
            transport_mode="sea",
            scheduled_pickup=datetime.utcnow() - timedelta(days=1),
            scheduled_delivery=datetime.utcnow() + timedelta(days=1, hours=16),
            sla_deadline=datetime.utcnow() + timedelta(days=1, hours=20),
            sla_buffer_hours=4,
            current_status="at_port",
            current_eta=datetime.utcnow() + timedelta(days=2, hours=10),
            container_id="MSCU1234568",
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(case2_shipment)

        # === CASE 3: High Risk - Cargo Damage ===
        case3_shipment = Shipment(
            shipment_id="SF-2024-09003",
            customer_name="Fisher & Paykel",
            customer_tier="VIP",
            cargo_description="Precision electronic components",
            cargo_value=185000.00,
            origin="Auckland Port",
            destination="Christchurch Factory",
            transport_mode="sea",
            scheduled_pickup=datetime.utcnow() - timedelta(days=2),
            scheduled_delivery=datetime.utcnow() + timedelta(days=1, hours=9),
            sla_deadline=datetime.utcnow() + timedelta(days=1, hours=9),
            sla_buffer_hours=0,
            current_status="damaged",
            current_eta=datetime.utcnow() + timedelta(days=1, hours=9),
            container_id="MSCU1234569",
            special_requirements="Temperature controlled (2-8°C)",
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(case3_shipment)

        db.commit()
        print("✓ Shipments created")

        # Create exceptions
        case1_exception = Exception(
            exception_id="EXC-2024-00156",
            shipment_id="SF-2024-09001",
            exception_type="delay",
            severity="low",
            risk_level="low",
            detected_at=datetime.utcnow() - timedelta(minutes=5),
            root_cause="Traffic accident on Southern Motorway",
            ai_diagnosis="Major accident on Southern Motorway, South Auckland causing traffic congestion. GPS data shows vehicle stationary for 35 minutes. Traffic API confirms incident. Estimated delay: 45 minutes.",
            ai_confidence=0.98,
            status="resolved",
            requires_human_approval=False,
            resolved_at=datetime.utcnow() - timedelta(minutes=3),
            resolution_time_minutes=2,
            created_at=datetime.utcnow() - timedelta(minutes=5)
        )
        db.add(case1_exception)

        case2_exception = Exception(
            exception_id="EXC-2024-00157",
            shipment_id="SF-2024-09002",
            exception_type="delay",
            severity="medium",
            risk_level="medium",
            detected_at=datetime.utcnow() - timedelta(minutes=15),
            root_cause="Ferry service disruption due to high winds",
            ai_diagnosis="Bluebridge ferry canceled afternoon sailing due to 45-knot winds in Cook Strait. Weather service confirms sustained high winds. Next available ferry: tomorrow 06:00 AM.",
            ai_confidence=0.95,
            status="pending_approval",
            requires_human_approval=True,
            assigned_to="Mike Wang",
            created_at=datetime.utcnow() - timedelta(minutes=15)
        )
        db.add(case2_exception)

        case3_exception = Exception(
            exception_id="EXC-2024-00158",
            shipment_id="SF-2024-09003",
            exception_type="damage",
            severity="critical",
            risk_level="high",
            detected_at=datetime.utcnow() - timedelta(hours=4),
            root_cause="Refrigeration unit failure",
            ai_diagnosis="Container refrigeration unit malfunction detected. Temperature logs show cargo exposed to 15-22°C for approximately 6 hours (requirement: 2-8°C). High risk of electronic component damage. Requires immediate inspection.",
            ai_confidence=0.87,
            status="escalated",
            requires_human_approval=True,
            assigned_to="Sarah Chen, James Liu, Emma Wong",
            created_at=datetime.utcnow() - timedelta(hours=4)
        )
        db.add(case3_exception)

        db.commit()
        print("✓ Exceptions created")

        print("Demo data seeded successfully!")
        print("\nCreated shipments:")
        print("  - SF-2024-09001 (Case 1: Low Risk)")
        print("  - SF-2024-09002 (Case 2: Medium Risk)")
        print("  - SF-2024-09003 (Case 3: High Risk)")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print("\nDatabase initialization complete!")

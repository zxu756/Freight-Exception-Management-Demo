"""
FastAPI main application entry point.
"""
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import engine, Base
import air_cargo_models  # noqa: F401  # Register air cargo tables on Base.metadata
import road_freight_models  # noqa: F401  # Register road freight tables on Base.metadata
import rail_freight_models  # noqa: F401  # Register rail freight tables on Base.metadata
import sea_freight_models  # noqa: F401  # Register sea freight tables on Base.metadata
import notification_models  # noqa: F401  # Register customer notification table
import customer_models  # noqa: F401  # Register customer master data table
import decision_models  # noqa: F401  # Register coordinator decision tables
import quote_models  # noqa: F401  # Register carrier quote table
import admin_models  # noqa: F401  # Register users table (RBAC)
import world.maintenance  # noqa: F401  # Register carrier performance + metric snapshot tables
import sla_models  # noqa: F401  # Register SLA policy table
import environment_models  # noqa: F401  # Register environmental event table
import world.weather  # noqa: F401  # Register weather override table
import world.shipments  # noqa: F401  # Register shipment link table
import world.predict  # noqa: F401  # Register predicted impact table


# Create database tables on startup
def _migrate_ml_fields():
    """Idempotently add ML classification columns to existing exception tables."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    for table in ["air_exceptions", "road_exceptions", "sea_exceptions"]:
        if table not in insp.get_table_names():
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        with engine.begin() as conn:
            if "business_section" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN business_section VARCHAR(50)"))
            if "classification_confidence" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN classification_confidence FLOAT"))
            if "classification_decision" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN classification_decision VARCHAR(20)"))
            if "ood_score" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN ood_score FLOAT"))
            if "is_ood" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN is_ood BOOLEAN DEFAULT 0"))
            if "anomaly_score" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN anomaly_score FLOAT"))
            if "anomaly_reason" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN anomaly_reason VARCHAR(100)"))
            if "exception_category" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN exception_category VARCHAR(50)"))
            if "root_cause_category" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN root_cause_category VARCHAR(50)"))
            if "predicted_downstream_impact" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN predicted_downstream_impact TEXT"))
            if "recovery_cost" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN recovery_cost FLOAT"))
            if "recommended_action" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN recommended_action VARCHAR(50)"))
            if "recommendation_reason" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN recommendation_reason TEXT"))

    # impact_at column on environment_events (weather buffer period)
    if "environment_events" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("environment_events")}
        if "impact_at" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE environment_events ADD COLUMN impact_at DATETIME"))

    # is_lcl column on sea_containers (LCL multi-consignment containers)
    if "sea_containers" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("sea_containers")}
        if "is_lcl" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sea_containers ADD COLUMN is_lcl BOOLEAN DEFAULT 0"))

    # cargo_line_id column on sea_exceptions (line-level exceptions)
    if "sea_exceptions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("sea_exceptions")}
        if "cargo_line_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sea_exceptions ADD COLUMN cargo_line_id INTEGER"))

    # is_consolidated column on air_waybills (consolidated MAWB)
    if "air_waybills" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("air_waybills")}
        if "is_consolidated" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE air_waybills ADD COLUMN is_consolidated BOOLEAN DEFAULT 0"))

    # hawb_id column on air_exceptions (house-level exceptions)
    if "air_exceptions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("air_exceptions")}
        if "hawb_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE air_exceptions ADD COLUMN hawb_id INTEGER"))

    # is_ltl column on road_consignments (LTL multi-consignment loads)
    if "road_consignments" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("road_consignments")}
        if "is_ltl" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE road_consignments ADD COLUMN is_ltl BOOLEAN DEFAULT 0"))

    # consignment_line_id column on road_exceptions (line-level exceptions)
    if "road_exceptions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("road_exceptions")}
        if "consignment_line_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE road_exceptions ADD COLUMN consignment_line_id INTEGER"))

    # customer contact columns on exception_notifications (real delivery addresses)
    if "exception_notifications" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("exception_notifications")}
        with engine.begin() as conn:
            if "recipient_email" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN recipient_email VARCHAR(200)"))
            if "recipient_phone" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN recipient_phone VARCHAR(30)"))

    # SLA columns on cargo tables
    for table in ["air_waybills", "road_consignments", "sea_containers"]:
        if table not in insp.get_table_names():
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        with engine.begin() as conn:
            if "service_level" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN service_level VARCHAR(20)"))
            if "sla_tier" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN sla_tier VARCHAR(20)"))
            if "sla_grace_deadline" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN sla_grace_deadline DATETIME"))
            if "is_sla_breached" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN is_sla_breached BOOLEAN DEFAULT 0"))
            if "breach_type" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN breach_type VARCHAR(20)"))
            if "sla_penalty_nzd" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN sla_penalty_nzd FLOAT"))

    # Scenario 4 P0/P1 columns on exception tables (trigger link / latency / actual outcome)
    for table in ["air_exceptions", "road_exceptions", "sea_exceptions", "rail_exceptions"]:
        if table not in insp.get_table_names():
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        with engine.begin() as conn:
            if "trigger_event_id" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN trigger_event_id VARCHAR(50)"))
            if "detection_latency_minutes" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN detection_latency_minutes FLOAT"))
            if "actual_action" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN actual_action VARCHAR(50)"))
            if "actual_cost" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN actual_cost FLOAT"))
            if "actual_recovery_hours" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN actual_recovery_hours FLOAT"))
            # EVT-006 / MON-005: disposition + close/reopen columns
            for _col, _ddl in (("disposition", "VARCHAR(20)"), ("disposition_note", "TEXT"),
                               ("disposition_by", "VARCHAR(100)"), ("disposition_at", "DATETIME"),
                               ("closed_at", "DATETIME"), ("close_evidence", "TEXT"),
                               ("reopen_count", "INTEGER DEFAULT 0")):
                if _col not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {_col} {_ddl}"))
            if "escalation_reason" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN escalation_reason VARCHAR(200)"))

    # Notification outbox columns (real delivery status)
    if "exception_notifications" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("exception_notifications")}
        with engine.begin() as conn:
            if "sent_status" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN sent_status VARCHAR(20) DEFAULT 'pending'"))
            if "external_message_id" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN external_message_id VARCHAR(100)"))
            if "sent_real_at" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN sent_real_at DATETIME"))
            if "review_status" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN review_status VARCHAR(20) DEFAULT 'approved'"))
            if "reviewed_by" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN reviewed_by VARCHAR(100)"))
            if "reviewed_at" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN reviewed_at DATETIME"))
            if "edited_message" not in cols:
                conn.execute(text("ALTER TABLE exception_notifications ADD COLUMN edited_message TEXT"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    _migrate_ml_fields()
    from sla_seed import seed_sla_policies
    from customer_models import seed_customers
    from database import SessionLocal as _S
    _db = _S()
    try:
        seed_sla_policies(_db)
        _created = seed_customers(_db)
        if _created:
            print(f"Customer directory seeded: {_created} new customers")
        from admin_models import seed_users
        seed_users(_db)
    finally:
        _db.close()
    print("Database initialized successfully")

    # Start the shared world clock (single time authority for all simulators)
    from world.clock import world_clock
    world_clock.start()
    print("World clock started")

    # Start the unified world coordinator (drives all three engines on one clock)
    from world.coordinator import world_sim
    world_sim.start()
    print("World simulator coordinator started")

    yield
    # Shutdown
    from world.coordinator import world_sim
    world_sim.stop()
    from world.clock import world_clock
    world_clock.stop()
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)


# RBAC 权限不足 → 403（PermissionError 统一转 HTTP 403）
@app.exception_handler(PermissionError)
async def permission_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=403, content={"detail": str(exc)})

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# Import and include routers
from routers import air_cargo, road_freight, sea_freight, rail_freight, ask, world

app.include_router(air_cargo.router, prefix=settings.api_prefix, tags=["air_cargo"])
app.include_router(road_freight.router, prefix=settings.api_prefix, tags=["road_freight"])
app.include_router(sea_freight.router, prefix=settings.api_prefix, tags=["sea_freight"])
app.include_router(rail_freight.router, prefix=settings.api_prefix, tags=["rail_freight"])
app.include_router(ask.router, prefix=settings.api_prefix, tags=["ask"])
app.include_router(world.router, prefix=settings.api_prefix, tags=["world"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

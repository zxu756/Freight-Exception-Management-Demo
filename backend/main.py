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
import sea_freight_models  # noqa: F401  # Register sea freight tables on Base.metadata
import notification_models  # noqa: F401  # Register customer notification table


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    _migrate_ml_fields()
    print("Database initialized successfully")

    # Start live air cargo simulator
    if settings.air_sim_enabled:
        from air_cargo_simulator import simulator
        simulator.start()
        print("Air cargo simulator started")

    # Start live road freight simulator
    if settings.road_sim_enabled:
        from road_freight_simulator import simulator as road_simulator
        road_simulator.start()
        print("Road freight simulator started")

    # Start live sea freight simulator
    if settings.sea_sim_enabled:
        from sea_freight_simulator import simulator as sea_simulator
        sea_simulator.start()
        print("Sea freight simulator started")

    yield
    # Shutdown
    if settings.air_sim_enabled:
        from air_cargo_simulator import simulator
        simulator.stop()
    if settings.road_sim_enabled:
        from road_freight_simulator import simulator as road_simulator
        road_simulator.stop()
    if settings.sea_sim_enabled:
        from sea_freight_simulator import simulator as sea_simulator
        sea_simulator.stop()
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

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
from routers import exceptions, shipments, decisions, demo, air_cargo, road_freight, sea_freight

app.include_router(exceptions.router, prefix=settings.api_prefix, tags=["exceptions"])
app.include_router(shipments.router, prefix=settings.api_prefix, tags=["shipments"])
app.include_router(decisions.router, prefix=settings.api_prefix, tags=["decisions"])
app.include_router(demo.router, prefix=settings.api_prefix, tags=["demo"])
app.include_router(air_cargo.router, prefix=settings.api_prefix, tags=["air_cargo"])
app.include_router(road_freight.router, prefix=settings.api_prefix, tags=["road_freight"])
app.include_router(sea_freight.router, prefix=settings.api_prefix, tags=["sea_freight"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

"""
FastAPI main application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import engine, Base


# Create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")
    yield
    # Shutdown
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
from routers import exceptions, shipments, decisions, demo

app.include_router(exceptions.router, prefix=settings.api_prefix, tags=["exceptions"])
app.include_router(shipments.router, prefix=settings.api_prefix, tags=["shipments"])
app.include_router(decisions.router, prefix=settings.api_prefix, tags=["decisions"])
app.include_router(demo.router, prefix=settings.api_prefix, tags=["demo"])


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

# Backend - FastAPI Application

## 🚧 Coming Soon

This directory will contain the Python FastAPI backend for the Freight Exception Management demo.

## Planned Structure

```
backend/
├── main.py                    # FastAPI entry point
├── config.py                  # Configuration settings
├── database.py                # Database connection
├── models.py                  # SQLAlchemy ORM models
├── schemas.py                 # Pydantic schemas for validation
├── init_db.py                 # Database initialization script
├── decision_engine.py         # AI decision logic
├── risk_calculator.py         # Risk scoring algorithm
├── event_simulator.py         # Demo event generation
├── notification_service.py    # Notification logic
├── routers/
│   ├── __init__.py
│   ├── exceptions.py          # Exception endpoints
│   ├── shipments.py           # Shipment endpoints
│   ├── decisions.py           # Decision endpoints
│   └── demo.py                # Demo control endpoints
├── tests/
│   ├── test_decision_engine.py
│   ├── test_risk_calculator.py
│   └── test_api.py
├── requirements.txt           # Python dependencies
└── README.md                  # Backend documentation
```

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Database**: SQLite (SQLAlchemy ORM)
- **WebSocket**: python-socketio
- **Validation**: Pydantic v2
- **Testing**: pytest
- **Code Quality**: Black, Ruff

## Key Features

1. **Exception Detection API**: Monitors shipment events and detects anomalies
2. **AI Decision Engine**: Risk scoring and solution generation
3. **WebSocket Server**: Real-time updates to frontend
4. **Mock External APIs**: Simulated carrier, weather, and port data
5. **Event Simulator**: Generates realistic demo scenarios

## Development Setup (Coming Soon)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Run development server
uvicorn main:app --reload
```

## API Endpoints (Planned)

See [DEMO_TECHNICAL_DESIGN.md](../DEMO_TECHNICAL_DESIGN.md) for complete API specification.

### Core Endpoints
- `GET /api/exceptions` - List all exceptions
- `GET /api/exceptions/{id}` - Get exception details
- `POST /api/exceptions/{id}/approve` - Approve decision
- `GET /api/shipments` - List shipments
- `GET /api/decisions/{exception_id}` - Get AI recommendations

### Demo Control
- `POST /api/demo/start` - Start demo simulation
- `POST /api/demo/reset` - Reset to initial state
- `POST /api/demo/pause` - Pause auto-play

### WebSocket
- `ws://localhost:8000/ws` - Real-time event stream

---

**Status**: 📋 Planning  
**Target Completion**: Week 1-2

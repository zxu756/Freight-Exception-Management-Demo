# Phase 1 - Freight Exception Management Demo

## Overview
This is a simplified version of the Freight Exception Management system for Phase 1 demo.

## Backend

### Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run
```bash
python main.py
```

The backend will start on port **8001**.

## Frontend

### Setup
```bash
cd frontend
npm install
```

### Run
```bash
npm run dev
```

The frontend will start on port **5174**.

## Features

### Dashboard
- Overview of active exceptions by type (Air, Road, Sea)
- Recent exceptions list

### Exception List
- Filter by type (Air, Road, Sea)
- Search by exception ID
- View exception details

### Exception Detail
- Basic information
- Exception details
- Impact information
- Recommended actions

### Notifications
- View all notifications
- Status tracking

### Decision Panel
- Select exception
- Make decisions (Approve, Reject, Escalate, Reroute, Hold)
- Add reason and notes

## API Endpoints

The backend provides REST API endpoints:

- `GET /api/air-cargo/exceptions` - List air cargo exceptions
- `GET /api/road-freight/exceptions` - List road freight exceptions
- `GET /api/sea-freight/exceptions` - List sea freight exceptions
- `GET /api/air-cargo/notifications` - List notifications

## Database

The SQLite database file is named `phase1_demo.db` and will be created automatically on first run.

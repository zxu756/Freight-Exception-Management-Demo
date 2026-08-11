# Freight Exception Management System - Demo Technical Design

**Version:** 1.0  
**Date:** 2026-08-11  
**Author:** Demo Development Team  
**Project:** Southern Freight Exception Management Agent Demo

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Demo Overview](#2-demo-overview)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Database Design](#5-database-design)
6. [API Design](#6-api-design)
7. [Frontend Components](#7-frontend-components)
8. [Three Demo Cases](#8-three-demo-cases)
9. [AI Decision Engine](#9-ai-decision-engine)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Deployment Guide](#11-deployment-guide)

---

## 1. Executive Summary

### 1.1 Purpose

This document provides a complete technical specification for building an interactive demo of the Freight Exception Management System. The demo showcases how an AI-powered system can automatically detect, diagnose, and resolve freight exceptions with varying levels of risk.

### 1.2 Demo Objectives

- **Demonstrate** the complete exception handling workflow from detection to resolution
- **Showcase** three different risk levels: low (auto-resolved), medium (human approval), high (deep human involvement)
- **Visualize** the time savings and efficiency improvements compared to manual processing
- **Provide** an interactive experience where users can see the system in action

### 1.3 Key Features

- ✅ Real-time exception detection and monitoring
- ✅ AI-powered root cause diagnosis
- ✅ Automated decision-making with risk-based escalation
- ✅ Interactive coordinator approval interface
- ✅ Live timeline visualization of exception handling
- ✅ Simulated external data sources (carriers, weather, ports)
- ✅ Multi-case parallel processing view

---

## 2. Demo Overview

### 2.1 Demo Scope

The demo simulates a 24-hour period where Southern Freight's system processes three concurrent exceptions:

| Case | Risk Level | Exception Type | Resolution |
|------|-----------|----------------|------------|
| Case 1 | 🟢 Low | Traffic delay | Auto-resolved |
| Case 2 | 🟡 Medium | Ferry cancellation | Human-approved rerouting |
| Case 3 | 🔴 High | Cargo damage | Deep team involvement |

### 2.2 User Journey

```
User opens demo dashboard
    ↓
Sees three active exceptions in real-time
    ↓
Can drill down into each case to see:
    - Event timeline
    - AI diagnosis
    - Decision logic
    - Communication sent
    - Resolution steps
    ↓
Can interact with Case 2 approval interface
    ↓
Views comparative metrics and outcomes
```

### 2.3 Demo Modes

1. **Auto-play Mode**: System automatically progresses through all cases
2. **Step-by-step Mode**: User clicks "Next" to advance each step
3. **Interactive Mode**: User can act as coordinator and approve/modify decisions

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Dashboard   │  │ Case Detail  │  │ Approval Panel  │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API + WebSocket
┌────────────────────────────┴────────────────────────────────┐
│                  Backend (Python FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Event Engine │  │ AI Decision  │  │ Notification    │  │
│  │   Simulator  │  │    Engine    │  │    Service      │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                    Database (SQLite)                        │
│     Shipments | Exceptions | Events | Decisions            │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Description

#### 3.2.1 Frontend Components

- **Dashboard**: Main view showing all active exceptions
- **Case Detail View**: Timeline and detailed information for one case
- **Approval Interface**: Coordinator decision panel (Case 2)
- **Team Collaboration View**: Multi-person handling (Case 3)
- **Metrics Dashboard**: Statistics and performance indicators

#### 3.2.2 Backend Services

- **Event Simulator**: Generates realistic freight tracking events
- **AI Decision Engine**: Implements risk assessment and recommendation logic
- **Notification Service**: Simulates email/SMS sending
- **External API Mock**: Simulates carrier, weather, and port APIs
- **WebSocket Server**: Real-time updates to frontend

#### 3.2.3 Data Layer

- **SQLite Database**: Lightweight, portable, perfect for demo
- **In-memory Cache**: For real-time event processing
- **Mock External APIs**: Simulated third-party data sources

---

## 4. Technology Stack

### 4.1 Frontend Stack

```javascript
{
  "framework": "React 18",
  "language": "TypeScript",
  "styling": "Tailwind CSS",
  "stateManagement": "React Context + Hooks",
  "routing": "React Router v6",
  "charts": "Recharts",
  "icons": "Lucide React",
  "http": "Axios",
  "websocket": "Socket.io Client"
}
```

### 4.2 Backend Stack

```python
{
  "framework": "FastAPI 0.104+",
  "language": "Python 3.11+",
  "database": "SQLite3",
  "orm": "SQLAlchemy 2.0",
  "websocket": "Socket.io (python-socketio)",
  "validation": "Pydantic v2",
  "async": "asyncio",
  "testing": "pytest"
}
```

### 4.3 Development Tools

- **Package Manager**: npm (frontend), pip (backend)
- **Code Quality**: ESLint, Prettier (frontend), Black, Ruff (backend)
- **Version Control**: Git
- **API Documentation**: Swagger/OpenAPI (auto-generated by FastAPI)

### 4.4 Deployment Options

- **Option 1**: Docker Compose (recommended for demo)
- **Option 2**: Local development servers
- **Option 3**: Cloud deployment (Vercel frontend + Railway/Render backend)

---

## 5. Database Design

### 5.1 Database Schema

#### 5.1.1 `shipments` Table

Stores freight shipment orders.

```sql
CREATE TABLE shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    customer_tier VARCHAR(20) NOT NULL, -- 'VIP', 'high', 'medium', 'low'
    cargo_description TEXT NOT NULL,
    cargo_value DECIMAL(10, 2) NOT NULL,
    origin VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    transport_mode VARCHAR(50) NOT NULL, -- 'road', 'rail', 'sea', 'air'
    scheduled_pickup TIMESTAMP NOT NULL,
    scheduled_delivery TIMESTAMP NOT NULL,
    sla_deadline TIMESTAMP NOT NULL,
    sla_buffer_hours INTEGER NOT NULL,
    current_status VARCHAR(50) NOT NULL,
    current_eta TIMESTAMP,
    container_id VARCHAR(50),
    vehicle_id VARCHAR(50),
    special_requirements TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5.1.2 `exceptions` Table

Stores detected freight exceptions.

```sql
CREATE TABLE exceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_id VARCHAR(50) UNIQUE NOT NULL,
    shipment_id VARCHAR(50) NOT NULL,
    exception_type VARCHAR(50) NOT NULL, -- 'delay', 'damage', 'misroute', 'customs_hold'
    severity VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    risk_level VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high'
    detected_at TIMESTAMP NOT NULL,
    root_cause TEXT,
    ai_diagnosis TEXT,
    ai_confidence DECIMAL(3, 2), -- 0.00 to 1.00
    status VARCHAR(50) NOT NULL, -- 'detected', 'diagnosed', 'pending_approval', 'approved', 'executing', 'resolved'
    requires_human_approval BOOLEAN DEFAULT FALSE,
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    resolution_time_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
);
```

#### 5.1.3 `events` Table

Stores all tracking and system events.

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id VARCHAR(50) UNIQUE NOT NULL,
    shipment_id VARCHAR(50),
    exception_id VARCHAR(50),
    event_type VARCHAR(100) NOT NULL,
    event_source VARCHAR(100) NOT NULL, -- 'carrier_api', 'port_api', 'vehicle_tracker', 'system'
    event_data JSON,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (exception_id) REFERENCES exceptions(exception_id)
);
```

#### 5.1.4 `decisions` Table

Stores AI recommendations and human decisions.

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id VARCHAR(50) UNIQUE NOT NULL,
    exception_id VARCHAR(50) NOT NULL,
    decision_type VARCHAR(50) NOT NULL, -- 'auto_resolve', 'recommend', 'escalate'
    options JSON NOT NULL, -- Array of solution options with cost/time/risk
    recommended_option VARCHAR(10), -- e.g., 'A', 'B', 'C'
    recommendation_reasoning TEXT,
    human_decision VARCHAR(10), -- What human actually chose
    human_decision_by VARCHAR(100),
    human_decision_at TIMESTAMP,
    decision_outcome VARCHAR(50), -- 'accepted', 'modified', 'rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exception_id) REFERENCES exceptions(exception_id)
);
```

#### 5.1.5 `notifications` Table

Stores all customer and internal notifications.

```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id VARCHAR(50) UNIQUE NOT NULL,
    exception_id VARCHAR(50) NOT NULL,
    recipient_type VARCHAR(50) NOT NULL, -- 'customer', 'coordinator', 'team'
    recipient VARCHAR(200) NOT NULL,
    channel VARCHAR(50) NOT NULL, -- 'email', 'sms', 'system'
    subject TEXT,
    message TEXT NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'sent', 'delivered', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exception_id) REFERENCES exceptions(exception_id)
);
```

### 5.2 Sample Data Seeds

The demo will include pre-populated data for the three cases:

```python
# Case 1: Low Risk
{
    "shipment_id": "SF-2024-09001",
    "customer_name": "Paper Plus",
    "customer_tier": "medium",
    "cargo_value": 2800.00,
    "origin": "Auckland",
    "destination": "Hamilton",
    "transport_mode": "road"
}

# Case 2: Medium Risk
{
    "shipment_id": "SF-2024-09002",
    "customer_name": "Countdown Supermarkets",
    "customer_tier": "high",
    "cargo_value": 28000.00,
    "origin": "Wellington Port",
    "destination": "Christchurch Warehouse",
    "transport_mode": "sea"
}

# Case 3: High Risk
{
    "shipment_id": "SF-2024-09003",
    "customer_name": "Fisher & Paykel",
    "customer_tier": "VIP",
    "cargo_value": 185000.00,
    "origin": "Auckland Port",
    "destination": "Christchurch Factory",
    "transport_mode": "sea"
}
```

---

## 6. API Design

### 6.1 API Endpoints

#### 6.1.1 Exception Endpoints

**GET /api/exceptions**
- Returns all active exceptions
- Response: Array of exception objects with full details

```json
{
  "exceptions": [
    {
      "exception_id": "EXC-2024-00156",
      "shipment_id": "SF-2024-09001",
      "exception_type": "delay",
      "severity": "low",
      "risk_level": "low",
      "status": "resolved",
      "detected_at": "2026-08-11T08:15:00Z",
      "resolved_at": "2026-08-11T08:17:00Z",
      "resolution_time_minutes": 2
    }
  ]
}
```

**GET /api/exceptions/{exception_id}**
- Returns detailed information for one exception
- Includes timeline, events, decisions, notifications

**POST /api/exceptions/{exception_id}/approve**
- Human approves a recommended decision
- Body: `{"decision": "B", "notes": "Approved rerouting"}`

**POST /api/exceptions/{exception_id}/modify**
- Human modifies AI recommendation
- Body: `{"decision": "custom", "custom_plan": {...}}`

#### 6.1.2 Shipment Endpoints

**GET /api/shipments**
- Returns all shipments

**GET /api/shipments/{shipment_id}**
- Returns detailed shipment information
- Includes current location, ETA, events

**GET /api/shipments/{shipment_id}/timeline**
- Returns event timeline for visualization

#### 6.1.3 Decision Endpoints

**GET /api/decisions/{exception_id}**
- Returns AI recommendations for an exception
- Includes all options with cost/time/risk analysis

```json
{
  "decision_id": "DEC-2024-00234",
  "exception_id": "EXC-2024-00157",
  "options": [
    {
      "option_id": "A",
      "description": "Wait for next ferry",
      "cost": 0,
      "new_eta": "2026-08-14T10:00:00Z",
      "sla_impact": "breach_18h",
      "risk": "low"
    },
    {
      "option_id": "B",
      "description": "Reroute via land",
      "cost": 650,
      "new_eta": "2026-08-13T18:00:00Z",
      "sla_impact": "minor_delay_2h",
      "risk": "medium"
    }
  ],
  "recommended_option": "B",
  "reasoning": "Cost reasonable, maintains customer relationship..."
}
```

#### 6.1.4 Demo Control Endpoints

**POST /api/demo/start**
- Starts the demo simulation
- Body: `{"mode": "auto" | "step" | "interactive"}`

**POST /api/demo/reset**
- Resets demo to initial state

**POST /api/demo/pause**
- Pauses auto-play mode

**POST /api/demo/next-step**
- Advances to next step in step-by-step mode

#### 6.1.5 WebSocket Events

**Connected at**: `ws://localhost:8000/ws`

**Events sent to client:**

```javascript
// New exception detected
{
  "type": "exception_detected",
  "data": {
    "exception_id": "EXC-2024-00156",
    "shipment_id": "SF-2024-09001",
    "severity": "low"
  }
}

// Exception status updated
{
  "type": "exception_status_update",
  "data": {
    "exception_id": "EXC-2024-00156",
    "old_status": "detected",
    "new_status": "diagnosed"
  }
}

// Notification sent
{
  "type": "notification_sent",
  "data": {
    "exception_id": "EXC-2024-00156",
    "recipient": "customer",
    "channel": "sms"
  }
}

// Decision pending approval
{
  "type": "approval_required",
  "data": {
    "exception_id": "EXC-2024-00157",
    "coordinator": "Mike Wang"
  }
}
```

### 6.2 API Response Format

All API responses follow this structure:

```json
{
  "success": true,
  "data": {...},
  "timestamp": "2026-08-11T14:32:00Z",
  "error": null
}
```

Error response:

```json
{
  "success": false,
  "data": null,
  "timestamp": "2026-08-11T14:32:00Z",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid exception_id format"
  }
}
```

---

## 7. Frontend Components

### 7.1 Component Hierarchy

```
App
├── DemoControlBar (start/pause/reset)
├── Dashboard
│   ├── MetricsPanel
│   │   ├── ActiveExceptionsCard
│   │   ├── ResolutionTimeCard
│   │   └── SavingsCard
│   ├── CaseCard (Case 1 - Low Risk)
│   ├── CaseCard (Case 2 - Medium Risk)
│   └── CaseCard (Case 3 - High Risk)
├── CaseDetailView
│   ├── CaseHeader
│   ├── TimelineView
│   ├── DiagnosisPanel
│   ├── DecisionPanel
│   └── NotificationsPanel
└── ApprovalInterface (for Case 2)
    ├── ExceptionSummary
    ├── AIRecommendation
    ├── OptionsComparison
    └── ApprovalActions
```

### 7.2 Key Component Specifications

#### 7.2.1 Dashboard Component

```typescript
interface DashboardProps {
  mode: 'auto' | 'step' | 'interactive';
}

interface DashboardState {
  exceptions: Exception[];
  metrics: Metrics;
  selectedCase: string | null;
}

// Features:
// - Real-time updates via WebSocket
// - Three case cards displayed side-by-side
// - Metrics summary at top
// - Click to drill down into case details
```

#### 7.2.2 CaseCard Component

```typescript
interface CaseCardProps {
  exception: Exception;
  shipment: Shipment;
  onClick: () => void;
}

// Visual elements:
// - Risk indicator (🟢🟡🔴)
// - Shipment ID and customer name
// - Current status badge
// - Mini timeline progress bar
// - Key metrics (resolution time, cost)
// - Quick action buttons
```

#### 7.2.3 TimelineView Component

```typescript
interface TimelineViewProps {
  exception: Exception;
  events: Event[];
}

interface TimelineEvent {
  timestamp: string;
  title: string;
  description: string;
  icon: string;
  status: 'completed' | 'current' | 'pending';
}

// Visual design:
// Vertical timeline with dots and connecting lines
// Color-coded by event type
// Expandable details for each event
// Auto-scroll to current event
```

---

## 8. Three Demo Cases

### 8.1 Case 1: Low Risk - Traffic Delay (Auto-Resolved) 🟢

#### 8.1.1 Scenario Details

```yaml
Shipment:
  ID: SF-2024-09001
  Customer: Paper Plus
  Tier: Medium
  Cargo: Office stationery
  Value: $2,800
  Route: Auckland → Hamilton
  Distance: 125 km
  Mode: Road
  Original ETA: 2026-08-12 10:00
  SLA Deadline: 2026-08-12 22:00
  SLA Buffer: 12 hours

Exception Event:
  Time: 2026-08-11 08:15
  Type: Vehicle dwell time exceeded
  Trigger: GPS shows truck stationary for 35 minutes
  Location: Southern Motorway, South Auckland

AI Analysis:
  Root Cause: "Traffic accident on Southern Motorway"
  Confidence: 98%
  Impact: 45-minute delay
  New ETA: 2026-08-12 10:45
  SLA Status: Within buffer
  Risk Level: LOW

Decision:
  Auto-resolve: TRUE
  Action: Send customer notification only
  Human approval: NOT REQUIRED
  Total time: 2 minutes
  Additional cost: $0
```

#### 8.1.2 Event Timeline

```
08:15:00 - 🚨 Event detected
08:16:00 - 🤖 AI diagnosis complete
08:16:30 - ✅ Auto-resolve decision
08:17:00 - 📱 SMS sent to customer
08:17:15 - ✅ Case closed
```

---

### 8.2 Case 2: Medium Risk - Ferry Cancellation (Human Approval) 🟡

#### 8.2.1 Scenario Details

```yaml
Shipment:
  ID: SF-2024-09002
  Customer: Countdown Supermarkets
  Tier: High
  Cargo: Food packaging
  Value: $28,000
  Route: Wellington → Christchurch
  Mode: Sea + Road
  Original ETA: 2026-08-13 16:00
  SLA Deadline: 2026-08-13 20:00

Exception Event:
  Time: 2026-08-11 14:30
  Type: Ferry cancellation
  Reason: High winds (45 knots)

AI Analysis:
  Root Cause: "Cook Strait wind disruption"
  Confidence: 95%
  Risk Level: MEDIUM

Decision Options:
  A. Wait for next ferry: $0, 18h late ❌
  B. Reroute via land: $650, 2h late ⚠️
  C. Air freight: $4,200, 2h early ✅

AI Recommendation: Option B
Reasoning: Cost-effective, avoids SLA breach

Approval Required: YES
Approved by: Mike Wang (14:42)
Total time: 14 minutes
Additional cost: $650
```

---

### 8.3 Case 3: High Risk - Cargo Damage (Team Handling) 🔴

#### 8.3.1 Scenario Details

```yaml
Shipment:
  ID: SF-2024-09003
  Customer: Fisher & Paykel (VIP)
  Cargo: Precision electronics
  Value: $185,000
  Route: Auckland Port → Christchurch
  Mode: Sea (refrigerated)
  Special: Temperature controlled (2-8°C)

Exception Event:
  Time: 2026-08-11 11:20
  Type: Cargo damage risk
  Issue: Refrigeration unit failure
  Duration: ~6 hours at 15-22°C

AI Analysis:
  Root Cause: "Reefer unit malfunction"
  Damage Risk: HIGH
  Confidence: 87% (needs inspection)
  Risk Level: HIGH

System Action:
  Auto-resolve: FALSE
  Immediate escalation to:
    - Senior Coordinator: Sarah Chen
    - Customer Manager: James Liu
    - Claims Specialist: Emma Wong

Team Decision (11:30-16:30):
  1. Seal container
  2. Insurance inspector
  3. Customer notification (phone)
  4. Damage assessment
  5. Negotiate solution

Final Resolution:
  - 40% cargo intact → expedite delivery
  - 60% damaged → full compensation
  - Emergency procurement assistance
  Total time: 5 hours
  Insurance claim: $110,000
  Additional cost: $8,500
```


---

## 9. AI Decision Engine

### 9.1 Decision Logic Flow

```python
def evaluate_exception(exception, shipment, context):
    """
    Core decision engine that determines risk level and routing.
    """
    
    # Step 1: Calculate risk score
    risk_score = calculate_risk_score(
        cargo_value=shipment.cargo_value,
        customer_tier=shipment.customer_tier,
        sla_breach_hours=calculate_sla_breach(exception, shipment),
        exception_type=exception.type,
        historical_patterns=context.historical_data
    )
    
    # Step 2: Determine risk level
    risk_level = categorize_risk(risk_score)
    
    # Step 3: Generate solution options
    options = generate_solutions(exception, shipment, context)
    
    # Step 4: Rank and recommend
    recommended = rank_solutions(options, shipment, risk_score)
    
    # Step 5: Route decision
    if should_auto_resolve(risk_level, exception, shipment):
        return auto_resolve(exception, recommended)
    elif should_escalate_to_team(risk_level, exception, shipment):
        return escalate_to_team(exception, options, context)
    else:
        return require_approval(exception, options, recommended)
```

### 9.2 Risk Scoring Algorithm

```python
def calculate_risk_score(cargo_value, customer_tier, sla_breach_hours, 
                         exception_type, historical_patterns):
    """
    Risk score: 0-100 (higher = more risk)
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
    tier_scores = {'low': 0, 'medium': 5, 'high': 15, 'VIP': 20}
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
    
    return score

def categorize_risk(score):
    """
    Low: 0-30, Medium: 31-60, High: 61-100
    """
    if score <= 30:
        return 'low'
    elif score <= 60:
        return 'medium'
    else:
        return 'high'
```

### 9.3 Auto-Resolution Rules

```python
def should_auto_resolve(risk_level, exception, shipment):
    """
    Conditions for automatic resolution without human approval.
    """
    
    # Never auto-resolve high risk
    if risk_level == 'high':
        return False
    
    # Auto-resolve criteria
    criteria = [
        shipment.cargo_value < 5000,
        exception.sla_breach_hours <= 0,
        exception.type == 'delay',
        exception.estimated_cost == 0,
        exception.ai_confidence >= 0.95
    ]
    
    # Must meet ALL criteria for low risk
    if risk_level == 'low':
        return all(criteria)
    
    # Medium risk: more restrictive
    return False
```

### 9.4 Solution Generation Logic

```python
def generate_solutions(exception, shipment, context):
    """
    Generate 2-4 solution options based on exception type.
    """
    options = []
    
    if exception.type == 'delay':
        # Option A: Wait
        options.append({
            'id': 'A',
            'description': 'Continue with current plan',
            'cost': 0,
            'new_eta': exception.delayed_eta,
            'sla_impact': calculate_sla_impact(exception.delayed_eta, shipment),
            'risk': 'low'
        })
        
        # Option B: Expedite
        if has_expedite_option(shipment):
            expedite = calculate_expedite_cost(shipment, exception)
            options.append({
                'id': 'B',
                'description': 'Expedite via faster transport',
                'cost': expedite.cost,
                'new_eta': expedite.eta,
                'sla_impact': calculate_sla_impact(expedite.eta, shipment),
                'risk': 'medium'
            })
        
        # Option C: Reroute
        if has_alternate_route(shipment):
            reroute = calculate_reroute_option(shipment, exception)
            options.append({
                'id': 'C',
                'description': 'Reroute via alternate path',
                'cost': reroute.cost,
                'new_eta': reroute.eta,
                'sla_impact': calculate_sla_impact(reroute.eta, shipment),
                'risk': 'medium'
            })
    
    elif exception.type == 'damage':
        # Different solution set for damage cases
        options = generate_damage_solutions(exception, shipment, context)
    
    return options

def rank_solutions(options, shipment, risk_score):
    """
    Rank solutions and recommend the best one.
    """
    for option in options:
        # Calculate utility score
        option['utility_score'] = calculate_utility(
            cost=option['cost'],
            sla_impact=option['sla_impact'],
            risk=option['risk'],
            cargo_value=shipment.cargo_value,
            customer_tier=shipment.customer_tier
        )
    
    # Sort by utility score (higher is better)
    ranked = sorted(options, key=lambda x: x['utility_score'], reverse=True)
    
    return ranked[0]['id']  # Return best option ID
```

### 9.5 Root Cause Diagnosis (Simulated AI)

For the demo, we simulate AI diagnosis using rule-based logic and templates:

```python
def generate_ai_diagnosis(exception, external_data):
    """
    Simulates AI-powered root cause analysis.
    In production, this would call an LLM API.
    """
    
    templates = {
        'traffic_delay': {
            'diagnosis': "Traffic accident on {location} causing {duration} delays",
            'confidence': 0.95,
            'evidence': ['GPS data', 'Traffic API', 'Historical patterns']
        },
        'weather_disruption': {
            'diagnosis': "Severe weather in {location}: {condition}",
            'confidence': 0.93,
            'evidence': ['Weather service', 'Carrier notification', 'Port status']
        },
        'equipment_failure': {
            'diagnosis': "{equipment} malfunction detected at {time}",
            'confidence': 0.87,
            'evidence': ['Sensor data', 'Maintenance logs', 'Inspection required']
        }
    }
    
    # Select appropriate template
    template = select_template(exception.type, external_data)
    
    # Fill in details
    diagnosis = template['diagnosis'].format(**external_data)
    
    # Calculate confidence based on data quality
    confidence = adjust_confidence(
        base_confidence=template['confidence'],
        data_completeness=external_data.completeness,
        data_recency=external_data.age
    )
    
    return {
        'root_cause': diagnosis,
        'confidence': confidence,
        'evidence': template['evidence'],
        'timestamp': datetime.now()
    }
```

---

## 10. Implementation Roadmap

### 10.1 Phase 1: Foundation (Week 1)

**Backend Setup**
- [ ] Initialize FastAPI project structure
- [ ] Set up SQLite database
- [ ] Create database schema and migrations
- [ ] Implement ORM models (SQLAlchemy)
- [ ] Seed database with three case scenarios
- [ ] Create mock external API services

**Frontend Setup**
- [ ] Initialize React + TypeScript project
- [ ] Set up Tailwind CSS
- [ ] Create basic routing structure
- [ ] Implement WebSocket connection
- [ ] Create layout and navigation

### 10.2 Phase 2: Core Features (Week 2)

**Backend Development**
- [ ] Implement exception detection logic
- [ ] Build AI decision engine (rules-based)
- [ ] Create risk scoring algorithm
- [ ] Implement solution generation logic
- [ ] Build notification service (mock)
- [ ] Create all REST API endpoints

**Frontend Development**
- [ ] Build Dashboard component
- [ ] Create CaseCard component
- [ ] Implement MetricsPanel
- [ ] Add real-time updates via WebSocket
- [ ] Create loading states and animations

### 10.3 Phase 3: Demo Cases (Week 3)

**Case Implementation**
- [ ] Implement Case 1 (low risk) flow
- [ ] Implement Case 2 (medium risk) flow
- [ ] Implement Case 3 (high risk) flow
- [ ] Create event simulator for all cases
- [ ] Build timeline visualization
- [ ] Add case detail views

**Approval Interface**
- [ ] Build approval panel for Case 2
- [ ] Implement decision modification
- [ ] Add notification preview
- [ ] Create team collaboration view for Case 3

### 10.4 Phase 4: Polish & Demo Modes (Week 4)

**Demo Controls**
- [ ] Implement auto-play mode
- [ ] Implement step-by-step mode
- [ ] Implement interactive mode
- [ ] Add demo reset functionality
- [ ] Create demo state persistence

**UI Polish**
- [ ] Add animations and transitions
- [ ] Implement responsive design
- [ ] Add loading states
- [ ] Create error handling
- [ ] Add tooltips and help text

**Documentation**
- [ ] Write API documentation
- [ ] Create user guide
- [ ] Add code comments
- [ ] Write deployment guide

### 10.5 Development Timeline

```
Week 1: Foundation
├─ Day 1-2: Project setup (backend + frontend)
├─ Day 3-4: Database design and models
├─ Day 5-7: Basic API and UI structure

Week 2: Core Features
├─ Day 8-10: Backend logic (decision engine)
├─ Day 11-14: Frontend components (dashboard)

Week 3: Demo Cases
├─ Day 15-17: Case 1 & 2 implementation
├─ Day 18-21: Case 3 & approval interface

Week 4: Polish
├─ Day 22-24: Demo modes and animations
├─ Day 25-28: Testing and documentation
```

---

## 11. Deployment Guide

### 11.1 Local Development

**Prerequisites**
```bash
- Python 3.11+
- Node.js 18+
- npm or yarn
- Git
```

**Backend Setup**
```bash
# Clone repository
git clone <repo-url>
cd freight-exception-demo/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Run development server
uvicorn main:app --reload --port 8000
```

**Frontend Setup**
```bash
# Navigate to frontend
cd freight-exception-demo/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Access demo at: `http://localhost:5173`

### 11.2 Docker Deployment

**docker-compose.yml**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./demo.db
    volumes:
      - ./backend:/app
      - db-data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  db-data:
```

**Run with Docker**
```bash
docker-compose up -d
```

### 11.3 Production Deployment Options

**Option 1: Vercel + Railway**
- Frontend: Deploy to Vercel
- Backend: Deploy to Railway
- Database: SQLite on Railway volume

**Option 2: AWS**
- Frontend: S3 + CloudFront
- Backend: EC2 or ECS
- Database: RDS (if scaling beyond SQLite)

**Option 3: Digital Ocean**
- App Platform for both frontend and backend
- Managed database option available

---

## 12. Testing Strategy

### 12.1 Unit Tests

**Backend**
```python
# Test risk scoring
def test_risk_score_low():
    score = calculate_risk_score(
        cargo_value=2000,
        customer_tier='medium',
        sla_breach_hours=0,
        exception_type='delay'
    )
    assert score <= 30
    assert categorize_risk(score) == 'low'

# Test auto-resolution logic
def test_auto_resolve_criteria():
    exception = create_test_exception(type='delay', cost=0)
    shipment = create_test_shipment(value=3000)
    assert should_auto_resolve('low', exception, shipment) == True
```

**Frontend**
```typescript
// Test CaseCard rendering
test('renders case card with correct risk indicator', () => {
  const exception = { risk_level: 'low', ... };
  render(<CaseCard exception={exception} />);
  expect(screen.getByText('🟢')).toBeInTheDocument();
});
```

### 12.2 Integration Tests

- Test full exception flow from detection to resolution
- Test WebSocket real-time updates
- Test approval workflow
- Test notification generation

### 12.3 End-to-End Tests

Use Playwright or Cypress to test:
- Complete demo playthrough
- User interactions (approval, modify)
- Mode switching (auto, step, interactive)
- Demo reset functionality

---

## 13. Future Enhancements

### 13.1 Post-Demo Extensions

**Real AI Integration**
- Integrate OpenAI/Anthropic API for actual LLM-powered diagnosis
- Train ML models on historical exception data
- Implement predictive exception detection

**Additional Features**
- Multi-language support (中文/English toggle)
- Export reports (PDF/Excel)
- Admin configuration panel
- Historical exception analytics dashboard
- Mobile responsive design

**Integration Points**
- Connect to real TMS systems
- Integrate actual carrier APIs
- Connect to real notification services (Twilio, SendGrid)
- Add authentication and user management

### 13.2 Scaling Considerations

When moving from demo to production:

- Replace SQLite with PostgreSQL
- Add Redis for caching and real-time features
- Implement message queue (RabbitMQ/Kafka) for event processing
- Add horizontal scaling for backend services
- Implement proper logging and monitoring (ELK stack)
- Add rate limiting and security measures

---

## Appendix A: File Structure

```
freight-exception-demo/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── database.py             # Database connection
│   ├── decision_engine.py      # AI decision logic
│   ├── risk_calculator.py      # Risk scoring
│   ├── event_simulator.py      # Demo event generation
│   ├── notification_service.py # Notification logic
│   ├── routers/
│   │   ├── exceptions.py       # Exception endpoints
│   │   ├── shipments.py        # Shipment endpoints
│   │   ├── decisions.py        # Decision endpoints
│   │   └── demo.py             # Demo control endpoints
│   ├── tests/
│   ├── requirements.txt
│   └── init_db.py              # Database initialization
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── CaseCard.tsx
│   │   │   ├── CaseDetailView.tsx
│   │   │   ├── TimelineView.tsx
│   │   │   ├── ApprovalInterface.tsx
│   │   │   └── MetricsPanel.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useExceptions.ts
│   │   │   └── useDemoControl.ts
│   │   ├── services/
│   │   │   └── api.ts          # API client
│   │   ├── types/
│   │   │   └── index.ts        # TypeScript types
│   │   └── utils/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── docker-compose.yml
├── README.md
└── TECHNICAL_DESIGN.md         # This document
```

---

## Appendix B: API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/exceptions` | GET | List all exceptions |
| `/api/exceptions/{id}` | GET | Get exception details |
| `/api/exceptions/{id}/approve` | POST | Approve decision |
| `/api/shipments` | GET | List shipments |
| `/api/shipments/{id}` | GET | Get shipment details |
| `/api/decisions/{exception_id}` | GET | Get decision options |
| `/api/demo/start` | POST | Start demo |
| `/api/demo/reset` | POST | Reset demo |
| `/ws` | WebSocket | Real-time updates |

---

**End of Technical Design Document**

# Frontend - React Application

## 🚧 Coming Soon

This directory will contain the React + TypeScript frontend for the Freight Exception Management demo.

## Planned Structure

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── App.tsx                    # Main app component
│   ├── main.tsx                   # Entry point
│   ├── components/
│   │   ├── Dashboard.tsx          # Main dashboard
│   │   ├── CaseCard.tsx           # Exception case card
│   │   ├── CaseDetailView.tsx     # Detailed case view
│   │   ├── TimelineView.tsx       # Event timeline
│   │   ├── ApprovalInterface.tsx  # Coordinator approval panel
│   │   ├── MetricsPanel.tsx       # Summary metrics
│   │   └── DemoControlBar.tsx     # Demo playback controls
│   ├── hooks/
│   │   ├── useWebSocket.ts        # WebSocket connection
│   │   ├── useExceptions.ts       # Exception data management
│   │   └── useDemoControl.ts      # Demo mode control
│   ├── services/
│   │   └── api.ts                 # API client
│   ├── types/
│   │   └── index.ts               # TypeScript type definitions
│   ├── utils/
│   │   ├── formatters.ts          # Data formatting utilities
│   │   └── constants.ts           # App constants
│   └── styles/
│       └── globals.css            # Global styles
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── README.md
```

## Tech Stack

- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **WebSocket**: Socket.io Client
- **Routing**: React Router v6

## Key Features

1. **Real-time Dashboard**: Live updates via WebSocket
2. **Interactive Timeline**: Visual representation of exception flow
3. **Approval Interface**: Coordinator decision-making panel
4. **Demo Modes**: Auto-play, step-by-step, interactive
5. **Responsive Design**: Works on desktop and mobile

## Component Highlights

### Dashboard
- Overview of all active exceptions
- Summary metrics (resolution time, savings, etc.)
- Three case cards (low, medium, high risk)
- Real-time status updates

### CaseCard
```tsx
interface CaseCardProps {
  exception: Exception;
  shipment: Shipment;
  onClick: () => void;
}

// Displays:
// - Risk indicator (🟢🟡🔴)
// - Shipment details
// - Current status
// - Mini timeline
// - Key metrics
```

### TimelineView
```tsx
interface TimelineViewProps {
  exception: Exception;
  events: Event[];
}

// Features:
// - Vertical timeline with milestones
// - Color-coded events
// - Expandable details
// - Auto-scroll to current step
```

### ApprovalInterface
```tsx
interface ApprovalInterfaceProps {
  exception: Exception;
  decision: Decision;
  onApprove: (option: string, notes: string) => void;
  onModify: (customPlan: CustomPlan) => void;
  onReject: (reason: string) => void;
}

// Displays:
// - Exception summary
// - AI diagnosis with confidence
// - Solution options comparison
// - Customer notification preview
// - Approval actions
```

## Color Scheme

```css
/* Risk Levels */
--risk-low: #10b981;      /* Green */
--risk-medium: #f59e0b;   /* Amber */
--risk-high: #ef4444;     /* Red */

/* Status Colors */
--status-resolved: #10b981;
--status-pending: #f59e0b;
--status-executing: #3b82f6;
--status-escalated: #ef4444;

/* UI Colors */
--primary: #2563eb;
--secondary: #64748b;
--background: #f8fafc;
--surface: #ffffff;
--border: #e2e8f0;
```

## Development Setup (Coming Soon)

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint code
npm run lint
```

## Environment Variables

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Demo Modes

### Auto-play Mode
- System automatically progresses through all cases
- Real-time animations
- Configurable playback speed

### Step-by-step Mode
- User clicks "Next" to advance
- Pause at each decision point
- Perfect for presentations

### Interactive Mode
- User acts as coordinator
- Approve/modify/reject decisions
- See the impact of choices

---

**Status**: 📋 Planning  
**Target Completion**: Week 2-3

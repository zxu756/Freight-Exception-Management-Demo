# Freight Exception Management System - Interactive Demo

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Demo](https://img.shields.io/badge/Status-Demo-blue.svg)]()

An interactive demonstration of an AI-powered freight exception management system for Southern Freight, showcasing automated detection, diagnosis, and resolution of logistics exceptions across multiple risk levels.

## 🎯 Project Overview

This demo showcases how modern AI can transform freight exception handling from a reactive, manual process into a proactive, intelligent system that:

- **Detects** exceptions within minutes instead of hours
- **Diagnoses** root causes with high confidence using AI
- **Resolves** low-risk cases automatically
- **Escalates** high-risk cases to humans with complete context
- **Communicates** proactively with customers before they call

## 🎬 Demo Features

### Three Live Case Studies

| Case | Risk Level | Scenario | Handling |
|------|-----------|----------|----------|
| **Case 1** | 🟢 Low | Traffic delay on road transport | Fully automated - 2 min resolution |
| **Case 2** | 🟡 Medium | Ferry cancellation requiring reroute | Human approval required - 14 min |
| **Case 3** | 🔴 High | Cargo damage with insurance claim | Team collaboration - 5 hours |

### Interactive Modes

- **🎥 Auto-play Mode**: Watch the system handle all three cases automatically
- **👆 Step-by-step Mode**: Click through each stage of exception handling
- **🎮 Interactive Mode**: Act as a coordinator and approve/modify AI recommendations

## 📊 Business Impact (Projected)

- ⏱️ **50% reduction** in coordinator reactive workload
- 📉 **30% reduction** in SLA breaches
- 💰 **~$24,000 NZD/month** cost savings
- 😊 **70%+ proactive** customer notifications (vs. inbound complaints)
- ⚡ **15 minutes** average exception detection time (from hours)

## 🏗️ Technology Stack

### Frontend
- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **WebSocket** for real-time updates

### Backend
- **Python FastAPI** for high-performance API
- **SQLAlchemy** ORM with SQLite
- **Socket.io** for WebSocket communication
- **Pydantic** for data validation

### Demo Infrastructure
- **Event Simulator** for realistic tracking events
- **AI Decision Engine** with risk-based routing
- **Mock External APIs** (carriers, weather, ports)

## 📁 Project Structure

```
Freight-Exception-Management-Demo/
├── README.md                          # This file
├── DEMO_TECHNICAL_DESIGN.md          # Complete technical specification
├── backend/                          # FastAPI backend (coming soon)
│   ├── main.py
│   ├── models.py
│   ├── decision_engine.py
│   └── ...
├── frontend/                         # React frontend (coming soon)
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── ...
│   └── package.json
└── docker-compose.yml               # Container orchestration (coming soon)
```

## 📖 Documentation

### [📘 Complete Technical Design Document](./DEMO_TECHNICAL_DESIGN.md)

This comprehensive document includes:

1. **System Architecture** - Component design and data flow
2. **Database Schema** - Complete SQL schema with relationships
3. **API Specification** - REST endpoints and WebSocket events
4. **Frontend Components** - React component hierarchy and specs
5. **Three Demo Cases** - Detailed scenarios with timelines
6. **AI Decision Engine** - Risk scoring and routing logic
7. **Implementation Roadmap** - 4-week development plan
8. **Deployment Guide** - Local, Docker, and cloud options

## 🚀 Quick Start (Coming Soon)

```bash
# Clone the repository
git clone https://github.com/zxu756/Freight-Exception-Management-Demo.git
cd Freight-Exception-Management-Demo

# Run with Docker Compose
docker-compose up

# Access demo at http://localhost:5173
```

## 🎯 Use Cases

This demo is designed for:

- **Business stakeholders** evaluating AI automation opportunities
- **Technical teams** planning logistics system modernization
- **Product managers** designing exception management workflows
- **Investors** assessing logistics technology solutions
- **Students** learning about AI in supply chain operations

## 🔮 Future Roadmap

### Phase 1: Demo Implementation (4 weeks)
- ✅ Technical design completed
- ⏳ Backend API development
- ⏳ Frontend dashboard implementation
- ⏳ Three case scenarios with data

### Phase 2: Enhanced Features
- Real AI integration (OpenAI/Anthropic API)
- Predictive exception detection
- Multi-language support (English/中文)
- Mobile responsive design
- Export and reporting features

### Phase 3: Production Ready
- PostgreSQL database migration
- Real carrier API integration
- Authentication and authorization
- Monitoring and analytics
- Horizontal scaling support

## 📊 Related Research

This demo is based on research conducted for Southern Freight, New Zealand's logistics provider. See the research documents in the related repository:

- [Scenario Analysis Report](../Kratos_Freight_Exception_Agent/docs/zxu756/Scenario_4_NZ_Company_Analysis_Bilingual_Report_zxu756.md)
- Competitive analysis of NZ logistics technology providers
- SLA benchmarking and recommendations

## 🤝 Contributing

This is currently a demonstration project. Once the initial implementation is complete, we welcome contributions:

- 🐛 Bug reports and fixes
- ✨ Feature suggestions
- 📖 Documentation improvements
- 🌍 Translations

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Team

**Project Lead**: zxu756  
**Research Context**: Southern Freight Exception Management Agent

## 📞 Contact

- GitHub Issues: [Report an issue](https://github.com/zxu756/Freight-Exception-Management-Demo/issues)
- GitHub Discussions: [Join the discussion](https://github.com/zxu756/Freight-Exception-Management-Demo/discussions)

---

## 🎓 Educational Value

This demo demonstrates key concepts in:

- **AI/ML in Operations**: Risk scoring, decision routing, confidence thresholds
- **Event-Driven Architecture**: WebSocket real-time updates, event sourcing
- **Human-in-the-Loop Systems**: Balancing automation with human judgment
- **Supply Chain Technology**: TMS integration, carrier APIs, exception handling
- **Full-Stack Development**: React + FastAPI modern web application

---

**⭐ Star this repo if you find it useful!**

**🔗 Related Project**: [Kratos Freight Exception Agent Research](https://github.com/zxu756/Kratos-Freight-Exception-Agent)

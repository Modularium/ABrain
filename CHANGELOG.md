# Changelog

All notable changes to this project are documented in this file.

## v1.1.0 - 2026-04-10 Foundations Release

### Included
- canonical agent model with `AgentDescriptor`, `Capability` and `AgentRegistry`
- Flowise import/export interoperability layer as a non-runtime UI bridge
- decision layer with `Planner`, `CandidateFilter`, always-on `NeuralPolicyModel` and `RoutingEngine`
- execution layer with static adapter registry, `ExecutionEngine`, agent creation and feedback loop
- learning system with dataset, reward model, online updater, trainer and explicit persistence helpers
- best-effort learning path so post-execution training failures do not break successful `run_task(...)` results
- updated release, architecture and setup documentation for the new ABrain foundations stack
- CI gates for `tests/decision`, `tests/execution`, `tests/adapters`, `tests/core`, `tests/services` and `py_compile`

### Not Included
- multi-agent orchestration
- broad MCP tool expansion
- advanced RL or continuous background training
- production-grade native adapters for all external systems

### Naming And Identity
- visible product identity is now consistently documented as `ABrain`
- technical slugs such as `abrain` and `abrain` remain where changing them would risk packaging or deployment regressions

## v1.0.0 - 2025-07-21 🚀 **Full-Stack Release**

### 🎉 Major Features
- **🌟 Complete Full-Stack Integration**: React Frontend + FastAPI Backend Bridge
- **💻 Modern React UI**: Built with React 19, TypeScript, Tailwind CSS
- **⚡ One-Click Setup**: Automated system setup with `start_fullstack.sh`
- **🔄 Real-time Communication**: WebSocket support for chat functionality
- **📊 Comprehensive Dashboard**: System metrics, agent management, task tracking
- **🔐 Authentication System**: Token-based security with demo login

### 🎨 Frontend Features
- Modern, responsive web interface (`frontend/agent-ui/`)
- Agent management with real-time status
- Task creation and monitoring
- Interactive chat interface
- System metrics dashboard
- Mobile-friendly design with Tailwind CSS

### 🚀 Backend Features
- FastAPI bridge server (`server/main.py`)
- RESTful API with OpenAPI documentation
- Agent orchestration and management
- Real-time WebSocket chat
- System health monitoring
- Mock mode for development

### 🛠️ Developer Experience
- **Automated Testing**: `test_system.sh` for comprehensive system validation
- **Status Monitoring**: `status_check.sh` for real-time status checks  
- **Docker Support**: Full containerization with docker-compose
- **Development Tools**: Hot reload, TypeScript support, ESLint

### 📦 New Components
- `server/main.py` - Main backend bridge server
- `frontend/agent-ui/` - Complete React application
- `start_fullstack.sh` - Automated startup script
- `test_system.sh` - System testing script
- `status_check.sh` - Status monitoring script
- `FULLSTACK_README.md` - Detailed setup documentation

### 🔧 Technical Improvements
- Modern Python packaging with requirements.txt
- Vite-based frontend build system
- Comprehensive error handling and logging
- Responsive UI with dark/light theme support
- Type-safe API communication with React Query

### 🌐 API Endpoints
- `/auth/login` - User authentication
- `/agents` - Agent management CRUD
- `/tasks` - Task management CRUD  
- `/chat/sessions/{id}/messages` - Chat functionality
- `/metrics/system` - System monitoring
- `/docs` - Interactive API documentation

### ⚡ Quick Start
```bash
git clone https://github.com/EcoSphereNetwork/ABrain.git
cd ABrain
bash start_fullstack.sh
# Access: http://localhost:3001
```

### 📊 System Requirements
- Python 3.10+
- Node.js 18+
- 4+ GB RAM
- Modern web browser

---

## Previous Versions

## v1.0.0-beta
- Deployment-Skripte und Dokumentation fertiggestellt
- Erste Beta-Version mit stabilem SDK und CLI
- HTTP-Schnittstellen eingefroren

## v1.0.1
- Bidirektionale Flowise-Integration
- Plugins akzeptieren `path`, `method`, `headers` und `timeout`
- Tests und Type-Hints fuer Plugins ergaenzt

## v1.0.2-rc
- Verbesserte Flowise-Komponente mit `auth`-Unterstützung und Fehlerbehandlung
- Beispiel-Flows und Screenshot hinzugefügt
- Quickstart- und Troubleshooting-Abschnitte in der Dokumentation
- Integrations-Builds generieren JavaScript-Dateien in `dist/`
- Version als Release Candidate markiert

## v1.0.2
- Stable-Tag für die Flowise-Integration
- Troubleshooting und Known-Issues ergänzt
- Changelog und Release-Notes aktualisiert

## v1.0.3
- Flowise-Export über `GET /agents/{id}?format=flowise` finalisiert
- Fehlercodes und Dokumentation ergänzt

## v0.9.0-mcp
- Abschluss der MCP-Migration
- Dokumentation überarbeitet
- Docker-Compose für Kernservices
- Tests und Linting eingerichtet

## Frühere Phasen
- Phase 1: Architektur-Blueprint
- Phase 2: Kernservices
- Phase 3: Wissens- und LLM-Services
- Phase 4: Qualitätssicherung

# Agent-NN 🤖✨
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![Node](https://img.shields.io/badge/node.js-18+-green)
![React](https://img.shields.io/badge/react-19.1-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.116-green)

**Agent-NN** ist ein modernes Multi-Agent-System mit integrierten neuronalen Netzen, einer intuitiven React-UI und einer robusten FastAPI-Backend-Architektur. Das System ermöglicht nahtlose KI-Agent-Orchestrierung mit einer benutzerfreundlichen Weboberfläche.

🌐 **[Live Demo](http://localhost:3001)** | 📚 **[Dokumentation](docs/)** | 🚀 **[Quick Start](#-quick-start)**

## ✨ Hauptfeatures

- 🤖 **Multi-Agent-System** - Intelligente Agent-Orchestrierung
- 💬 **Interaktive Chat-UI** - Echtzeit-Kommunikation mit Agenten
- 📊 **Dashboard & Monitoring** - Umfassende System-Überwachung
- 🔐 **Sichere Authentifizierung** - Token-basierte Sicherheit
- 🐳 **Docker-Ready** - Vollständige Containerisierung
- ⚡ **Ein-Klick-Setup** - Automatisierte Installation und Konfiguration
- 🎨 **Modernes UI/UX** - Tailwind CSS + TypeScript
- 🎯 **Moderne Fullstack-Architektur** - React Frontend + FastAPI Backend
 

## 🚀 Quick Start

### Automatisches Full-Stack Setup (Empfohlen)

```bash
# Repository klonen
git clone https://github.com/EcoSphereNetwork/Agent-NN.git
cd Agent-NN

# Setup
bash ./scripts/setup.sh --full

# For other options
# bash ./scripts/setup.sh --help

# Sollte der Poetry-Schritt scheitern, hilft oft ein erneuter Aufruf mit
#
# ```bash
# poetry install --no-root
# ```

# System testen
bash test_system.sh

# Vollständiges System starten
bash start_fullstack.sh
```

Das war's! Das System läuft nun auf:
- **Frontend**: http://localhost:3001 (oder 3000)
- **Backend API**: http://localhost:8000
- **API Dokumentation**: http://localhost:8000/docs

### Login-Daten
- **Email**: `demo@agent-nn.com`
- **Passwort**: `demo`

## 📋 Systemvoraussetzungen

### Erforderlich
- **Python 3.10+** mit Virtual Environment
- **Node.js 18+** mit npm
- **Git**
- **4+ GB RAM** (8 GB empfohlen)
- **5+ GB freier Speicherplatz**

### Optional für erweiterte Features
- **Docker** mit Docker Compose
- **Poetry** für Python-Paket-Management

### Plattformkompatibilität
✅ Ubuntu 20.04+  
✅ macOS 11+  
✅ Windows 10+ (WSL2 empfohlen)  
✅ Debian 11+  
✅ CentOS/RHEL 8+

## 🏗️ Architektur

```mermaid
graph TD
    U[React Frontend :3001] -->|HTTP/WebSocket| B[FastAPI Bridge :8000]
    B -->|Agent Orchestration| A[Agent-NN Core]
    A --> S[Supervisor Agent]
    A --> C[Chatbot Agent]
    A --> M[Agent Manager]
    A --> D[Monitoring System]
    
    B --> Auth[Authentication]
    B --> API[REST API]
    B --> WS[WebSocket Chat]
    
    style U fill:#61dafb
    style B fill:#009688
    style A fill:#ff6b6b
    style S fill:#4ecdc4
```

### Komponenten-Übersicht

| Komponente | Beschreibung | Port | Status |
|------------|--------------|------|--------|
| **React Frontend** | Moderne Web-UI mit TypeScript | 3001/3000 | ✅ Aktiv |
| **FastAPI Bridge** | API-Server als Backend-Bridge | 8000 | ✅ Aktiv |
| **Agent-NN Core** | Haupt-Agent-System | - | ✅ Integriert |
| **Authentication** | Token-basierte Sicherheit | - | ✅ Mock/Demo |
| **WebSocket Chat** | Echtzeit-Kommunikation | 8000/ws | ✅ Aktiv |

## 💻 Verwendung

### 1. System starten
```bash
# Vollständiges System
bash start_fullstack.sh

# Oder manuell:
# Backend
source .venv/bin/activate && python server/main.py

# Frontend (neues Terminal)
cd frontend/agent-ui && npm run dev
```

### 2. Web-Interface verwenden
1. Öffne http://localhost:3001
2. Melde dich mit `demo@agent-nn.com` / `demo` an
3. Erkunde das Dashboard, Agenten, Tasks und Chat

### 3. API direkt verwenden
```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@agent-nn.com","password":"demo"}'

# Agenten auflisten
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/agents

# Task erstellen
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Task","description":"Analysiere diese Daten","priority":"medium"}'
```

## 📱 Frontend Features

### Dashboard
- 📈 System-Metriken in Echtzeit
- 🎯 Agent-Performance-Übersicht
- 📋 Task-Status und -Verlauf
- 🔔 Benachrichtigungen und Alerts

### Agent-Management
- 👥 Agent-Liste mit Status
- ⚙️ Agent-Konfiguration
- 📊 Performance-Metriken
- 🔄 Agent-Lifecycle-Management

### Task-Management
- ➕ Task-Erstellung mit Prioritäten
- 📝 Task-Details und Fortschritt
- 🏷️ Kategorisierung und Filter
- 📈 Ausführungsstatistiken

### Chat-Interface
- 💬 Echtzeit-Chat mit Agenten
- 🎭 Kontext-bewusste Unterhaltungen
- 📎 Datei-Upload (geplant)
- 🔍 Chat-Verlauf und Suche

## 🛠️ Entwicklung

### Frontend-Entwicklung
```bash
cd frontend/agent-ui

# Abhängigkeiten installieren
npm install

# Development Server
npm run dev

# Production Build
npm run build

# Linting & Testing
npm run lint
npm run type-check
```

### Backend-Entwicklung
```bash
# Virtual Environment aktivieren
source .venv/bin/activate

# Development Server mit Auto-reload
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

# Dependencies installieren
pip install -r requirements.txt
```

### Tech Stack
- **Frontend**: React 19, TypeScript, Tailwind CSS, Vite
- **State Management**: Zustand, React Query
- **Backend**: FastAPI, Python 3.10+, Pydantic
- **UI Components**: Headless UI, Heroicons, Framer Motion
- **Build Tools**: Vite, ESBuild, PostCSS

## 🧪 Tests & Qualitätssicherung

### Vollständiger Systemtest
```bash
# Automatisierte Tests aller Komponenten
bash test_system.sh
```

### Einzelne Tests
```bash
# Backend-Tests
cd /home/dev/Agent-NN
source .venv/bin/activate
python -m pytest tests/

# Frontend-Tests
cd frontend/agent-ui
npm run test

# E2E-Tests
npm run test:e2e
```

### Status-Monitoring
```bash
# Aktueller System-Status
bash status_check.sh

# Kontinuierliche Überwachung
watch -n 5 'bash status_check.sh'
```

## 🐳 Docker Deployment

### Development
```bash
# Standard Docker Compose
docker compose up --build -d

# Mit spezifischer Konfiguration
docker compose -f docker-compose.yml up --build -d

# Services stoppen
docker compose down
```

### Production
```bash
# Production Setup
cp .env.production .env
docker compose -f docker-compose.production.yml up -d

# Mit Monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

## ⚙️ Konfiguration

### Umgebungsvariablen (.env)
```bash
# API-Konfiguration
VITE_API_URL=http://localhost:8000
API_PORT=8000
FRONTEND_PORT=3001

# Agent-NN Core
OPENAI_API_KEY=your_openai_key
LLM_BACKEND=openai
LLM_MODEL=gpt-3.5-turbo

# Sicherheit
JWT_SECRET=your_secure_secret
AUTH_ENABLED=true

# Datenbank (optional)
DATABASE_URL=postgresql://user:pass@localhost:5432/agentnn
```

### Frontend-Konfiguration
```typescript
// src/store/useAppStore.ts
const defaultSettings: AppSettings = {
  api: {
    baseUrl: 'http://localhost:8000',
    timeout: 30000,
    retries: 3
  },
  theme: 'light',
  // ...
}
```

## 📊 Monitoring & Observability

### System-Metriken
- 🖥️ CPU & Memory Usage
- 🔄 Request/Response Times
- 📈 Agent Performance
- 🚨 Error Rates
- 💾 Storage Usage

### Logs
```bash
# Backend-Logs
tail -f backend.log

# Frontend-Logs
tail -f frontend.log

# Docker-Logs
docker compose logs -f
```

### Health Checks
```bash
# Backend Health
curl http://localhost:8000/health

# System Status
curl http://localhost:8000/system/health

# Metriken
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/metrics/system
```

## 🔧 Troubleshooting

### Häufige Probleme

1. **Port-Konflikte**
   ```bash
   # Prozesse auf Ports finden
   netstat -tulnp | grep :8000
   netstat -tulnp | grep :3000
   
   # Ports freigeben
   kill -9 <PID>
   ```

2. **Frontend Build-Fehler**
   ```bash
   cd frontend/agent-ui
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

3. **Backend-Probleme**
   ```bash
   # Virtual Environment neu erstellen
   rm -rf .venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Authentifizierung schlägt fehl**
   - Stelle sicher, dass die korrekten Login-Daten verwendet werden
   - Überprüfe Browser-Cookies und Local Storage
   - Teste API-Endpunkte direkt mit curl

### Debug-Modus
```bash
# Backend mit Debug-Logging
DEBUG=1 python server/main.py

# Frontend mit Source Maps
cd frontend/agent-ui
npm run dev -- --debug
```

## 📚 Dokumentation

- **[Vollständige Dokumentation](FULLSTACK_README.md)** - Detaillierte Setup-Anleitung
- **[API-Dokumentation](http://localhost:8000/docs)** - Swagger UI (wenn Server läuft)
- **[Konfiguration](docs/config_reference.md)** - Konfigurationsreferenz
- **[Deployment](docs/deployment.md)** - Produktions-Deployment
- **[Troubleshooting](docs/troubleshooting.md)** - Problemlösungen
- **[Contributing](CONTRIBUTING.md)** - Entwickler-Guide

## 🗺️ Roadmap

### Version 1.1 (Q1 2025)
- [ ] Erweiterte Agent-Typen und -Fähigkeiten
- [ ] File Upload & Processing
- [ ] Multi-Language Support
- [ ] Enhanced Monitoring Dashboard

### Version 1.2 (Q2 2025)
- [ ] Real-time Collaboration Features
- [ ] Advanced Agent Orchestration
- [ ] Plugin System for Custom Agents
- [ ] Performance Optimizations

### Version 2.0 (Q3 2025)
- [ ] Graph-based Agent Workflows
- [ ] Advanced ML Model Integration
- [ ] Enterprise Features & SSO
- [ ] Mobile App

Siehe [ROADMAP.md](ROADMAP.md) für Details.

## 🤝 Contributing

Wir freuen uns über Beiträge! Bitte lies [CONTRIBUTING.md](CONTRIBUTING.md) für Details zu:

- Code-Style Guidelines
- Pull Request Process
- Issue Templates
- Development Setup

### Development Setup
```bash
# Repository forken und klonen
git clone https://github.com/YOUR_USERNAME/Agent-NN.git
cd Agent-NN

# Development Environment einrichten
bash test_system.sh
bash start_fullstack.sh

# Feature Branch erstellen
git checkout -b feature/amazing-feature

# Änderungen testen
bash test_system.sh

# Pull Request erstellen
```

## 🛡️ Sicherheit

- 🔐 **Authentifizierung**: Token-basierte API-Sicherheit
- 🛡️ **CORS**: Konfigurierbare Cross-Origin-Policies
- 🔑 **Environment Secrets**: Sichere Verwaltung von API-Keys
- 🚫 **Input Validation**: Umfassende Request-Validierung

Für Sicherheitsprobleme, erstelle bitte ein Issue oder kontaktiere das Team direkt.

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) für Details.

## 🆘 Support & Community

- **🐛 Bug Reports**: [GitHub Issues](https://github.com/EcoSphereNetwork/Agent-NN/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/EcoSphereNetwork/Agent-NN/discussions)
- **📖 Dokumentation**: [docs/](docs/)
- **💬 Community**: [Discord Server](https://discord.gg/agent-nn) (geplant)

## 🏆 Danksagungen

- React Team für das ausgezeichnete Frontend-Framework
- FastAPI Team für die moderne Python-Web-API-Lösung
- Open Source Community für die verwendeten Bibliotheken
- Alle Contributors und Beta-Tester

---

**Agent-NN v1.0.0**: Moderne Multi-Agent-KI mit Full-Stack-Web-Interface 🚀

*Entwickelt mit ❤️ für die Zukunft der KI-Anwendungen*

---

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/EcoSphereNetwork/Agent-NN?style=social)](https://github.com/EcoSphereNetwork/Agent-NN/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/EcoSphereNetwork/Agent-NN?style=social)](https://github.com/EcoSphereNetwork/Agent-NN/network/members)
[![GitHub issues](https://img.shields.io/github/issues/EcoSphereNetwork/Agent-NN)](https://github.com/EcoSphereNetwork/Agent-NN/issues)

</div>

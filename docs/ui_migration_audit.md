# UI Migration Audit

> Status: Historisches Audit. Diese Datei dokumentiert frühere UI-Konsolidierungen und ist keine vollständige Aussage darüber, welche Frontend-/Monitoring-Pfade heute als primäre Referenz gelten.

This document tracks legacy UI components and their migration status to the consolidated React interface under `frontend/agent-ui`.

## Legacy Sources

- **frontend/** (root React project using Smolitux-UI)
  - Components: `AgentCard`, `ChatMessage`, `Navbar`, `SettingsForm`, `Sidebar`, `TaskItem`
  - Pages: `HomePage`, `ChatPage`, `AgentsPage`, `TasksPage`, `SettingsPage`
  - Layout: `MainLayout`
- **monitoring/monitoring/dashboard/** (monitoring React app)
  - Numerous dashboard components such as `MetricsChart`, `AgentsPanel`, `SystemOverviewPanel` and others
  - Layout elements like `DashboardLayout`, `Sidebar`, `Header`, `Footer`
  - Pages: `Dashboard`, `LoginPage`, `NotFoundPage`
  - Utility widgets: `DocumentViewer`, `NotificationSystem`, etc.
- **monitoring/grafana/**
  - Grafana provisioning with `agentnn.json` dashboard

## Migration Status

| Component/Module | Origin | Status |
|------------------|--------|--------|
| Chat interface | `frontend/src/pages/ChatPage.tsx` | Migrated to `agent-ui/ChatPage` |
| Agents listing | `frontend/src/pages/AgentsPage.tsx` | Migrated to `agent-ui/AgentsPage` |
| Tasks overview | `frontend/src/pages/TasksPage.tsx` | Migrated to `agent-ui/TasksPage` |
| Settings form | `frontend/src/pages/SettingsPage.tsx` | Migrated to `agent-ui/SettingsPage` |
| Home page | `frontend/src/pages/HomePage.tsx` | Dropped (replaced by chat start page) |
| Navbar component | `frontend/src/components/Navbar.tsx` | Dropped (replaced by sidebar) |
| Monitoring dashboard app | `monitoring/monitoring/dashboard` | Archived, key panels replicated in agent-ui |
| Grafana panels | `monitoring/grafana` | Embedded via `/metrics` route |

All other minor widgets from the legacy dashboard have been archived under `archive/ui_legacy`.

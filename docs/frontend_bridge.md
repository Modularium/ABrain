# Frontend Bridge

This document describes how the `agent-ui` frontend connects to the ABrain backend services.

## Development

```bash
cd frontend/agent-ui
npm install
npm run dev
```

The development server expects an environment variable `VITE_API_URL` defined in `.env.local` pointing to the API gateway (e.g. `http://localhost:8080`).

Phase M uses the API gateway as the browser-facing control-plane boundary. The main UI reads and writes through thin `/control-plane/*` routes that delegate to `services/core.py`.

## Build & Deployment

To create a production build run:

```bash
npm run build
```

The compiled files are written to `frontend/dist/` and can be served via any static file server or the provided nginx container in `docker-compose.yml`.

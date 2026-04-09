# OpenAPI Overview

Status: historical service snapshot, not a foundations release contract.

Der folgende Überblick beschreibt weiter wichtige Service-Routen im Repository, ist aber keine vollständige Spezifikation des neuen Foundations-Releases. Für den aktuellen Kern sind `services/core.py`, die aktiven FastAPI-Apps und die Architektur-Dokumente maßgeblich.

| Method | Path | Description | Tags |
|-------|------|-------------|------|
| **GET** | `/agents` | List all registered agents | #agent #core |
| **POST** | `/register` | Register a new agent | #agent |
| **GET** | `/agents/{agent_id}` | Get agent by id | #agent |
| **POST** | `/task` | Queue a task for processing | #task |
| **POST** | `/start_session` | Start a new session | #session |
| **POST** | `/update_context` | Update conversation context | #session |
| **GET** | `/context/{session_id}` | Retrieve session context | #session |
| **POST** | `/add_document` | Add document to vector store | #vector |
| **POST** | `/vector_search` | Search documents via embeddings | #vector |
| **POST** | `/generate` | Generate text with selected model | #model |
| **POST** | `/embed` | Create vector embeddings | #vector |

# Architecture Overview

ABrain is being refactored into a Modular Control Plane. Instead of one monolithic agent process, separate services take care of orchestration, knowledge retrieval and task execution.

## Core Repository Folders

- **agents/** – legacy agent implementations (will evolve into worker services)
- **llm_models/** – wrappers for various LLM backends
- **managers/** – utilities for model and agent management
- **datastores/** – vector store and agent specific databases
- **api/** – FastAPI endpoints
- **cli/** – command line interface utilities

## MCP Components

1. **Task-Dispatcher** – replaces the Supervisor and delegates tasks to workers
2. **Agent Registry** – stores available agent services and metadata
3. **Session Manager** – keeps conversation state centrally
4. **Worker Services** – domain specific executors running in their own processes
5. **Vector Store Service** – provides semantic search capabilities
6. **LLM Gateway** – unified interface to LLM providers
7. **User Manager Service** – handles user accounts and tokens

For an overview of the interaction between these services see `overview_mcp.md`.

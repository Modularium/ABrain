"""Generate OpenAPI specs for all MCP services."""
from importlib import import_module
from pathlib import Path
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

SERVICES = {
    "agent_registry": "mcp.agent_registry.main",
    "task_dispatcher": "mcp.task_dispatcher.main",
    "session_manager": "mcp.session_manager.main",
    "llm_gateway": "mcp.llm_gateway.main",
    "vector_store": "mcp.vector_store.main",
    "routing_agent": "mcp.routing_agent.main",
    "worker_dev": "mcp.worker_dev.main",
    "worker_loh": "mcp.worker_loh.main",
    "worker_openhands": "mcp.worker_openhands.main",
}

OUTPUT_DIR = Path("docs/api/openapi")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for name, module_path in SERVICES.items():
    try:
        mod = import_module(module_path)
        app = getattr(mod, "app")
        spec = app.openapi()
        out_file = OUTPUT_DIR / f"{name}.json"
        out_file.write_text(json.dumps(spec, indent=2))
        print(f"Wrote {out_file}")
    except Exception as exc:  # pragma: no cover - optional modules
        print(f"Failed to import {module_path}: {exc}")

"""Generate OpenAPI specs for the canonical services/* runtime."""
from importlib import import_module
from pathlib import Path
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

SERVICES = {
    "agent_registry": "services.agent_registry.main",
    "task_dispatcher": "services.task_dispatcher.main",
    "session_manager": "services.session_manager.main",
    "llm_gateway": "services.llm_gateway.main",
    "vector_store": "services.vector_store.main",
    "routing_agent": "services.routing_agent.main",
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

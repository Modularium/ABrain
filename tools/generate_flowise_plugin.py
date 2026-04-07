"""Generate a Flowise plugin manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_NODE_DIR = Path("integrations/flowise-nodes")
DEFAULT_OUTFILE = Path("flowise-plugin.json")


def get_version() -> str:
    """Return the latest git tag or fall back to VERSION file."""
    try:
        tag = (
            subprocess.check_output([
                "git",
                "describe",
                "--tags",
                "--abbrev=0",
            ],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
        )
        if tag:
            return tag.lstrip("v")
    except Exception:  # pragma: no cover - git missing
        pass
    return Path("VERSION").read_text().strip()


def collect_nodes(node_dir: Path) -> list[str]:
    """Return Flowise node names within *node_dir*."""
    nodes: list[str] = []
    for file in sorted(node_dir.glob("*.node.json")):
        data = json.loads(file.read_text())
        nodes.append(data.get("name", file.stem))
    return nodes


def generate_manifest(node_dir: Path, out_file: Path) -> Path:
    """Create plugin manifest from nodes in *node_dir* and store it at *out_file*."""
    version = get_version()
    manifest = {
        "name": "agent-nn",
        "version": version,
        "buildDate": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "compatibleFlowiseVersion": ">=1.3.0",
        "description": "ABrain Flowise nodes",
        "nodes": collect_nodes(node_dir),
        "author": "ABrain Team",
        "keywords": ["abrain", "agent-nn", "flowise", "plugin"],
        "repository": "https://github.com/EcoSphereNetwork/Agent-NN",
        "homepage": "https://github.com/EcoSphereNetwork/Agent-NN",
        "license": "MIT",
    }
    out_file.write_text(json.dumps(manifest, indent=2))
    Path("plugin_version.txt").write_text(version)
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate flowise-plugin.json")
    parser.add_argument("--node-dir", type=Path, default=DEFAULT_NODE_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTFILE)
    args = parser.parse_args()

    manifest_path = generate_manifest(args.node_dir, args.out)
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()

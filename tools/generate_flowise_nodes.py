"""Generate Flowise node definitions from a structured table."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def parse_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def parse_json(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return list(data)
    raise ValueError("JSON must contain a list of node entries")


def parse_markdown(path: Path) -> List[Dict[str, Any]]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    table_lines = [ln for ln in lines if ln.startswith("|")]
    if not table_lines:
        return []
    headers = [h.strip() for h in table_lines[0].strip("|").split("|")]
    entries: List[Dict[str, Any]] = []
    for line in table_lines[2:]:
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != len(headers):
            continue
        entry = {headers[i]: parts[i] for i in range(len(headers))}
        entries.append(entry)
    return entries


def parse_file(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        return parse_csv(path)
    if path.suffix.lower() in {".json"}:
        return parse_json(path)
    if path.suffix.lower() in {".md", ".markdown"}:
        return parse_markdown(path)
    raise ValueError(f"Unsupported input format: {path}")


def to_python(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return value


def generate_ts(name: str, inputs: List[Dict[str, Any]], path: str, method: str) -> str:
    params = []
    for inp in inputs:
        pname = inp.get("name")
        ptype = inp.get("type", "any")
        default = inp.get("default")
        if default is not None:
            params.append(f"    private {pname}: {ptype} = {json.dumps(default)}")
        else:
            params.append(f"    private {pname}: {ptype}")
    params_str = ",\n".join(params)

    return f"import axios, {{ AxiosRequestConfig }} from 'axios';\n\n" \
        f"export default class {name} {{\n" \
        f"  constructor(\n{params_str}\n  ) {{}}\n\n" \
        f"  async run(): Promise<any> {{\n" \
        f"    const url = `${{this.endpoint.replace(/\\/$/, '')}}{path}`;\n" \
        f"    const opts: AxiosRequestConfig = {{ url, method: '{method}', headers: this.headers }};\n" \
        f"    try {{\n" \
        f"      const response = await axios.request(opts);\n" \
        f"      return response.data;\n" \
        f"    }} catch (err: any) {{\n" \
        f"      return {{ error: err.message ?? String(err) }};\n" \
        f"    }}\n  }}\n}}\n"


def write_node(entry: Dict[str, Any], outdir: Path, ts: bool) -> None:
    name = entry.get("name")
    description = entry.get("description", "")
    inputs = entry.get("inputs")
    outputs = entry.get("outputs") or [{"name": "result", "type": "object"}]
    path_val = entry.get("path", "/")
    method = entry.get("method", "GET")
    icon = entry.get("icon", "user")
    color = entry.get("color", "#2375ec")
    category = entry.get("category", "ABrain")
    tooltip = entry.get("tooltip", description)
    doc_url = entry.get("documentationURL")

    if isinstance(inputs, str):
        inputs = to_python(inputs)
    if isinstance(outputs, str):
        outputs = to_python(outputs)
    if not isinstance(inputs, list):
        inputs = []
    node = {
        "name": name,
        "description": description,
        "inputs": inputs,
        "outputs": outputs,
        "icon": icon,
        "color": color,
        "category": category,
        "tooltip": tooltip,
    }
    if doc_url:
        node["documentationURL"] = doc_url
    outdir.mkdir(parents=True, exist_ok=True)
    node_file = outdir / f"{name}.node.json"
    node_file.write_text(json.dumps(node, indent=2))
    if ts:
        ts_file = outdir / f"{name}.ts"
        ts_file.write_text(generate_ts(name, inputs, path_val, method))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Flowise node definitions")
    parser.add_argument("table", type=Path, help="CSV, JSON or Markdown file with node specs")
    parser.add_argument("--outdir", type=Path, default=Path("integrations/flowise-nodes"))
    parser.add_argument("--typescript", action="store_true", help="Generate TypeScript skeleton")
    args = parser.parse_args()

    entries = parse_file(args.table)
    for entry in entries:
        write_node(entry, args.outdir, args.typescript)


if __name__ == "__main__":
    main()

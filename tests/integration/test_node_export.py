import json
import subprocess
import sys
import pytest


@pytest.mark.unit
def test_generate_flowise_nodes(tmp_path):
    table = tmp_path / "nodes.csv"
    table.write_text(
        "name,description,path,method,inputs,outputs\n"
        "EchoNode,Simple echo,/echo,POST,[{\"name\":\"endpoint\",\"type\":\"string\",\"default\":\"http://localhost\"},{\"name\":\"payload\",\"type\":\"object\"}],[{\"name\":\"result\",\"type\":\"object\"}]\n"
    )
    outdir = tmp_path / "out"
    subprocess.check_call([
        sys.executable,
        "tools/generate_flowise_nodes.py",
        str(table),
        "--typescript",
        "--outdir",
        str(outdir),
    ])
    node_path = outdir / "EchoNode.node.json"
    assert node_path.exists()
    data = json.loads(node_path.read_text())
    assert data["name"] == "EchoNode"
    assert (outdir / "EchoNode.ts").exists()
    assert data["icon"] == "user"
    assert data["color"] == "#2375ec"
    assert data["category"] == "ABrain"
    assert data["tooltip"] == "Simple echo"

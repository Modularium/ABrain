from pathlib import Path
import subprocess

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_script(script_name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / script_name), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_abrain_help_smoke_includes_control_plane_commands():
    result = _run_script("abrain", "help")

    assert result.returncode == 0
    assert "task run" in result.stdout
    assert "approval <action>" in result.stdout
    assert "health" in result.stdout


def test_abrain_health_help_smoke():
    result = _run_script("abrain", "health", "--help")

    assert result.returncode == 0
    assert "Kernstatus" in result.stdout
    assert "--json" in result.stdout


def test_agentnn_wrapper_remains_thin_alias():
    result = _run_script("agentnn", "help")

    assert result.returncode == 0
    assert "Kompatibilitätsalias aktiv: agentnn -> abrain" in result.stdout

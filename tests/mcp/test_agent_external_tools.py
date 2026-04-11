from pathlib import Path
import types
import httpx
from typer.testing import CliRunner
import pytest
import sys

sys.modules.setdefault(
    "mlflow",
    types.SimpleNamespace(
        start_run=lambda *a, **k: None,
        set_tag=lambda *a, **k: None,
        log_param=lambda *a, **k: None,
        log_metric=lambda *a, **k: None,
        set_tracking_uri=lambda *a, **k: None,
        tracking=types.SimpleNamespace(
            MlflowClient=lambda: types.SimpleNamespace(
                list_experiments=lambda: [],
                get_run=lambda run_id: types.SimpleNamespace(
                    info=types.SimpleNamespace(run_id=run_id, status="FINISHED"),
                    data=types.SimpleNamespace(metrics={}, params={}),
                ),
            )
        ),
    ),
)
sys.modules.setdefault(
    "agentnn.session.session_manager",
    types.SimpleNamespace(SessionManager=object),
)
sys.modules.setdefault(
    "agentnn.mcp.mcp_ws",
    types.SimpleNamespace(ws_server=types.SimpleNamespace(broadcast=lambda *a, **k: None)),
)
import sdk.nn_models as _nn  # noqa: E402
sys.modules.setdefault("sdk.cli.nn_models", _nn)
sys.modules.setdefault(
    "core.config", types.SimpleNamespace(settings=types.SimpleNamespace(model_dump=lambda: {}))
)
sys.modules.setdefault("jsonschema", types.SimpleNamespace(validate=lambda *a, **k: None))

from sdk.cli.main import app  # noqa: E402


@pytest.mark.unit
def test_register_and_invoke(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    import sdk.cli.commands.mcp as mcp_cmd
    mcp_cmd._CONFIG = home / ".agentnn" / "mcp_endpoints.json"
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, json, timeout=10: types.SimpleNamespace(
            status_code=200,
            text="ok",
            json=lambda: {"ok": True},
            raise_for_status=lambda: None,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["mcp", "register-endpoint", "demo", "http://example.com"])
    assert result.exit_code == 0
    file = home / ".agentnn" / "mcp_endpoints.json"
    assert file.exists()

    result = runner.invoke(app, ["mcp", "invoke", "demo.test", "--input", "{}"])
    assert result.exit_code == 0

    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, timeout=10: types.SimpleNamespace(
            status_code=200,
            text="[]",
            json=lambda: [],
            raise_for_status=lambda: None,
        ),
    )

    result = runner.invoke(app, ["mcp", "list-tools", "demo"])
    assert result.exit_code == 0

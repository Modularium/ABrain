import pytest

from mcp.plugin_agent_service.service import PluginAgentService


pytestmark = pytest.mark.unit


def test_legacy_plugin_service_rejects_dynamic_execution():
    service = PluginAgentService(plugin_dir="plugins")
    result = service.execute_tool(
        "filesystem",
        {"action": "write", "path": "note.txt", "content": "data"},
        {},
    )

    assert result["error_code"] == "legacy_tool_proxy_disabled"
    assert "fixed core tool surface" in result["message"]


def test_legacy_plugin_service_lists_no_executable_tools():
    service = PluginAgentService(plugin_dir="plugins")
    assert service.list_tools() == []

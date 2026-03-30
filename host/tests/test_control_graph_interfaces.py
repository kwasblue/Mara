import importlib
from unittest.mock import MagicMock

from mara_host.cli.context import CLIContext
from mara_host.mcp.runtime import MaraRuntime
from mara_host.mcp.tool_schema import get_tool_by_name


def _make_mock_client():
    """Create a mock client with the required bus interface."""
    client = MagicMock()
    client.bus = MagicMock()
    client.bus.subscribe = MagicMock()
    client.bus.unsubscribe = MagicMock()
    return client


def test_cli_context_exposes_control_graph_service_property():
    assert "control_graph_service" in dir(CLIContext)
    assert isinstance(getattr(CLIContext, "control_graph_service"), property)


def test_mcp_runtime_exposes_control_graph_service_property():
    assert "control_graph_service" in dir(MaraRuntime)
    assert isinstance(getattr(MaraRuntime, "control_graph_service"), property)


def test_tool_schema_exposes_control_graph_tools():
    expected = {
        "control_graph_upload",
        "control_graph_apply",
        "control_graph_status",
        "control_graph_enable",
        "control_graph_disable",
        "control_graph_clear",
    }
    for name in expected:
        tool = get_tool_by_name(name)
        assert tool is not None
        assert tool.service == "control_graph_service"


def test_cli_context_control_graph_service_binds_sensor_policy_provider():
    ctx = CLIContext(port="/dev/null")
    ctx._client = _make_mock_client()
    try:
        service = ctx.control_graph_service
        assert service is not None
        assert service._sensor_policy_provider is not None
    finally:
        service.close()
        ctx._control_graph_service = None


def test_robot_control_graph_service_binds_sensor_policy_provider():
    from mara_host.robot import Robot

    robot = Robot({
        "name": "testbot",
        "transport": {"type": "serial", "port": "/dev/null"},
    })
    robot._client = _make_mock_client()
    service = robot.control_graph_service
    assert service is not None
    assert service._sensor_policy_provider is not None
    service.close()


def test_generated_control_graph_defs_exports_typed_spec_objects():
    mod = importlib.import_module("mara_host.config.control_graph_defs")
    assert hasattr(mod, "CONTROL_GRAPH_SPEC_OBJECTS")
    assert hasattr(mod, "CONTROL_GRAPH_SPECS")
    assert mod.CONTROL_GRAPH_SPEC_OBJECTS["constant"].kind == "constant"
    assert mod.CONTROL_GRAPH_SPECS["constant"]["kind"] == "constant"

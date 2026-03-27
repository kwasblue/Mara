import inspect

from mara_host.mcp.tool_schema import get_tool_by_name


def test_cli_context_exposes_control_graph_service_property():
    from mara_host.cli.context import CLIContext

    assert "control_graph_service" in dir(CLIContext)
    assert isinstance(getattr(CLIContext, "control_graph_service"), property)


def test_mcp_runtime_exposes_control_graph_service_property():
    from mara_host.mcp.runtime import MaraRuntime

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
        assert tool is not None, name
        assert tool.service == "control_graph_service"


def test_cli_control_module_registers_graph_commands():
    from mara_host.cli.commands import control as control_module

    source = inspect.getsource(control_module)
    for command in [
        "graph-upload",
        "graph-apply",
        "graph-status",
        "graph-enable",
        "graph-disable",
        "graph-clear",
    ]:
        assert command in source

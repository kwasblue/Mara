# tests/test_mcp_plugins.py
"""Tests for the MCP plugin system."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from mara_host.mcp.plugin_loader import (
    load_plugin,
    load_plugins,
    get_plugin_tools,
    dispatch_plugin_tool,
    ToolDef,
    ToolParam,
    MaraPluginAPI,
)


class TestPluginLoader:
    """Tests for plugin loading."""

    def test_load_dict_style_plugin(self, tmp_path):
        """Test loading a plugin using dict-style tool definitions."""
        plugin_code = '''
TOOLS = [
    {
        "name": "my_test_tool",
        "description": "A test tool",
        "params": [
            {"name": "value", "type": "integer", "description": "A value"},
        ],
    }
]

async def my_test_tool(api, value: int) -> dict:
    return {"doubled": value * 2}
'''
        plugin_path = tmp_path / "dict_plugin.py"
        plugin_path.write_text(plugin_code)

        plugin = load_plugin(plugin_path)
        assert plugin is not None
        assert plugin.name == "dict_plugin"
        assert len(plugin.tools) == 1
        assert plugin.tools[0]["name"] == "my_test_tool"
        assert "my_test_tool" in plugin.handlers

    def test_load_dataclass_style_plugin(self, tmp_path):
        """Test loading a plugin using dataclass-style tool definitions."""
        plugin_code = '''
class DoubleTool(ToolDef):
    name = "double_value"
    description = "Double a number"
    params = [ToolParam("n", "integer", "Number to double")]

    async def run(self, api, n: int) -> dict:
        return {"result": n * 2}
'''
        plugin_path = tmp_path / "dataclass_plugin.py"
        plugin_path.write_text(plugin_code)

        plugin = load_plugin(plugin_path)
        assert plugin is not None
        assert plugin.name == "dataclass_plugin"
        assert len(plugin.tools) == 1
        assert plugin.tools[0]["name"] == "double_value"
        assert "double_value" in plugin.handlers

    def test_load_plugins_from_directory(self, tmp_path):
        """Test loading multiple plugins from a directory."""
        # Create plugin 1
        (tmp_path / "plugin_a.py").write_text('''
TOOLS = [{"name": "tool_a", "description": "Tool A", "params": []}]
async def tool_a(api) -> dict:
    return {"source": "a"}
''')

        # Create plugin 2
        (tmp_path / "plugin_b.py").write_text('''
TOOLS = [{"name": "tool_b", "description": "Tool B", "params": []}]
async def tool_b(api) -> dict:
    return {"source": "b"}
''')

        # Create ignored file (starts with _)
        (tmp_path / "_ignored.py").write_text('''
TOOLS = [{"name": "ignored", "description": "Ignored", "params": []}]
''')

        plugins = load_plugins(tmp_path)
        assert len(plugins) == 2
        names = {p.name for p in plugins}
        assert names == {"plugin_a", "plugin_b"}

    def test_get_plugin_tools_generates_mcp_tools(self, tmp_path):
        """Test that get_plugin_tools generates valid MCP Tool objects."""
        plugin_code = '''
TOOLS = [
    {
        "name": "greet",
        "description": "Greet someone",
        "params": [
            {"name": "name", "type": "string", "description": "Name to greet", "required": True},
            {"name": "formal", "type": "boolean", "description": "Use formal greeting", "required": False, "default": False},
        ],
    }
]
async def greet(api, name: str, formal: bool = False) -> dict:
    return {"greeting": f"Hello, {name}"}
'''
        plugin_path = tmp_path / "greet_plugin.py"
        plugin_path.write_text(plugin_code)

        plugins = load_plugins(tmp_path)
        tools = get_plugin_tools(plugins)

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "greet"
        assert "[plugin:greet_plugin]" in tool.description
        assert tool.inputSchema["type"] == "object"
        assert "name" in tool.inputSchema["properties"]
        assert "formal" in tool.inputSchema["properties"]
        assert "required" in tool.inputSchema
        assert "name" in tool.inputSchema["required"]

    def test_plugin_with_no_tools_returns_none(self, tmp_path):
        """Test that a plugin file with no tools returns None."""
        plugin_path = tmp_path / "empty.py"
        plugin_path.write_text("# No tools here\nx = 42\n")

        plugin = load_plugin(plugin_path)
        assert plugin is None

    def test_invalid_plugin_file_returns_none(self, tmp_path):
        """Test that an invalid Python file returns None."""
        plugin_path = tmp_path / "invalid.py"
        plugin_path.write_text("this is not valid python @#$%")

        plugin = load_plugin(plugin_path)
        assert plugin is None


class TestPluginDispatch:
    """Tests for plugin tool dispatch."""

    @pytest.fixture
    def mock_runtime(self):
        """Create a minimal mock runtime for testing."""
        class MockRuntime:
            is_connected = True
            state = type("State", (), {"robot_state": type("RS", (), {"value": "IDLE"})()})()
        return MockRuntime()

    @pytest.mark.asyncio
    async def test_dispatch_to_plugin_tool(self, tmp_path, mock_runtime):
        """Test dispatching a tool call to a plugin handler."""
        plugin_code = '''
TOOLS = [
    {
        "name": "add_numbers",
        "description": "Add two numbers",
        "params": [
            {"name": "a", "type": "integer"},
            {"name": "b", "type": "integer"},
        ],
    }
]
async def add_numbers(api, a: int, b: int) -> dict:
    return {"sum": a + b}
'''
        plugin_path = tmp_path / "math_plugin.py"
        plugin_path.write_text(plugin_code)

        plugins = load_plugins(tmp_path)
        result = await dispatch_plugin_tool(plugins, mock_runtime, "add_numbers", {"a": 5, "b": 3})

        assert result is not None
        assert result["sum"] == 8

    @pytest.mark.asyncio
    async def test_dispatch_returns_none_for_unknown_tool(self, tmp_path, mock_runtime):
        """Test that dispatch returns None for unknown tools."""
        plugins = load_plugins(tmp_path)  # Empty directory
        result = await dispatch_plugin_tool(plugins, mock_runtime, "unknown_tool", {})

        assert result is None

    @pytest.mark.asyncio
    async def test_dispatch_dataclass_tool(self, tmp_path, mock_runtime):
        """Test dispatching to a dataclass-style tool."""
        plugin_code = '''
class MultiplyTool(ToolDef):
    name = "multiply"
    description = "Multiply two numbers"
    params = [
        ToolParam("x", "integer", "First number"),
        ToolParam("y", "integer", "Second number"),
    ]

    async def run(self, api, x: int, y: int) -> dict:
        return {"product": x * y}
'''
        plugin_path = tmp_path / "multiply_plugin.py"
        plugin_path.write_text(plugin_code)

        plugins = load_plugins(tmp_path)
        result = await dispatch_plugin_tool(plugins, mock_runtime, "multiply", {"x": 4, "y": 7})

        assert result is not None
        assert result["product"] == 28


class TestMaraPluginAPI:
    """Tests for the MaraPluginAPI."""

    def test_api_exposes_connection_status(self):
        """Test that API exposes connection status."""
        class MockRuntime:
            is_connected = True
        api = MaraPluginAPI(_runtime=MockRuntime())
        assert api.connected is True

    def test_api_exposes_robot_state(self):
        """Test that API exposes robot state."""
        class MockRuntime:
            state = type("State", (), {"robot_state": type("RS", (), {"value": "ARMED"})()})()
        api = MaraPluginAPI(_runtime=MockRuntime())
        assert api.robot_state == "ARMED"

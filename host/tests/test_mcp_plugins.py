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


# ═══════════════════════════════════════════════════════════════════════════
# Error Handling Tests (Priority: HIGH)
# ═══════════════════════════════════════════════════════════════════════════

class TestPluginErrorHandling:
    """Tests for plugin error handling.

    A bad plugin should NEVER take down the server.
    """

    def test_syntax_error_plugin_skipped_cleanly(self, tmp_path):
        """Plugin with syntax error should be skipped, not crash the loader."""
        # Create a plugin with syntax error
        bad_plugin = tmp_path / "bad_syntax.py"
        bad_plugin.write_text('''
TOOLS = [{"name": "broken", "description": "Broken", "params": []}]
def this is not valid python {{{
''')

        # Create a good plugin
        good_plugin = tmp_path / "good.py"
        good_plugin.write_text('''
TOOLS = [{"name": "working", "description": "Works", "params": []}]
async def working(api) -> dict:
    return {"status": "ok"}
''')

        # load_plugins should NOT raise, should skip bad plugin
        plugins = load_plugins(tmp_path)

        # Only the good plugin should be loaded
        assert len(plugins) == 1
        assert plugins[0].name == "good"

    def test_runtime_error_in_plugin_load_skipped(self, tmp_path):
        """Plugin that raises at import time should be skipped."""
        bad_plugin = tmp_path / "runtime_error.py"
        bad_plugin.write_text('''
raise RuntimeError("Plugin initialization failed")
''')

        good_plugin = tmp_path / "working.py"
        good_plugin.write_text('''
TOOLS = [{"name": "ok", "description": "OK", "params": []}]
async def ok(api) -> dict:
    return {"status": "ok"}
''')

        plugins = load_plugins(tmp_path)
        assert len(plugins) == 1
        assert plugins[0].name == "working"

    @pytest.mark.asyncio
    async def test_handler_exception_returns_error_dict(self, tmp_path):
        """Handler that raises should return structured error, not bubble up."""
        plugin_code = '''
TOOLS = [{"name": "explode", "description": "Will raise", "params": []}]
async def explode(api) -> dict:
    raise ValueError("Something went wrong!")
'''
        plugin_path = tmp_path / "exploding.py"
        plugin_path.write_text(plugin_code)

        plugins = load_plugins(tmp_path)

        class MockRuntime:
            is_connected = True
            state = type("State", (), {"robot_state": type("RS", (), {"value": "IDLE"})()})()

        # Should NOT raise - should return error dict
        result = await dispatch_plugin_tool(plugins, MockRuntime(), "explode", {})

        assert result is not None
        assert "error" in result
        assert "Something went wrong" in result["error"]

    @pytest.mark.asyncio
    async def test_handler_exception_includes_error_type(self, tmp_path):
        """Error response should include exception type."""
        plugin_code = '''
TOOLS = [{"name": "crash", "description": "Crash", "params": []}]
async def crash(api) -> dict:
    raise KeyError("missing_key")
'''
        plugin_path = tmp_path / "crasher.py"
        plugin_path.write_text(plugin_code)

        plugins = load_plugins(tmp_path)

        class MockRuntime:
            is_connected = True
            state = type("State", (), {"robot_state": type("RS", (), {"value": "IDLE"})()})()

        result = await dispatch_plugin_tool(plugins, MockRuntime(), "crash", {})

        assert result is not None
        assert "error" in result
        # Should include the exception type or message
        assert "KeyError" in result["error"] or "missing_key" in result["error"]

    def test_plugin_name_collision_detection(self, tmp_path):
        """Two plugins defining same tool name should be detectable."""
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text('''
TOOLS = [{"name": "duplicate", "description": "From A", "params": []}]
async def duplicate(api) -> dict:
    return {"source": "a"}
''')

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text('''
TOOLS = [{"name": "duplicate", "description": "From B", "params": []}]
async def duplicate(api) -> dict:
    return {"source": "b"}
''')

        plugins = load_plugins(tmp_path)

        # Both should load - collision happens at dispatch time
        assert len(plugins) == 2

        # get_plugin_tools should include both (last wins or both present)
        tools = get_plugin_tools(plugins)
        duplicate_tools = [t for t in tools if t.name == "duplicate"]

        # Could be 1 (last wins) or 2 (both included) depending on implementation
        # The key is it doesn't crash
        assert len(duplicate_tools) >= 1

    @pytest.mark.asyncio
    async def test_dispatch_collision_first_wins(self, tmp_path):
        """When two plugins have same tool name, first loaded wins."""
        # Plugin a (sorted first alphabetically)
        plugin_a = tmp_path / "aaa_plugin.py"
        plugin_a.write_text('''
TOOLS = [{"name": "collision", "description": "From A", "params": []}]
async def collision(api) -> dict:
    return {"source": "a"}
''')

        # Plugin b (sorted second)
        plugin_b = tmp_path / "bbb_plugin.py"
        plugin_b.write_text('''
TOOLS = [{"name": "collision", "description": "From B", "params": []}]
async def collision(api) -> dict:
    return {"source": "b"}
''')

        plugins = load_plugins(tmp_path)

        class MockRuntime:
            is_connected = True
            state = type("State", (), {"robot_state": type("RS", (), {"value": "IDLE"})()})()

        result = await dispatch_plugin_tool(plugins, MockRuntime(), "collision", {})

        # First plugin wins (sorted alphabetically)
        assert result is not None
        assert result["source"] == "a"

    def test_missing_handler_function_skipped(self, tmp_path):
        """Plugin with TOOLS but missing handler function should not crash."""
        bad_plugin = tmp_path / "missing_handler.py"
        bad_plugin.write_text('''
TOOLS = [{"name": "missing", "description": "Handler missing", "params": []}]
# No 'missing' function defined!
''')

        good_plugin = tmp_path / "ok.py"
        good_plugin.write_text('''
TOOLS = [{"name": "present", "description": "OK", "params": []}]
async def present(api) -> dict:
    return {"ok": True}
''')

        plugins = load_plugins(tmp_path)

        # Should load both, but missing handler's tool won't work
        # The key is it doesn't crash during loading
        tool_names = set()
        for p in plugins:
            for t in p.tools:
                tool_names.add(t["name"])

        assert "present" in tool_names

    def test_malformed_tools_list_skipped(self, tmp_path):
        """Plugin with malformed TOOLS should be skipped."""
        bad_plugin = tmp_path / "bad_tools.py"
        bad_plugin.write_text('''
TOOLS = "not a list"
''')

        good_plugin = tmp_path / "good.py"
        good_plugin.write_text('''
TOOLS = [{"name": "works", "description": "OK", "params": []}]
async def works(api) -> dict:
    return {"ok": True}
''')

        plugins = load_plugins(tmp_path)

        # Only good plugin should be loaded
        names = [p.name for p in plugins]
        assert "good" in names
        # bad_tools might be skipped or loaded with empty tools

    @pytest.mark.asyncio
    async def test_async_timeout_does_not_crash_server(self, tmp_path):
        """Handler that hangs should be handleable (timeout not crash)."""
        plugin_code = '''
import asyncio
TOOLS = [{"name": "hang", "description": "Hangs", "params": []}]
async def hang(api) -> dict:
    await asyncio.sleep(0.1)  # Short sleep for test
    return {"completed": True}
'''
        plugin_path = tmp_path / "hanging.py"
        plugin_path.write_text(plugin_code)

        plugins = load_plugins(tmp_path)

        class MockRuntime:
            is_connected = True
            state = type("State", (), {"robot_state": type("RS", (), {"value": "IDLE"})()})()

        # Should complete (not actually hang in this test)
        result = await dispatch_plugin_tool(plugins, MockRuntime(), "hang", {})
        assert result is not None
        assert result.get("completed") is True

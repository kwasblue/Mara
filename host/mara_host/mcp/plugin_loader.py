# mara_host/mcp/plugin_loader.py
"""
Plugin loader for MARA MCP server.

Loads single-file plugins from ~/.mara/plugins/ and provides
generic dispatch for plugin tools.

Plugin files are plain Python that define tools either as dicts or dataclasses.
No imports required - the plugin API is injected at load time.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

from mcp.types import Tool


# ═══════════════════════════════════════════════════════════════════════════
# Plugin API - These types are injected into plugin namespace
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToolParam:
    """A parameter for a plugin tool."""
    name: str
    type: str = "string"  # "string", "integer", "number", "boolean"
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class ToolDef:
    """
    A plugin tool definition.

    Example:
        @dataclass
        class MyTool(ToolDef):
            name = "my_plugin_tool"
            description = "Does something cool"
            params = [ToolParam("value", "integer", "The value to use")]

            async def run(self, api, value: int) -> dict:
                return {"result": value * 2}
    """
    name: str = ""
    description: str = ""
    params: list[ToolParam] = field(default_factory=list)

    async def run(self, api: "MaraPluginAPI", **kwargs) -> dict:
        """Override this to implement the tool."""
        raise NotImplementedError("Subclass must implement run()")


@dataclass
class MaraPluginAPI:
    """
    API exposed to plugins for robot interaction.

    Wraps the MaraRuntime with a clean interface that plugins can use.
    """
    _runtime: Any  # MaraRuntime, but we don't import it to avoid cycles

    # Connection
    @property
    def connected(self) -> bool:
        return self._runtime.is_connected

    async def connect(self) -> dict:
        return await self._runtime.connect()

    async def disconnect(self) -> dict:
        return await self._runtime.disconnect()

    async def ensure_connected(self) -> None:
        await self._runtime.ensure_connected()

    # State
    def get_state(self) -> dict:
        return self._runtime.get_snapshot()

    @property
    def robot_state(self) -> str:
        return self._runtime.state.robot_state.value

    # Services (lazy access)
    @property
    def servo(self):
        return self._runtime.servo_service

    @property
    def motor(self):
        return self._runtime.motor_service

    @property
    def gpio(self):
        return self._runtime.gpio_service

    @property
    def imu(self):
        return self._runtime.imu_service

    @property
    def encoder(self):
        return self._runtime.encoder_service

    @property
    def stepper(self):
        return self._runtime.stepper_service

    @property
    def signals(self):
        return self._runtime.signal_service

    @property
    def control_graph(self):
        return self._runtime.control_graph_service

    @property
    def motion(self):
        return self._runtime.motion_service

    @property
    def state_service(self):
        return self._runtime.state_service

    @property
    def client(self):
        """Direct client access for advanced use."""
        return self._runtime.client


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Loading
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LoadedPlugin:
    """A loaded plugin with its tools."""
    name: str
    path: Path
    tools: list[dict]  # Normalized tool definitions
    handlers: dict[str, Callable[[MaraPluginAPI, dict], Awaitable[dict]]]


def _normalize_tool_def(tool_def: dict | ToolDef) -> dict:
    """Normalize a tool definition to dict format."""
    if isinstance(tool_def, ToolDef):
        return {
            "name": tool_def.name,
            "description": tool_def.description,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                }
                for p in tool_def.params
            ],
        }
    return tool_def


def _make_input_schema(params: list[dict]) -> dict:
    """Build MCP inputSchema from params list."""
    properties = {}
    required = []

    for p in params:
        prop = {"type": p.get("type", "string")}
        if p.get("description"):
            prop["description"] = p["description"]
        if p.get("default") is not None:
            prop["default"] = p["default"]

        properties[p["name"]] = prop

        if p.get("required", True):
            required.append(p["name"])

    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def load_plugin(path: Path) -> LoadedPlugin | None:
    """
    Load a single plugin file.

    Injects ToolDef, ToolParam, and MaraPluginAPI into the plugin namespace.
    Plugin can define tools as:

    1. Dict style:
        TOOLS = [
            {
                "name": "my_tool",
                "description": "Does something",
                "params": [{"name": "value", "type": "integer"}],
            }
        ]

        async def my_tool(api, value: int) -> dict:
            return {"result": value}

    2. Dataclass style:
        class MyTool(ToolDef):
            name = "my_tool"
            description = "Does something"
            params = [ToolParam("value", "integer")]

            async def run(self, api, value: int) -> dict:
                return {"result": value}
    """
    if not path.exists() or not path.suffix == ".py":
        return None

    plugin_name = path.stem

    # Create module spec
    spec = importlib.util.spec_from_file_location(f"mara_plugin_{plugin_name}", path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)

    # Inject plugin API into module namespace
    module.ToolDef = ToolDef
    module.ToolParam = ToolParam
    module.MaraPluginAPI = MaraPluginAPI

    # Load the module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[Plugin] Failed to load {path}: {e}", file=sys.stderr)
        return None

    tools = []
    handlers = {}

    # Look for TOOLS list (dict style)
    if hasattr(module, "TOOLS") and isinstance(module.TOOLS, list):
        for tool_def in module.TOOLS:
            normalized = _normalize_tool_def(tool_def)
            tools.append(normalized)

            # Find handler function
            handler_name = normalized["name"]
            if hasattr(module, handler_name):
                fn = getattr(module, handler_name)

                # Wrap the raw function to accept (api, args: dict) -> dict
                async def wrapped_handler(api: MaraPluginAPI, args: dict, func=fn) -> dict:
                    return await func(api, **args)

                handlers[handler_name] = wrapped_handler

    # Look for ToolDef subclasses (dataclass style)
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, ToolDef)
            and attr is not ToolDef
        ):
            # Check for class-level name attribute (not instance attribute)
            tool_name = getattr(attr, "name", "")
            if not tool_name:
                continue

            # Instantiate to get defaults
            try:
                instance = attr()
                # Override with class-level name if instance name is empty
                if not instance.name:
                    instance.name = tool_name
                if not instance.description:
                    instance.description = getattr(attr, "description", "")
                if not instance.params:
                    instance.params = getattr(attr, "params", [])

                normalized = _normalize_tool_def(instance)
                tools.append(normalized)

                # Capture instance in closure properly using default argument
                async def bound_handler(api: MaraPluginAPI, args: dict, inst=instance) -> dict:
                    return await inst.run(api, **args)

                handlers[normalized["name"]] = bound_handler
            except Exception as e:
                print(f"[Plugin] Failed to instantiate {attr_name}: {e}", file=sys.stderr)

    if not tools:
        return None

    return LoadedPlugin(
        name=plugin_name,
        path=path,
        tools=tools,
        handlers=handlers,
    )


def load_plugins(plugin_dir: Path | None = None) -> list[LoadedPlugin]:
    """
    Load all plugins from the plugin directory.

    Default: ~/.mara/plugins/
    """
    if plugin_dir is None:
        plugin_dir = Path.home() / ".mara" / "plugins"

    if not plugin_dir.exists():
        return []

    plugins = []
    for path in sorted(plugin_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue

        plugin = load_plugin(path)
        if plugin:
            plugins.append(plugin)
            print(f"[Plugin] Loaded {plugin.name}: {len(plugin.tools)} tools", file=sys.stderr)

    return plugins


def get_plugin_tools(plugins: list[LoadedPlugin]) -> list[Tool]:
    """Convert loaded plugins to MCP Tool definitions."""
    tools = []
    for plugin in plugins:
        for tool_def in plugin.tools:
            tools.append(Tool(
                name=tool_def["name"],
                description=f"[plugin:{plugin.name}] {tool_def['description']}",
                inputSchema=_make_input_schema(tool_def.get("params", [])),
            ))
    return tools


async def dispatch_plugin_tool(
    plugins: list[LoadedPlugin],
    runtime: Any,  # MaraRuntime
    name: str,
    args: dict,
) -> dict | None:
    """
    Dispatch a tool call to the appropriate plugin handler.

    Returns None if no plugin handles this tool name.
    """
    api = MaraPluginAPI(_runtime=runtime)

    for plugin in plugins:
        if name in plugin.handlers:
            handler = plugin.handlers[name]
            return await handler(api, args)

    return None

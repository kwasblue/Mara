#!/usr/bin/env python3
"""
Generate MCP and HTTP server files from tool schema AND command schema.

This generator reads:
- `mara_host/mcp/tool_schema.py` - Hand-crafted tool definitions with service mappings
- `mara_host/tools/schema/commands/` - Firmware command definitions (auto-discovered)

And produces:
- mara_host/mcp/_generated_tools.py - Tool list and dispatch for MCP
- mara_host/mcp/_generated_http.py - Handlers and routes for HTTP

Commands in the schema that don't have explicit tool definitions are auto-generated
as generic "send command" tools, ensuring complete firmware coverage.

Usage:
    python -m mara_host.tools.gen_mcp_servers
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Any

# Add parent to path for imports
TOOLS_DIR = Path(__file__).parent
HOST_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(HOST_DIR))
sys.path.insert(0, str(HOST_DIR.parent))

# Import directly to avoid circular import through mcp/__init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "tool_schema",
    HOST_DIR / "mcp" / "tool_schema.py"
)
tool_schema_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool_schema_module
spec.loader.exec_module(tool_schema_module)
TOOLS = tool_schema_module.TOOLS
ToolDef = tool_schema_module.ToolDef
ToolParam = tool_schema_module.ToolParam

# Import command schema for auto-generation
from mara_host.tools.schema.commands import COMMANDS, COMMAND_OBJECTS
from mara_host.tools.schema.commands.core import CommandDef, FieldDef, UNSET


# =============================================================================
# Output Paths
# =============================================================================

MCP_OUTPUT = HOST_DIR / "mcp" / "_generated_tools.py"
HTTP_OUTPUT = HOST_DIR / "mcp" / "_generated_http.py"


# =============================================================================
# Auto-Generation from Command Schema
# =============================================================================

# Commands to skip (internal/low-level)
SKIP_COMMANDS = {
    "CMD_ACK", "CMD_NACK", "CMD_ERROR", "CMD_UNKNOWN",
    "CMD_HEARTBEAT",  # Internal keep-alive
}

# Type mapping from schema to JSON Schema
SCHEMA_TYPE_MAP = {
    "string": "string", "str": "string",
    "int": "integer", "integer": "integer",
    "float": "number", "number": "number",
    "bool": "boolean", "boolean": "boolean",
    "array": "array", "object": "object",
}


def cmd_to_tool_name(cmd_name: str) -> str:
    """Convert CMD_FOO_BAR to foo_bar."""
    return cmd_name.removeprefix("CMD_").lower()


def is_host_to_mcu(cmd_def: CommandDef | dict) -> bool:
    """Check if command is host->mcu."""
    if isinstance(cmd_def, CommandDef):
        return cmd_def.direction in ("host->mcu", "both")
    return cmd_def.get("direction", "host->mcu") in ("host->mcu", "both")


def field_to_json_schema(field_def: FieldDef | dict) -> dict[str, Any]:
    """Convert a FieldDef to JSON Schema."""
    if isinstance(field_def, FieldDef):
        schema: dict[str, Any] = {"type": SCHEMA_TYPE_MAP.get(field_def.type, field_def.type)}
        if field_def.description:
            schema["description"] = field_def.description
        if field_def.default is not UNSET:
            schema["default"] = field_def.default
        if field_def.enum:
            schema["enum"] = list(field_def.enum)
        if field_def.minimum is not None:
            schema["minimum"] = field_def.minimum
        if field_def.maximum is not None:
            schema["maximum"] = field_def.maximum
        return schema
    else:
        schema = {"type": SCHEMA_TYPE_MAP.get(field_def.get("type", "string"), "string")}
        if "description" in field_def:
            schema["description"] = field_def["description"]
        if "default" in field_def:
            schema["default"] = field_def["default"]
        if "enum" in field_def:
            schema["enum"] = field_def["enum"]
        return schema


def get_auto_generated_tools() -> list[tuple[str, str, dict, str]]:
    """
    Get tools auto-generated from command schema.

    Returns list of (tool_name, cmd_name, input_schema, description) for commands
    not already defined in tool_schema.py.
    """
    # Get tool names already defined in tool_schema.py
    existing_tools = {f"mara_{t.name}" for t in TOOLS}

    auto_tools = []

    for cmd_name in sorted(COMMANDS.keys()):
        if cmd_name in SKIP_COMMANDS:
            continue

        tool_name = f"mara_{cmd_to_tool_name(cmd_name)}"

        # Skip if already defined manually
        if tool_name in existing_tools:
            continue

        cmd_def = COMMAND_OBJECTS.get(cmd_name) or COMMANDS.get(cmd_name)
        if not cmd_def or not is_host_to_mcu(cmd_def):
            continue

        # Get description
        if isinstance(cmd_def, CommandDef):
            description = cmd_def.description
            payload = dict(cmd_def.payload)
        else:
            description = cmd_def.get("description", cmd_name)
            payload = cmd_def.get("payload", {})

        # Build input schema
        properties = {}
        required = []

        for field_name, field_def in payload.items():
            properties[field_name] = field_to_json_schema(field_def)
            if isinstance(field_def, FieldDef):
                if field_def.required:
                    required.append(field_name)
            elif field_def.get("required"):
                required.append(field_name)

        input_schema = {"type": "object", "properties": properties}
        if required:
            input_schema["required"] = required

        auto_tools.append((tool_name, cmd_name, input_schema, description))

    return auto_tools


# =============================================================================
# Code Generation Helpers
# =============================================================================

def generate_header(description: str) -> str:
    """Generate file header."""
    return f'''# AUTO-GENERATED FILE - DO NOT EDIT
# Generated by: tools/gen_mcp_servers.py
# Generated at: {datetime.now().isoformat()}
"""
{description}
"""

from __future__ import annotations

'''


def param_to_json_schema(param: ToolParam) -> dict:
    """Convert ToolParam to JSON Schema property."""
    return param.to_json_schema()


def tool_to_mcp_schema(tool: ToolDef) -> dict:
    """Convert ToolDef to MCP Tool inputSchema."""
    return tool.input_schema()


# =============================================================================
# MCP Tools Generator
# =============================================================================

def generate_mcp_tools() -> str:
    """Generate _generated_tools.py content."""
    lines = [generate_header("Generated MCP tool definitions and dispatch.")]

    # Imports
    lines.append("""from typing import Any
from datetime import datetime
from mcp.types import Tool, TextContent


def get_tool_definitions() -> list[Tool]:
    \"\"\"Return list of MCP Tool definitions.\"\"\"
    return [
""")

    # Generate Tool definitions
    for tool in TOOLS:
        schema = tool_to_mcp_schema(tool)
        lines.append(f'''        Tool(
            name="mara_{tool.name}",
            description="{tool.description}",
            inputSchema={schema!r},
        ),
''')

    # Add auto-generated tools from command schema
    auto_tools = get_auto_generated_tools()
    for tool_name, cmd_name, schema, description in auto_tools:
        # Escape description for string literal
        desc_escaped = description.replace('"', '\\"').replace('\n', ' ')
        lines.append(f'''        Tool(
            name="{tool_name}",
            description="{desc_escaped}",
            inputSchema={schema!r},
        ),
''')

    lines.append("    ]\n\n")

    # Generate dispatch function
    lines.append("""
async def dispatch_tool(runtime, name: str, args: dict[str, Any]) -> str:
    \"\"\"Execute a tool by name and return result string.\"\"\"

""")

    # Generate dispatch cases
    for tool in TOOLS:
        mcp_name = f"mara_{tool.name}"

        if tool.custom_handler:
            # Custom handlers are defined in server.py
            lines.append(f'''    if name == "{mcp_name}":
        return await _handle_{tool.name}(runtime, args)

''')
        elif tool.client_method:
            # Direct client method call
            response = tool.response_format or tool.name.replace("_", " ").title()
            lines.append(f'''    if name == "{mcp_name}":
        await runtime.ensure_connected()
        ok, err = await runtime.client.{tool.client_method}()
        runtime.record_command("{tool.name}", {{}}, ok, err)
        return "OK: {response}" if ok else f"FAIL: {{err}}"

''')
        elif tool.service and tool.method:
            # Service method call
            ensure = "ensure_armed" if tool.requires_arm else "ensure_connected"

            # Build args list for service call
            service_args = []
            for param in tool.params:
                arg_name = param.service_name or param.name
                if param.required:
                    service_args.append(f'{arg_name}=args["{param.name}"]')
                else:
                    default_repr = repr(param.default)
                    service_args.append(f'{arg_name}=args.get("{param.name}", {default_repr})')

            args_str = ", ".join(service_args)

            # Build response format
            if tool.response_format:
                # Use .format(**args) to interpolate parameter values
                response_ok = f'"{tool.response_format}".format(**args)'
            else:
                response_ok = f'str(result.data) if result.data else "{tool.name} OK"'

            sync_line = ""
            if tool.service == "state_service":
                sync_line = "        runtime.sync_state_result(result)\n"

            lines.append(f'''    if name == "{mcp_name}":
        await runtime.{ensure}()
        sent_at = datetime.now()
        result = await runtime.{tool.service}.{tool.method}({args_str})
{sync_line}        runtime.record_command("{tool.name}", args, result.ok, result.error, sent_at=sent_at)
        if result.ok:
            return {response_ok}
        return f"FAIL: {{result.error}}"

''')

    # Add dispatch for auto-generated tools (generic command send)
    for tool_name, cmd_name, schema, description in auto_tools:
        # Extract required params for the call
        props = schema.get("properties", {})
        required = schema.get("required", [])

        lines.append(f'''    if name == "{tool_name}":
        await runtime.ensure_connected()
        sent_at = datetime.now()
        # Auto-generated: send command directly
        ok, error, data = await runtime.client.send_with_data("{cmd_name}", args)
        runtime.record_command("{cmd_name}", args, ok, error, sent_at=sent_at)
        if ok:
            return f"{cmd_name} OK" + (f": {{data}}" if data else "")
        return f"FAIL: {{error}}"

''')

    lines.append('''    return f"Unknown tool: {name}"


# Custom handlers for special tools
async def _handle_connect(runtime, args: dict) -> str:
    result = await runtime.connect()
    return f"Connected: {result}"


async def _handle_disconnect(runtime, args: dict) -> str:
    result = await runtime.disconnect()
    return f"Disconnected: {result}"


async def _handle_get_state(runtime, args: dict) -> str:
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    return str(runtime.get_snapshot())


async def _handle_get_freshness(runtime, args: dict) -> str:
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    return str(runtime.get_freshness_report())


async def _handle_get_events(runtime, args: dict) -> str:
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    events = runtime.state.get_recent_events(20)
    return str([e.to_dict() for e in events])


async def _handle_get_command_stats(runtime, args: dict) -> str:
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    return str(runtime.state.get_command_stats())


# Robot abstraction layer handlers
async def _handle_robot_describe(runtime, args: dict) -> str:
    if not runtime.robot_loaded:
        return "Robot not loaded. Call load_robot(config_path) first."
    return runtime.robot_service.describe()


async def _handle_robot_state(runtime, args: dict) -> str:
    if not runtime.robot_loaded:
        return "Robot not loaded. Call load_robot(config_path) first."
    return runtime.robot_context.get_state_summary()


async def _handle_robot_pose(runtime, args: dict) -> str:
    if not runtime.robot_loaded:
        return "Robot not loaded. Call load_robot(config_path) first."
    return runtime.robot_context.format_pose()
''')

    return "".join(lines)


# =============================================================================
# HTTP Server Generator
# =============================================================================

def generate_http_handlers() -> str:
    """Generate _generated_http.py content."""
    lines = [generate_header("Generated HTTP handlers and routes.")]

    # Imports
    lines.append("""from datetime import datetime
import dataclasses
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


def _serialize_result_data(data):
    \"\"\"Convert dataclass result data to dict for JSON serialization.\"\"\"
    if data is None:
        return None
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        return dataclasses.asdict(data)
    return data


def create_generated_routes(runtime) -> list[Route]:
    \"\"\"Create routes for all generated tools.\"\"\"

""")

    # Generate handler functions
    for tool in TOOLS:
        if tool.custom_handler:
            continue  # Skip custom handlers - defined elsewhere

        http_path = f"/{tool.category}/{tool.name.split('_', 1)[-1] if '_' in tool.name else tool.name}"
        # Simplify path: /servo/servo_attach -> /servo/attach
        if tool.name.startswith(tool.category + "_"):
            action = tool.name[len(tool.category) + 1:]
            http_path = f"/{tool.category}/{action}"
        else:
            http_path = f"/{tool.category}/{tool.name}"

        ensure = "ensure_armed" if tool.requires_arm else "ensure_connected"

        lines.append(f'''    async def handle_{tool.name}(request: Request) -> JSONResponse:
        \"\"\"POST {http_path}\"\"\"
        await runtime.{ensure}()
''')

        # Parse body if has params
        if tool.params:
            lines.append("        body = await request.json()\n")

            # Extract params
            for param in tool.params:
                if param.required:
                    lines.append(f'        {param.name} = body.get("{param.name}")\n')
                    lines.append(f'''        if {param.name} is None:
            return JSONResponse({{"ok": False, "error": "{param.name} required"}}, status_code=400)
''')
                else:
                    default_repr = repr(param.default)
                    lines.append(f'        {param.name} = body.get("{param.name}", {default_repr})\n')

        # Call service or client
        if tool.client_method:
            lines.append(f'''        ok, err = await runtime.client.{tool.client_method}()
        runtime.record_command("{tool.name}", {{}}, ok, err)
        return JSONResponse({{"ok": ok, "error": err}})

''')
        elif tool.service and tool.method:
            # Build service call args
            service_args = []
            for param in tool.params:
                arg_name = param.service_name or param.name
                service_args.append(f'{arg_name}={param.name}')
            args_str = ", ".join(service_args)

            # Use body dict only if there are params
            record_args = "body" if tool.params else "{}"

            sync_line = ""
            if tool.service == "state_service":
                sync_line = "        runtime.sync_state_result(result)\n"

            lines.append(f'''        sent_at = datetime.now()
        result = await runtime.{tool.service}.{tool.method}({args_str})
{sync_line}        runtime.record_command("{tool.name}", {record_args}, result.ok, result.error, sent_at=sent_at)
        return JSONResponse({{"ok": result.ok, "error": result.error, "state": getattr(result, 'state', None), "data": _serialize_result_data(getattr(result, 'data', None))}})

''')

    # Generate routes list
    lines.append("    # Build routes list\n    routes = [\n")

    for tool in TOOLS:
        if tool.custom_handler:
            continue

        # Compute HTTP path
        if tool.name.startswith(tool.category + "_"):
            action = tool.name[len(tool.category) + 1:]
            http_path = f"/{tool.category}/{action}"
        else:
            http_path = f"/{tool.category}/{tool.name}"

        lines.append(f'        Route("{http_path}", handle_{tool.name}, methods=["POST"]),\n')

    lines.append("    ]\n")
    lines.append("    return routes\n")

    # Add OpenAI-compatible schema generator
    lines.append("""

def get_openai_function_schema() -> list[dict]:
    \"\"\"Get OpenAI-compatible function definitions for LLMs.\"\"\"
    return [
""")

    for tool in TOOLS:
        if tool.custom_handler:
            continue

        schema = tool_to_mcp_schema(tool)
        lines.append(f'''        {{
            "name": "mara_{tool.name}",
            "description": "{tool.description}",
            "parameters": {schema!r},
        }},
''')

    lines.append("    ]\n")

    return "".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    print("Generating MCP server tools...")

    # Count auto-generated tools
    auto_tools = get_auto_generated_tools()
    total_tools = len(TOOLS) + len(auto_tools)

    # Generate MCP tools
    mcp_content = generate_mcp_tools()
    MCP_OUTPUT.write_text(mcp_content)
    print(f"  -> {MCP_OUTPUT}")

    # Generate HTTP handlers
    http_content = generate_http_handlers()
    HTTP_OUTPUT.write_text(http_content)
    print(f"  -> {HTTP_OUTPUT}")

    print(f"Generated {total_tools} tools ({len(TOOLS)} manual + {len(auto_tools)} auto-generated from schema)")


if __name__ == "__main__":
    main()

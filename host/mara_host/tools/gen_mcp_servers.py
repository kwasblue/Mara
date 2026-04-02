#!/usr/bin/env python3
"""
Generate MCP and HTTP server files from command schema.

This generator reads:
- `mara_host/mcp/tool_schema.py` - Host-only tool definitions (custom handlers)
- `mara_host/tools/schema/commands/` - Firmware command definitions (auto-discovered)

And produces:
- mara_host/mcp/_generated_tools.py - Tool list and dispatch for MCP
- mara_host/mcp/_generated_http.py - Handlers and routes for HTTP

All firmware commands are auto-generated as tools using metadata from CommandDef.
Host-only tools (connection, recording, testing) come from tool_schema.py.

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
HOST_TOOLS = tool_schema_module.HOST_TOOLS
ToolDef = tool_schema_module.ToolDef
ToolParam = tool_schema_module.ToolParam

# Load command schema directly to avoid mara_host.__init__ dependencies
# First load the core module with proper module name registration
core_module_name = "mara_host.tools.schema.commands.core"
core_spec = importlib.util.spec_from_file_location(
    core_module_name,
    HOST_DIR / "tools" / "schema" / "commands" / "core.py"
)
core_module = importlib.util.module_from_spec(core_spec)
sys.modules[core_module_name] = core_module  # Register before exec
core_spec.loader.exec_module(core_module)
CommandDef = core_module.CommandDef
FieldDef = core_module.FieldDef
UNSET = core_module.UNSET
export_command_dicts = core_module.export_command_dicts

# Discover command modules directly
def discover_command_objects() -> dict[str, CommandDef]:
    """Discover all CommandDef objects from command schema files."""
    commands_dir = HOST_DIR / "tools" / "schema" / "commands"
    all_objects = {}

    for module_file in sorted(commands_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue

        # Load the module with proper name registration
        module_name = f"mara_host.tools.schema.commands.{module_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, module_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module  # Register before exec
        spec.loader.exec_module(module)

        # Find *_COMMAND_OBJECTS dictionaries
        for attr_name in dir(module):
            if attr_name.endswith("_COMMAND_OBJECTS"):
                value = getattr(module, attr_name)
                if isinstance(value, dict):
                    for k, v in value.items():
                        if isinstance(v, CommandDef):
                            all_objects[k] = v

    return all_objects

COMMAND_OBJECTS = discover_command_objects()
COMMANDS = export_command_dicts(COMMAND_OBJECTS)


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


def is_host_to_mcu(cmd_def: CommandDef | dict) -> bool:
    """Check if command is host->mcu."""
    if isinstance(cmd_def, CommandDef):
        return cmd_def.direction in ("host->mcu", "both")
    return cmd_def.get("direction", "host->mcu") in ("host->mcu", "both")


def field_to_json_schema(field_def: FieldDef | dict, overrides: dict | None = None) -> dict[str, Any]:
    """Convert a FieldDef to JSON Schema."""
    overrides = overrides or {}

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
        if field_def.items is not None:
            schema["items"] = field_def.items if isinstance(field_def.items, dict) else field_def.items.to_dict()
    else:
        schema = {"type": SCHEMA_TYPE_MAP.get(field_def.get("type", "string"), "string")}
        if "description" in field_def:
            schema["description"] = field_def["description"]
        if "default" in field_def:
            schema["default"] = field_def["default"]
        if "enum" in field_def:
            schema["enum"] = field_def["enum"]

    # Apply overrides
    if "description" in overrides:
        schema["description"] = overrides["description"]

    return schema


def get_auto_generated_tools() -> list[dict]:
    """
    Get tools auto-generated from command schema.

    Returns list of tool info dicts with all metadata needed for generation.
    """
    auto_tools = []

    for cmd_name in sorted(COMMAND_OBJECTS.keys()):
        if cmd_name in SKIP_COMMANDS:
            continue

        cmd_def = COMMAND_OBJECTS[cmd_name]

        # Skip if not host->mcu
        if not is_host_to_mcu(cmd_def):
            continue

        # Skip if explicitly marked
        if cmd_def.skip_tool:
            continue

        # Get tool metadata from CommandDef
        tool_name = cmd_def.get_tool_name(cmd_name)
        description = cmd_def.tool_description or cmd_def.description
        category = cmd_def.get_category(cmd_name)
        service_name = cmd_def.get_service_name(cmd_name)
        method_name = cmd_def.get_method_name(cmd_name)
        requires_arm = cmd_def.requires_arm
        response_format = cmd_def.response_format
        param_overrides = dict(cmd_def.param_overrides) if cmd_def.param_overrides else {}

        # Build input schema from payload
        payload = dict(cmd_def.payload)
        properties = {}
        required = []
        param_mapping = {}  # Maps tool param name -> command param name

        for field_name, field_def in payload.items():
            # Check for parameter name override
            field_overrides = param_overrides.get(field_name, {})
            tool_param_name = field_overrides.get("tool_name", field_name)

            if tool_param_name != field_name:
                param_mapping[tool_param_name] = field_name

            properties[tool_param_name] = field_to_json_schema(field_def, field_overrides)

            if isinstance(field_def, FieldDef):
                if field_def.required and field_def.default is UNSET:
                    required.append(tool_param_name)
            elif field_def.get("required"):
                required.append(tool_param_name)

        input_schema = {"type": "object", "properties": properties}
        if required:
            input_schema["required"] = required

        auto_tools.append({
            "tool_name": tool_name,
            "mcp_name": f"mara_{tool_name}",
            "cmd_name": cmd_name,
            "description": description,
            "category": category,
            "service_name": service_name,
            "method_name": method_name,
            "requires_arm": requires_arm,
            "response_format": response_format,
            "input_schema": input_schema,
            "param_mapping": param_mapping,
        })

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

    # Generate Tool definitions for host tools
    for tool in HOST_TOOLS:
        schema = tool_to_mcp_schema(tool)
        lines.append(f'''        Tool(
            name="mara_{tool.name}",
            description="{tool.description}",
            inputSchema={schema!r},
        ),
''')

    # Add auto-generated tools from command schema
    auto_tools = get_auto_generated_tools()
    for tool_info in auto_tools:
        desc_escaped = tool_info["description"].replace('"', '\\"').replace('\n', ' ')
        lines.append(f'''        Tool(
            name="{tool_info['mcp_name']}",
            description="{desc_escaped}",
            inputSchema={tool_info['input_schema']!r},
        ),
''')

    lines.append("    ]\n\n")

    # Generate dispatch function
    lines.append("""
async def dispatch_tool(runtime, name: str, args: dict[str, Any]) -> str:
    \"\"\"Execute a tool by name and return result string.\"\"\"

""")

    # Generate dispatch cases for host tools
    for tool in HOST_TOOLS:
        mcp_name = f"mara_{tool.name}"

        if tool.custom_handler:
            lines.append(f'''    if name == "{mcp_name}":
        return await _handle_{tool.name}(runtime, args)

''')
        elif tool.client_method:
            response = tool.response_format or tool.name.replace("_", " ").title()
            lines.append(f'''    if name == "{mcp_name}":
        await runtime.ensure_connected()
        ok, err = await runtime.client.{tool.client_method}()
        runtime.record_command("{tool.name}", {{}}, ok, err)
        return "OK: {response}" if ok else f"FAIL: {{err}}"

''')
        elif tool.service and tool.method:
            ensure = "ensure_armed" if tool.requires_arm else "ensure_connected"
            service_args = []
            for param in tool.params:
                arg_name = param.service_name or param.name
                if param.required:
                    service_args.append(f'{arg_name}=args["{param.name}"]')
                else:
                    default_repr = repr(param.default)
                    service_args.append(f'{arg_name}=args.get("{param.name}", {default_repr})')
            args_str = ", ".join(service_args)

            if tool.response_format:
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

    # Add dispatch for auto-generated tools (via generated services)
    for tool_info in auto_tools:
        mcp_name = tool_info["mcp_name"]
        cmd_name = tool_info["cmd_name"]
        category = tool_info["category"]
        method_name = tool_info["method_name"]
        requires_arm = tool_info["requires_arm"]
        response_format = tool_info["response_format"]
        param_mapping = tool_info["param_mapping"]

        # Build args string for service call
        props = tool_info["input_schema"].get("properties", {})
        required = tool_info["input_schema"].get("required", [])
        service_args = []

        for tool_param_name in props.keys():
            # Map tool param back to command param name
            cmd_param_name = param_mapping.get(tool_param_name, tool_param_name)
            if tool_param_name in required:
                service_args.append(f'{cmd_param_name}=args["{tool_param_name}"]')
            else:
                service_args.append(f'{cmd_param_name}=args.get("{tool_param_name}")')
        args_str = ", ".join(service_args)

        ensure = "ensure_armed" if requires_arm else "ensure_connected"

        # Build response handling
        if response_format:
            response_ok = f'"{response_format}".format(**args)'
        else:
            response_ok = f'f"{cmd_name} OK" + (f": {{result.data}}" if result.data else "")'

        lines.append(f'''    if name == "{mcp_name}":
        await runtime.{ensure}()
        sent_at = datetime.now()
        # Auto-generated: via generated {category} service
        service = runtime.get_generated_service("{category}")
        if service:
            result = await service.{method_name}({args_str})
            runtime.record_command("{cmd_name}", args, result.ok, result.error, sent_at=sent_at)
            if result.ok:
                return {response_ok}
            return f"FAIL: {{result.error}}"
        else:
            # Fallback to direct client call
            ok, error, data = await runtime.client.send_with_data("{cmd_name}", args)
            runtime.record_command("{cmd_name}", args, ok, error, sent_at=sent_at)
            if ok:
                return f"{cmd_name} OK" + (f": {{data}}" if data else "")
            return f"FAIL: {{error}}"

''')

    lines.append('''    return f"Unknown tool: {name}"


# =============================================================================
# Host Tool Handlers (imported from host_tools.py)
# =============================================================================
# Import handlers from the centralized host_tools module
from mara_host.mcp.host_tools import (
    handle_connect as _handle_connect,
    handle_disconnect as _handle_disconnect,
    handle_get_state as _handle_get_state,
    handle_get_freshness as _handle_get_freshness,
    handle_get_events as _handle_get_events,
    handle_get_command_stats as _handle_get_command_stats,
    handle_robot_describe as _handle_robot_describe,
    handle_robot_state as _handle_robot_state,
    handle_robot_pose as _handle_robot_pose,
    handle_firmware_test as _handle_firmware_test,
    handle_host_test as _handle_host_test,
    handle_robot_test_connection as _handle_robot_test_connection,
    handle_robot_test_latency as _handle_robot_test_latency,
    handle_robot_test_all as _handle_robot_test_all,
    handle_record_start as _handle_record_start,
    handle_record_stop as _handle_record_stop,
    handle_record_list as _handle_record_list,
    handle_record_status as _handle_record_status,
)
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

    # Generate handler functions for host tools that aren't custom handlers
    for tool in HOST_TOOLS:
        if tool.custom_handler:
            continue

        http_path = f"/{tool.category}/{tool.name.split('_', 1)[-1] if '_' in tool.name else tool.name}"
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

        if tool.params:
            lines.append("        body = await request.json()\n")
            for param in tool.params:
                if param.required:
                    lines.append(f'        {param.name} = body.get("{param.name}")\n')
                    lines.append(f'''        if {param.name} is None:
            return JSONResponse({{"ok": False, "error": "{param.name} required"}}, status_code=400)
''')
                else:
                    default_repr = repr(param.default)
                    lines.append(f'        {param.name} = body.get("{param.name}", {default_repr})\n')

        if tool.client_method:
            lines.append(f'''        ok, err = await runtime.client.{tool.client_method}()
        runtime.record_command("{tool.name}", {{}}, ok, err)
        return JSONResponse({{"ok": ok, "error": err}})

''')
        elif tool.service and tool.method:
            service_args = []
            for param in tool.params:
                arg_name = param.service_name or param.name
                service_args.append(f'{arg_name}={param.name}')
            args_str = ", ".join(service_args)
            record_args = "body" if tool.params else "{}"

            sync_line = ""
            if tool.service == "state_service":
                sync_line = "        runtime.sync_state_result(result)\n"

            lines.append(f'''        sent_at = datetime.now()
        result = await runtime.{tool.service}.{tool.method}({args_str})
{sync_line}        runtime.record_command("{tool.name}", {record_args}, result.ok, result.error, sent_at=sent_at)
        return JSONResponse({{"ok": result.ok, "error": result.error, "state": getattr(result, 'state', None), "data": _serialize_result_data(getattr(result, 'data', None))}})

''')

    # Generate handler functions for auto-generated tools
    auto_tools = get_auto_generated_tools()
    for tool_info in auto_tools:
        tool_name = tool_info["tool_name"]
        category = tool_info["category"]
        method_name = tool_info["method_name"]
        requires_arm = tool_info["requires_arm"]
        cmd_name = tool_info["cmd_name"]
        param_mapping = tool_info["param_mapping"]

        http_path = f"/{category}/{method_name}"
        ensure = "ensure_armed" if requires_arm else "ensure_connected"

        props = tool_info["input_schema"].get("properties", {})
        required = tool_info["input_schema"].get("required", [])

        lines.append(f'''    async def handle_{tool_name}(request: Request) -> JSONResponse:
        \"\"\"POST {http_path}\"\"\"
        await runtime.{ensure}()
''')

        if props:
            lines.append("        body = await request.json()\n")
            for tool_param_name, prop_schema in props.items():
                if tool_param_name in required:
                    lines.append(f'        {tool_param_name} = body.get("{tool_param_name}")\n')
                    lines.append(f'''        if {tool_param_name} is None:
            return JSONResponse({{"ok": False, "error": "{tool_param_name} required"}}, status_code=400)
''')
                else:
                    default_val = prop_schema.get("default")
                    default_repr = repr(default_val)
                    lines.append(f'        {tool_param_name} = body.get("{tool_param_name}", {default_repr})\n')

        # Build service call args (map tool params back to command params)
        service_args = []
        for tool_param_name in props.keys():
            cmd_param_name = param_mapping.get(tool_param_name, tool_param_name)
            service_args.append(f'{cmd_param_name}={tool_param_name}')
        args_str = ", ".join(service_args)
        record_args = "body" if props else "{}"

        lines.append(f'''        sent_at = datetime.now()
        service = runtime.get_generated_service("{category}")
        if service:
            result = await service.{method_name}({args_str})
            runtime.record_command("{cmd_name}", {record_args}, result.ok, result.error, sent_at=sent_at)
            return JSONResponse({{"ok": result.ok, "error": result.error, "data": _serialize_result_data(getattr(result, 'data', None))}})
        else:
            ok, error, data = await runtime.client.send_with_data("{cmd_name}", {record_args})
            runtime.record_command("{cmd_name}", {record_args}, ok, error, sent_at=sent_at)
            return JSONResponse({{"ok": ok, "error": error, "data": data}})

''')

    # Generate routes list
    lines.append("    # Build routes list\n    routes = [\n")

    for tool in HOST_TOOLS:
        if tool.custom_handler:
            continue
        if tool.name.startswith(tool.category + "_"):
            action = tool.name[len(tool.category) + 1:]
            http_path = f"/{tool.category}/{action}"
        else:
            http_path = f"/{tool.category}/{tool.name}"
        lines.append(f'        Route("{http_path}", handle_{tool.name}, methods=["POST"]),\n')

    for tool_info in auto_tools:
        tool_name = tool_info["tool_name"]
        category = tool_info["category"]
        method_name = tool_info["method_name"]
        http_path = f"/{category}/{method_name}"
        lines.append(f'        Route("{http_path}", handle_{tool_name}, methods=["POST"]),\n')

    lines.append("    ]\n")
    lines.append("    return routes\n")

    # Add OpenAI-compatible schema generator
    lines.append("""

def get_openai_function_schema() -> list[dict]:
    \"\"\"Get OpenAI-compatible function definitions for LLMs.\"\"\"
    return [
""")

    for tool in HOST_TOOLS:
        if tool.custom_handler:
            continue
        schema = tool_to_mcp_schema(tool)
        lines.append(f'''        {{
            "name": "mara_{tool.name}",
            "description": "{tool.description}",
            "parameters": {schema!r},
        }},
''')

    for tool_info in auto_tools:
        desc_escaped = tool_info["description"].replace('"', '\\"').replace('\n', ' ')
        lines.append(f'''        {{
            "name": "{tool_info['mcp_name']}",
            "description": "{desc_escaped}",
            "parameters": {tool_info['input_schema']!r},
        }},
''')

    lines.append("    ]\n")

    return "".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    print("Generating MCP server tools...")

    # Count tools
    auto_tools = get_auto_generated_tools()
    total_tools = len(HOST_TOOLS) + len(auto_tools)

    # Generate MCP tools
    mcp_content = generate_mcp_tools()
    MCP_OUTPUT.write_text(mcp_content)
    print(f"  -> {MCP_OUTPUT}")

    # Generate HTTP handlers
    http_content = generate_http_handlers()
    HTTP_OUTPUT.write_text(http_content)
    print(f"  -> {HTTP_OUTPUT}")

    print(f"Generated {total_tools} tools ({len(HOST_TOOLS)} host-only + {len(auto_tools)} from command schema)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# mara_host/mcp/server.py
"""
MCP server for MARA robot control.

Exposes robot control and telemetry as MCP tools with:
- Server-level instructions to guide LLM behavior
- Structured error responses with recovery hints
- MCP Resources for passive context
- MCP Prompts for common workflows
- Tool modes (standard/developer) for tool count management

Usage:
    python -m mara_host.mcp.server

    # Standard mode (~35 curated tools)
    python -m mara_host.mcp.server --mode standard

    # Developer mode (all ~155 tools)
    python -m mara_host.mcp.server --mode developer

    # With specific serial port
    python -m mara_host.mcp.server -p /dev/ttyUSB0
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource, Prompt, PromptMessage, GetPromptResult

from mara_host.mcp.runtime import MaraRuntime
from mara_host.mcp._generated_tools import get_tool_definitions, dispatch_tool
from mara_host.mcp.errors import wrap_exception, StructuredResult
from mara_host.mcp.instructions import SERVER_INSTRUCTIONS, get_mode_tools
from mara_host.mcp.resources import get_resource_definitions, read_resource
from mara_host.mcp.prompts import get_prompt_definitions, get_prompt_template
from mara_host.mcp.plugin_loader import load_plugins, get_plugin_tools, dispatch_plugin_tool
from mara_host.mcp.categories import (
    get_tool_category,
    get_category_description,
    list_tools_by_category,
    get_category_summary,
    format_tools_for_llm,
    CATEGORIES,
)


@dataclass
class MCPToolStats:
    """Statistics for a single MCP tool."""
    calls: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        if self.calls == 0:
            return 0.0
        return self.total_latency_ms / self.calls

    def to_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "errors": self.errors,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
        }


class MCPInstrumentation:
    """Instrumentation for MCP tool calls."""

    def __init__(self) -> None:
        self._stats: dict[str, MCPToolStats] = {}
        self._lock = asyncio.Lock()

    def _get_or_create(self, tool_name: str) -> MCPToolStats:
        if tool_name not in self._stats:
            self._stats[tool_name] = MCPToolStats()
        return self._stats[tool_name]

    async def record_call(
        self, tool_name: str, latency_ms: float, is_error: bool = False
    ) -> None:
        async with self._lock:
            stats = self._get_or_create(tool_name)
            stats.calls += 1
            stats.total_latency_ms += latency_ms
            if is_error:
                stats.errors += 1

    def get_stats(self) -> dict[str, dict[str, Any]]:
        return {name: stats.to_dict() for name, stats in self._stats.items()}

    def get_tool_stats(self, tool_name: str) -> dict[str, Any] | None:
        stats = self._stats.get(tool_name)
        return stats.to_dict() if stats else None

    def reset(self) -> None:
        self._stats.clear()

    def get_summary(self) -> dict[str, Any]:
        total_calls = sum(s.calls for s in self._stats.values())
        total_errors = sum(s.errors for s in self._stats.values())
        total_latency = sum(s.total_latency_ms for s in self._stats.values())
        return {
            "total_calls": total_calls,
            "total_errors": total_errors,
            "total_latency_ms": total_latency,
            "avg_latency_ms": total_latency / total_calls if total_calls > 0 else 0.0,
            "tool_count": len(self._stats),
        }


# Global instrumentation instance
_instrumentation = MCPInstrumentation()


def get_mcp_instrumentation() -> MCPInstrumentation:
    """Get the global MCP instrumentation instance."""
    return _instrumentation


# Optional token-based authentication
AUTH_TOKEN = os.environ.get("MARA_MCP_TOKEN")


def _check_auth(arguments: dict[str, Any] | None) -> tuple[bool, str | None, dict[str, Any]]:
    """Check if the request is authenticated."""
    args = dict(arguments or {})

    if not AUTH_TOKEN:
        return True, None, args

    provided_token = args.pop("_auth_token", None)
    if provided_token == AUTH_TOKEN:
        return True, None, args

    return False, "Authentication required. Set _auth_token in arguments.", args


def create_server(
    port: str | None = None,
    host: str | None = None,
    ble_name: str | None = None,
    tcp_port: int = 3333,
    mode: str = "standard",
) -> Server:
    """
    Create and configure the MCP server.

    Args:
        port: Serial port path
        host: TCP host for WiFi connection
        ble_name: Bluetooth SPP device name
        tcp_port: TCP port number
        mode: Tool mode - "standard" (~35 tools) or "developer" (all ~155 tools)
    """
    server = Server("mara", instructions=SERVER_INSTRUCTIONS)
    runtime = MaraRuntime(port=port, host=host, ble_name=ble_name, tcp_port=tcp_port)

    # Get tool filter for this mode
    mode_tools = get_mode_tools(mode)

    # Load plugins from ~/.mara/plugins/
    plugins = load_plugins()

    # ═══════════════════════════════════════════════════════════════════════════
    # Tools
    # ═══════════════════════════════════════════════════════════════════════════

    # Meta-tool for listing tools by category
    META_TOOL_LIST = Tool(
        name="mara_list_tools",
        description="List all available tools organized by category. Use this to find the right tool for a task.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter to specific category (lifecycle, state, safety, motion, servo, motor, sensor, signal, control, gpio, config, diagnostic, recording, network, benchmark, camera)",
                },
                "format": {
                    "type": "string",
                    "enum": ["summary", "detailed"],
                    "description": "Output format: 'summary' for category counts, 'detailed' for full tool list",
                    "default": "summary",
                },
            },
        },
    )

    def _add_category_to_description(tool: Tool) -> Tool:
        """Add category prefix to tool description."""
        cat = get_tool_category(tool.name)
        if cat:
            prefix = f"[{cat.name}] "
            if not tool.description.startswith("["):
                return Tool(
                    name=tool.name,
                    description=prefix + tool.description,
                    inputSchema=tool.inputSchema,
                )
        return tool

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        all_tools = get_tool_definitions()

        # Filter to mode-specific tools
        if mode_tools is not None:
            all_tools = [t for t in all_tools if t.name in mode_tools]

        # Add category prefixes to descriptions
        categorized_tools = [_add_category_to_description(t) for t in all_tools]

        # Add plugin tools
        plugin_tools = get_plugin_tools(plugins)

        # Add meta-tool at the beginning, then core tools, then plugins
        return [META_TOOL_LIST] + categorized_tools + plugin_tools

    def _handle_list_tools(arguments: dict[str, Any] | None) -> dict:
        """Handle the mara_list_tools meta-tool."""
        args = arguments or {}
        category_filter = args.get("category")
        output_format = args.get("format", "summary")

        all_tools = get_tool_definitions()
        if mode_tools is not None:
            all_tools = [t for t in all_tools if t.name in mode_tools]

        if output_format == "summary":
            # Return category summary with counts
            by_cat = list_tools_by_category(all_tools)
            summary = {}
            for cat_id, cat in CATEGORIES.items():
                tools_in_cat = by_cat.get(cat_id, [])
                if category_filter and cat_id != category_filter:
                    continue
                if tools_in_cat:
                    summary[cat_id] = {
                        "name": cat.name,
                        "icon": cat.icon,
                        "description": cat.description,
                        "tool_count": len(tools_in_cat),
                        "tools": [t["name"] for t in tools_in_cat],
                    }
            return {"categories": summary, "total_tools": len(all_tools)}
        else:
            # Return detailed markdown format
            if category_filter:
                all_tools = [t for t in all_tools if get_tool_category(t.name) and get_tool_category(t.name).id == category_filter]
            return {"tools_by_category": format_tools_for_llm(all_tools)}

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        """Execute a tool with structured error handling."""
        # Check authentication
        is_auth, auth_error, arguments = _check_auth(arguments)
        if not is_auth:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "AUTHENTICATION_REQUIRED",
                "message": auth_error,
                "next_action": None,
            }))]

        start_time = time.monotonic()
        is_error = False

        try:
            # Handle meta-tools locally
            if name == "mara_list_tools":
                result = _handle_list_tools(arguments)
            else:
                # Try plugin dispatch first
                result = await dispatch_plugin_tool(plugins, runtime, name, arguments or {})
                if result is None:
                    # Fall back to generated tools
                    result = await dispatch_tool(runtime, name, arguments)

            # Wrap successful results in structured format
            if isinstance(result, dict):
                response = StructuredResult(success=True, data=result)
            else:
                response = StructuredResult(success=True, data={"result": result})

            return [TextContent(type="text", text=response.to_json())]

        except Exception as e:
            is_error = True
            # Wrap exceptions in structured error with recovery hints
            error = wrap_exception(e, context=name)
            return [TextContent(type="text", text=error.to_json())]

        finally:
            latency_ms = (time.monotonic() - start_time) * 1000
            await _instrumentation.record_call(name, latency_ms, is_error)

    # ═══════════════════════════════════════════════════════════════════════════
    # Resources
    # ═══════════════════════════════════════════════════════════════════════════

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available resources for passive context."""
        defs = get_resource_definitions()
        return [
            Resource(
                uri=d["uri"],
                name=d["name"],
                description=d["description"],
                mimeType=d["mimeType"],
            )
            for d in defs
        ]

    @server.read_resource()
    async def read_resource_handler(uri: str) -> str:
        """Read a resource."""
        return await read_resource(runtime, uri)

    # ═══════════════════════════════════════════════════════════════════════════
    # Prompts
    # ═══════════════════════════════════════════════════════════════════════════

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        """List available workflow prompts."""
        defs = get_prompt_definitions()
        return [
            Prompt(
                name=d["name"],
                description=d["description"],
                arguments=[
                    {"name": a["name"], "description": a["description"], "required": a.get("required", False)}
                    for a in d.get("arguments", [])
                ],
            )
            for d in defs
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
        """Get a prompt with arguments filled in."""
        template = get_prompt_template(name, arguments)
        if template is None:
            return GetPromptResult(
                description=f"Unknown prompt: {name}",
                messages=[],
            )

        return GetPromptResult(
            description=f"Workflow: {name}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=template),
                )
            ],
        )

    return server


def get_server_instructions() -> str:
    """Get server instructions for LLM context injection."""
    return SERVER_INSTRUCTIONS


async def main():
    """Run the MCP or HTTP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MARA Server - MCP or HTTP mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # MCP mode with standard tools (~35 curated tools)
  python -m mara_host.mcp

  # Developer mode (all ~155 tools)
  python -m mara_host.mcp --mode developer

  # HTTP mode (for any LLM)
  python -m mara_host.mcp --http

  # With specific serial port
  python -m mara_host.mcp -p /dev/ttyUSB0
"""
    )
    parser.add_argument("-p", "--port", help="Serial port (default: from config)")
    parser.add_argument("--tcp", metavar="HOST", help="TCP host (instead of serial)")
    parser.add_argument("--ble-name", default=None, help="Bluetooth SPP device name")
    parser.add_argument("--tcp-port", type=int, default=3333, help="TCP port (default: 3333)")
    parser.add_argument("--http", action="store_true", help="Run HTTP server instead of MCP")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP port (default: 8000)")
    parser.add_argument(
        "--mode",
        choices=["standard", "developer"],
        default="standard",
        help="Tool mode: 'standard' (~35 tools) or 'developer' (all ~155 tools)",
    )
    args = parser.parse_args()

    # Get connection params from args or environment or config
    port = args.port or os.environ.get("MARA_PORT")
    host = args.tcp or os.environ.get("MARA_HOST")
    ble_name = args.ble_name or os.environ.get("MARA_BLE_NAME")
    tcp_port = args.tcp_port or int(os.environ.get("MARA_TCP_PORT", "3333"))

    # Default to config if nothing specified
    if not port and not host and not ble_name:
        from mara_host.cli.cli_config import get_serial_port
        port = get_serial_port()

    # Debug output to stderr
    print(f"[MCP Server] port={port}, host={host}, ble={ble_name}, mode={args.mode}", file=sys.stderr)

    if args.http:
        # HTTP mode
        from mara_host.mcp.http_server import run_http_server
        await run_http_server(
            port=port,
            host=host,
            ble_name=ble_name,
            tcp_port=tcp_port,
            http_port=args.http_port,
        )
    else:
        # MCP mode with server instructions
        server = create_server(
            port=port,
            host=host,
            ble_name=ble_name,
            tcp_port=tcp_port,
            mode=args.mode,
        )

        # Create initialization options
        init_options = server.create_initialization_options()

        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())

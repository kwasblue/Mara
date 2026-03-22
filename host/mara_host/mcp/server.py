#!/usr/bin/env python3
# mara_host/mcp/server.py
"""
MCP server for MARA robot control.

Exposes robot control and telemetry as MCP tools.

Usage:
    python -m mara_host.mcp.server

    # Or with options:
    python -m mara_host.mcp.server --port /dev/cu.usbserial-0001
    python -m mara_host.mcp.server --tcp 192.168.4.1
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mara_host.mcp.runtime import MaraRuntime
from mara_host.mcp._generated_tools import get_tool_definitions, dispatch_tool


def create_server(
    port: str | None = None,
    host: str | None = None,
    tcp_port: int = 3333,
) -> Server:
    """Create and configure the MCP server."""

    server = Server("mara")
    runtime = MaraRuntime(port=port, host=host, tcp_port=tcp_port)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return get_tool_definitions()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a tool and return result."""
        try:
            result = await dispatch_tool(runtime, name, arguments)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def main():
    """Run the MCP or HTTP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MARA Server - MCP or HTTP mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # MCP mode (for Claude Code)
  python -m mara_host.mcp

  # HTTP mode (for any LLM)
  python -m mara_host.mcp --http
  python -m mara_host.mcp --http --http-port 8080

  # With specific serial port
  python -m mara_host.mcp -p /dev/ttyUSB0

  # With TCP connection
  python -m mara_host.mcp --tcp 192.168.4.1
"""
    )
    parser.add_argument("-p", "--port", help="Serial port (default: from config)")
    parser.add_argument("--tcp", metavar="HOST", help="TCP host (instead of serial)")
    parser.add_argument("--tcp-port", type=int, default=3333, help="TCP port (default: 3333)")
    parser.add_argument("--http", action="store_true", help="Run HTTP server instead of MCP")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP port (default: 8000)")
    args = parser.parse_args()

    # Get port from args or environment or config
    port = args.port or os.environ.get("MARA_PORT")
    host = args.tcp or os.environ.get("MARA_HOST")
    tcp_port = args.tcp_port or int(os.environ.get("MARA_TCP_PORT", "3333"))

    # Default to config if nothing specified
    if not port and not host:
        from mara_host.cli.cli_config import get_serial_port
        port = get_serial_port()

    if args.http:
        # HTTP mode
        from mara_host.mcp.http_server import run_http_server
        await run_http_server(
            port=port,
            host=host,
            tcp_port=tcp_port,
            http_port=args.http_port,
        )
    else:
        # MCP mode
        server = create_server(port=port, host=host, tcp_port=tcp_port)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

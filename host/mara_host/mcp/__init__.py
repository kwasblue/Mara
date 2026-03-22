# mara_host/mcp/__init__.py
"""
MCP (Model Context Protocol) server for MARA.

Exposes robot control and telemetry as MCP tools for LLM integration.

Usage:
    python -m mara_host.mcp.server

Configure in Claude Code:
    ~/.claude/settings.json:
    {
        "mcpServers": {
            "mara": {
                "command": "python",
                "args": ["-m", "mara_host.mcp.server"],
                "env": {"MARA_PORT": "/dev/cu.usbserial-0001"}
            }
        }
    }
"""

from mara_host.mcp.server import create_server

__all__ = ["create_server"]

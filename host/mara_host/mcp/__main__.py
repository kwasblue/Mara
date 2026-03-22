# mara_host/mcp/__main__.py
"""Entry point for running MCP server as a module."""

import asyncio
from mara_host.mcp.server import main

asyncio.run(main())

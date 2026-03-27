# mara_host/mcp/http_server.py
"""
HTTP API server for MARA robot control.

Provides REST endpoints for any LLM with function calling.

Usage:
    python -m mara_host.mcp --http
    python -m mara_host.mcp --http --http-port 8080
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mara_host.mcp.runtime import MaraRuntime
from mara_host.mcp._generated_http import create_generated_routes, get_openai_function_schema


def create_http_app(runtime: MaraRuntime) -> Starlette:
    """Create HTTP API application."""

    @asynccontextmanager
    async def lifespan(app):
        # Connect on startup
        try:
            await runtime.connect()
            print(f"[MARA HTTP] Connected to robot")
        except Exception as e:
            print(f"[MARA HTTP] Connection failed: {e}")
        yield
        # Disconnect on shutdown
        await runtime.disconnect()
        print("[MARA HTTP] Disconnected")

    # ═══════════════════════════════════════════════════════════
    # Custom Endpoints (not generated)
    # ═══════════════════════════════════════════════════════════

    async def get_state(request: Request) -> JSONResponse:
        """GET /state - Get full robot state."""
        if not runtime.is_connected:
            return JSONResponse({"error": "not_connected"}, status_code=503)
        return JSONResponse(runtime.get_snapshot())

    async def get_freshness(request: Request) -> JSONResponse:
        """GET /freshness - Get data freshness report."""
        if not runtime.is_connected:
            return JSONResponse({"error": "not_connected"}, status_code=503)
        return JSONResponse(runtime.get_freshness_report())

    async def get_events(request: Request) -> JSONResponse:
        """GET /events - Get recent events."""
        if not runtime.is_connected:
            return JSONResponse({"error": "not_connected"}, status_code=503)
        n = int(request.query_params.get("n", 20))
        events = runtime.state.get_recent_events(n)
        return JSONResponse({"events": [e.to_dict() for e in events]})

    async def get_commands(request: Request) -> JSONResponse:
        """GET /commands - Get command history and stats."""
        if not runtime.is_connected:
            return JSONResponse({"error": "not_connected"}, status_code=503)
        n = int(request.query_params.get("n", 20))
        commands = runtime.state.commands[-n:]
        return JSONResponse({
            "stats": runtime.state.get_command_stats(),
            "commands": [c.to_dict() for c in commands],
        })

    async def get_health(request: Request) -> JSONResponse:
        """GET /health - Compact runtime connectivity/telemetry health."""
        status = 200 if runtime.is_connected else 503
        return JSONResponse(runtime.get_health_report(), status_code=status)

    async def post_connect(request: Request) -> JSONResponse:
        """POST /connect - Connect to robot."""
        result = await runtime.connect()
        return JSONResponse(result)

    async def post_disconnect(request: Request) -> JSONResponse:
        """POST /disconnect - Disconnect from robot."""
        result = await runtime.disconnect()
        return JSONResponse(result)

    async def get_schema(request: Request) -> JSONResponse:
        """GET /schema - Get OpenAI-compatible function definitions."""
        return JSONResponse({"functions": get_openai_function_schema()})

    # ═══════════════════════════════════════════════════════════
    # Routes
    # ═══════════════════════════════════════════════════════════

    # Custom routes
    custom_routes = [
        Route("/state", get_state, methods=["GET"]),
        Route("/freshness", get_freshness, methods=["GET"]),
        Route("/health", get_health, methods=["GET"]),
        Route("/events", get_events, methods=["GET"]),
        Route("/commands", get_commands, methods=["GET"]),
        Route("/schema", get_schema, methods=["GET"]),
        Route("/connect", post_connect, methods=["POST"]),
        Route("/disconnect", post_disconnect, methods=["POST"]),
    ]

    # Generated routes from tool schema
    generated_routes = create_generated_routes(runtime)

    return Starlette(routes=custom_routes + generated_routes, lifespan=lifespan)


async def run_http_server(
    port: Optional[str] = None,
    host: Optional[str] = None,
    ble_name: Optional[str] = None,
    tcp_port: int = 3333,
    http_port: int = 8000,
) -> None:
    """Run the HTTP server."""
    import uvicorn

    runtime = MaraRuntime(port=port, host=host, ble_name=ble_name, tcp_port=tcp_port)
    app = create_http_app(runtime)

    print(f"[MARA HTTP] Starting server on http://localhost:{http_port}")
    print(f"[MARA HTTP] Endpoints:")
    print(f"  GET  /state       - Get robot state")
    print(f"  GET  /schema      - Get function definitions for LLMs")
    print(f"  POST /servo/set   - Move servo")
    print(f"  POST /motor/set   - Set motor speed")
    print(f"  POST /gpio/write  - Set GPIO")
    print(f"  POST /state/stop  - Emergency stop")
    print()

    config = uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

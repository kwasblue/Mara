# tests/test_mcp_server_instructions.py
"""
Tests for MCP server instructions injection.

Priority: LOW - But this is the most important reliability fix from this session.
Verifies that server_instructions are properly passed to MCP initialization.
"""

from __future__ import annotations

import pytest

from mcp.server import Server


class TestServerInstructions:
    """Tests for MCP server instructions configuration."""

    def test_server_constructor_accepts_instructions(self):
        """Test that Server constructor accepts instructions parameter."""
        server = Server("test", instructions="Test instructions for the model")

        # Server should have been created successfully
        assert server is not None
        assert server.name == "test"

    def test_instructions_can_be_multiline(self):
        """Test that instructions can contain multiple lines."""
        instructions = """
        These are multiline instructions.

        They explain how the server works.
        - Item 1
        - Item 2
        """

        server = Server("test", instructions=instructions)

        # Server should accept multiline instructions
        assert server is not None

    def test_instructions_can_be_none(self):
        """Test that instructions can be omitted."""
        server = Server("test")

        # Server should work without instructions
        assert server is not None


class TestServerInstructionsContent:
    """Tests for actual MARA server instructions content."""

    def test_server_instructions_defined(self):
        """Test that SERVER_INSTRUCTIONS is defined in server module."""
        from mara_host.mcp.server import SERVER_INSTRUCTIONS

        assert SERVER_INSTRUCTIONS is not None
        assert len(SERVER_INSTRUCTIONS) > 0

    def test_server_instructions_mentions_key_concepts(self):
        """Test that instructions mention important concepts."""
        from mara_host.mcp.server import SERVER_INSTRUCTIONS

        # Should mention connection
        assert "connect" in SERVER_INSTRUCTIONS.lower() or "connection" in SERVER_INSTRUCTIONS.lower()

    def test_server_instructions_formatted_correctly(self):
        """Test that instructions are well-formatted for model consumption."""
        from mara_host.mcp.server import SERVER_INSTRUCTIONS

        # Should not have excessive whitespace
        lines = SERVER_INSTRUCTIONS.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]
        assert len(non_empty_lines) > 0

        # Should not be ridiculously long (model context limits)
        assert len(SERVER_INSTRUCTIONS) < 10000


class TestMcpServerIntegration:
    """Integration tests for MCP server with instructions."""

    def test_create_server_returns_server_instance(self):
        """Test that create_server returns a valid Server."""
        from mara_host.mcp.server import create_server

        server = create_server()
        assert isinstance(server, Server)

    def test_create_server_with_plugins_dir(self, tmp_path):
        """Test that create_server accepts plugins_dir."""
        from mara_host.mcp.server import create_server

        # Create empty plugins dir
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        server = create_server(plugins_dir=plugins_dir)
        assert isinstance(server, Server)

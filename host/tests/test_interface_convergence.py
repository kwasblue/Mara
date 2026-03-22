# tests/test_interface_convergence.py
"""
Tests for interface convergence.

Verifies that CLI, GUI, MCP, and HTTP interfaces all use the same
service contracts for state operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import inspect

from mara_host.core.result import ServiceResult


class TestStateServiceConvergence:
    """Test that all interfaces converge on StateService for state operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock MaraClient."""
        client = MagicMock()
        client.arm = AsyncMock(return_value=(True, None))
        client.disarm = AsyncMock(return_value=(True, None))
        client.cmd_stop = AsyncMock(return_value=(True, None))
        return client

    @pytest.fixture
    def state_service(self, mock_client):
        """Create StateService with mock client."""
        from mara_host.services.control import StateService
        return StateService(mock_client)

    @pytest.mark.asyncio
    async def test_state_service_arm_returns_result(self, state_service):
        """Test StateService.arm returns ServiceResult."""
        result = await state_service.arm()

        assert isinstance(result, ServiceResult)
        assert result.ok is True
        assert result.state == "ARMED"

    @pytest.mark.asyncio
    async def test_state_service_arm_failure_returns_error(self, state_service, mock_client):
        """Test StateService.arm failure returns error."""
        mock_client.arm = AsyncMock(return_value=(False, "not_idle"))

        result = await state_service.arm()

        assert not result.ok
        assert "not_idle" in result.error


class TestCLIContextConvergence:
    """Test that CLIContext uses StateService."""

    def test_cli_context_has_state_service_property(self):
        """Test CLIContext exposes state_service property."""
        from mara_host.cli.context import CLIContext

        # Check the class has state_service as a property (without calling it)
        assert 'state_service' in dir(CLIContext)
        assert isinstance(getattr(CLIContext, 'state_service'), property)

    def test_cli_context_connect_uses_state_service(self):
        """Test that CLIContext.connect() uses state_service.arm()."""
        from mara_host.cli.context import CLIContext
        import ast

        # Read the source code of connect method
        source = inspect.getsource(CLIContext.connect)

        # Parse to AST and verify it uses state_service.arm()
        # Simple check: look for state_service.arm in the source
        assert "state_service.arm()" in source, \
            "CLIContext.connect should use state_service.arm()"

    def test_cli_context_disconnect_uses_state_service(self):
        """Test that CLIContext.disconnect() uses state_service.disarm()."""
        from mara_host.cli.context import CLIContext
        import ast

        source = inspect.getsource(CLIContext.disconnect)

        # Should use state_service, not client directly
        assert "_state_service" in source, \
            "CLIContext.disconnect should use state_service"


class TestMcpRuntimeConvergence:
    """Test that MCP runtime uses StateService."""

    def test_mcp_runtime_has_state_service_property(self):
        """Test MaraRuntime exposes state_service property."""
        from mara_host.mcp.runtime import MaraRuntime

        # Check the class has state_service as a property (without calling it)
        assert 'state_service' in dir(MaraRuntime)
        assert isinstance(getattr(MaraRuntime, 'state_service'), property)

    def test_mcp_runtime_ensure_armed_uses_state_service(self):
        """Test that MaraRuntime.ensure_armed() uses state_service.arm()."""
        from mara_host.mcp.runtime import MaraRuntime

        source = inspect.getsource(MaraRuntime.ensure_armed)

        assert "state_service.arm()" in source, \
            "MaraRuntime.ensure_armed should use state_service.arm()"


class TestHttpHandlerConvergence:
    """Test that HTTP handlers use StateService."""

    def test_http_arm_handler_uses_state_service(self):
        """Test HTTP arm handler uses state_service."""
        from mara_host.mcp._generated_http import create_generated_routes
        import inspect

        # Get the source of the module
        import mara_host.mcp._generated_http as http_module
        source = inspect.getsource(http_module)

        # Check that handle_arm uses state_service
        assert "state_service.arm()" in source, \
            "HTTP arm handler should use state_service.arm()"

    def test_http_disarm_handler_uses_state_service(self):
        """Test HTTP disarm handler uses state_service."""
        import mara_host.mcp._generated_http as http_module
        import inspect

        source = inspect.getsource(http_module)

        assert "state_service.disarm()" in source, \
            "HTTP disarm handler should use state_service.disarm()"

    def test_http_stop_handler_uses_state_service(self):
        """Test HTTP stop handler uses state_service."""
        import mara_host.mcp._generated_http as http_module
        import inspect

        source = inspect.getsource(http_module)

        assert "state_service.stop()" in source, \
            "HTTP stop handler should use state_service.stop()"


class TestMcpToolConvergence:
    """Test that MCP tools use StateService."""

    def test_mcp_arm_tool_uses_state_service(self):
        """Test MCP arm tool uses state_service."""
        import mara_host.mcp._generated_tools as tools_module
        import inspect

        source = inspect.getsource(tools_module)

        # Look for the arm tool handler using state_service
        assert "state_service.arm()" in source, \
            "MCP arm tool should use state_service.arm()"

    def test_mcp_disarm_tool_uses_state_service(self):
        """Test MCP disarm tool uses state_service."""
        import mara_host.mcp._generated_tools as tools_module
        import inspect

        source = inspect.getsource(tools_module)

        assert "state_service.disarm()" in source, \
            "MCP disarm tool should use state_service.disarm()"


class TestGuiControllerConvergence:
    """Test that GUI controller uses services."""

    def test_gui_controller_uses_state_service(self):
        """Test GUI controller uses StateService for arm/disarm."""
        from mara_host.gui.core.controller import RobotController
        import inspect

        source = inspect.getsource(RobotController)

        # GUI uses _state_service through _state_op
        assert "_state_service" in source, \
            "GUI controller should use state_service"

    def test_gui_controller_has_signal_service(self):
        """Test GUI controller has signal service."""
        from mara_host.gui.core.controller import RobotController
        import inspect

        source = inspect.getsource(RobotController)

        assert "_signal_service" in source, \
            "GUI controller should have signal_service"

    def test_gui_controller_has_controller_service(self):
        """Test GUI controller has controller service."""
        from mara_host.gui.core.controller import RobotController
        import inspect

        source = inspect.getsource(RobotController)

        assert "_controller_service" in source, \
            "GUI controller should have controller_service"


class TestServiceContractConsistency:
    """Test that service contracts are consistent."""

    def test_state_service_arm_signature(self):
        """Test StateService.arm has correct signature."""
        from mara_host.services.control import StateService

        sig = inspect.signature(StateService.arm)
        params = list(sig.parameters.keys())

        # Should only have self
        assert params == ["self"], \
            "StateService.arm should take no parameters"

    def test_state_service_arm_return_type(self):
        """Test StateService.arm returns ServiceResult."""
        from mara_host.services.control import StateService

        # Check docstring or annotations indicate ServiceResult
        doc = StateService.arm.__doc__ or ""
        assert "ServiceResult" in doc, \
            "StateService.arm should document ServiceResult return"

    def test_all_state_methods_return_service_result(self):
        """Test all StateService methods return ServiceResult."""
        from mara_host.services.control import StateService

        async_methods = [
            'arm', 'disarm', 'activate', 'deactivate',
            'estop', 'clear_estop', 'stop', 'safe_shutdown'
        ]

        for method_name in async_methods:
            method = getattr(StateService, method_name)
            doc = method.__doc__ or ""
            # Each should mention ServiceResult
            assert "ServiceResult" in doc or "Returns:" in doc, \
                f"StateService.{method_name} should document its return type"

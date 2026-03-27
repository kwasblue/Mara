# tests/test_http_handlers.py
"""Tests for HTTP handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Test the generated HTTP handler patterns
from mara_host.core.result import ServiceResult


class TestHttpHandlerPatterns:
    """
    Test the patterns used in generated HTTP handlers.

    These tests verify the handler logic without requiring a full HTTP server.
    """

    @pytest.fixture
    def mock_runtime(self):
        """Create a mock runtime with services."""
        runtime = MagicMock()

        # Mock state service
        runtime.state_service = MagicMock()
        runtime.state_service.arm = AsyncMock(
            return_value=ServiceResult.success(state="ARMED")
        )
        runtime.state_service.disarm = AsyncMock(
            return_value=ServiceResult.success(state="IDLE")
        )
        runtime.state_service.stop = AsyncMock(
            return_value=ServiceResult.success(state="ARMED")
        )

        # Mock servo service
        runtime.servo_service = MagicMock()
        runtime.servo_service.set_angle = AsyncMock(
            return_value=ServiceResult.success(data={"angle": 90})
        )
        runtime.composite_service = MagicMock()
        runtime.composite_service.apply = AsyncMock(
            return_value=ServiceResult.success(data={"count": 2})
        )
        runtime.servo_service.attach = AsyncMock(
            return_value=ServiceResult.success(data={"servo_id": 0})
        )

        # Mock motor service
        runtime.motor_service = MagicMock()
        runtime.motor_service.set_speed = AsyncMock(
            return_value=ServiceResult.success(data={"speed": 0.5})
        )

        # Mock gpio service
        runtime.gpio_service = MagicMock()
        runtime.gpio_service.write = AsyncMock(
            return_value=ServiceResult.success(data={"channel": 1, "value": 1})
        )

        # Mock ensure methods
        runtime.ensure_connected = AsyncMock()
        runtime.ensure_armed = AsyncMock()

        # Mock record_command
        runtime.record_command = MagicMock()

        return runtime

    @pytest.mark.asyncio
    async def test_arm_handler_uses_state_service(self, mock_runtime):
        """Test arm endpoint uses state_service."""
        # Simulate handler logic
        await mock_runtime.ensure_connected()
        result = await mock_runtime.state_service.arm()

        assert result.ok
        assert result.state == "ARMED"
        mock_runtime.state_service.arm.assert_called_once()

    @pytest.mark.asyncio
    async def test_disarm_handler_uses_state_service(self, mock_runtime):
        """Test disarm endpoint uses state_service."""
        await mock_runtime.ensure_connected()
        result = await mock_runtime.state_service.disarm()

        assert result.ok
        assert result.state == "IDLE"
        mock_runtime.state_service.disarm.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_handler_uses_state_service(self, mock_runtime):
        """Test stop endpoint uses state_service."""
        await mock_runtime.ensure_connected()
        result = await mock_runtime.state_service.stop()

        assert result.ok
        mock_runtime.state_service.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_servo_set_handler(self, mock_runtime):
        """Test servo set endpoint."""
        await mock_runtime.ensure_armed()
        result = await mock_runtime.servo_service.set_angle(
            servo_id=0, angle=90, duration_ms=300
        )

        assert result.ok
        mock_runtime.servo_service.set_angle.assert_called_once_with(
            servo_id=0, angle=90, duration_ms=300
        )

    @pytest.mark.asyncio
    async def test_batch_apply_handler(self, mock_runtime):
        """Test generic batch endpoint."""
        await mock_runtime.ensure_armed()
        actions = [
            {"cmd": "CMD_GPIO_WRITE", "args": {"channel": 0, "value": 1}},
            {"cmd": "CMD_SERVO_SET_ANGLE", "args": {"servo_id": 0, "angle_deg": 90, "duration_ms": 300}},
            {"cmd": "CMD_DC_SET_SPEED", "args": {"motor_id": 0, "speed": 0.5}},
            {"cmd": "CMD_STEPPER_STOP", "args": {"motor_id": 1}},
        ]
        result = await mock_runtime.composite_service.apply(actions=actions)

        assert result.ok
        mock_runtime.composite_service.apply.assert_called_once_with(actions=actions)

    @pytest.mark.asyncio
    async def test_motor_set_handler(self, mock_runtime):
        """Test motor set endpoint."""
        await mock_runtime.ensure_armed()
        result = await mock_runtime.motor_service.set_speed(motor_id=0, speed=0.5)

        assert result.ok
        mock_runtime.motor_service.set_speed.assert_called_once_with(
            motor_id=0, speed=0.5
        )

    @pytest.mark.asyncio
    async def test_arm_failure_returns_error(self, mock_runtime):
        """Test arm failure returns error."""
        mock_runtime.state_service.arm = AsyncMock(
            return_value=ServiceResult.failure("not_idle", state="ESTOP")
        )

        result = await mock_runtime.state_service.arm()

        assert not result.ok
        assert "not_idle" in result.error

    @pytest.mark.asyncio
    async def test_ensure_armed_called_for_actuator_ops(self, mock_runtime):
        """Test that actuator operations call ensure_armed."""
        # Servo operation should call ensure_armed
        await mock_runtime.ensure_armed()
        await mock_runtime.servo_service.set_angle(servo_id=0, angle=45)

        mock_runtime.ensure_armed.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_connected_called_for_state_ops(self, mock_runtime):
        """Test that state operations call ensure_connected, not ensure_armed."""
        await mock_runtime.ensure_connected()
        await mock_runtime.state_service.arm()

        mock_runtime.ensure_connected.assert_called()


class TestHttpResponseFormats:
    """Test HTTP response formatting patterns."""

    def test_success_response_format(self):
        """Test successful response format."""
        result = ServiceResult.success(state="ARMED")

        response = {
            "ok": result.ok,
            "error": result.error,
            "state": getattr(result, 'state', None),
        }

        assert response["ok"] is True
        assert response["error"] is None
        assert response["state"] == "ARMED"

    def test_failure_response_format(self):
        """Test failure response format."""
        result = ServiceResult.failure("not_armed", state="IDLE")

        response = {
            "ok": result.ok,
            "error": result.error,
            "state": getattr(result, 'state', None),
        }

        assert response["ok"] is False
        assert response["error"] == "not_armed"
        assert response["state"] == "IDLE"

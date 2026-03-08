# tests/test_control_services.py
"""Tests for control services (StateService, MotionService)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from mara_host.services.control import (
    StateService,
    MotionService,
    ServiceResult,
    RobotState,
)
from mara_host.services.control.motion_service import Velocity


# ============== ServiceResult Tests ==============


class TestServiceResult:
    """Tests for ServiceResult dataclass."""

    def test_success_factory(self):
        result = ServiceResult.success(state="ARMED", data={"key": "value"})
        assert result.ok is True
        assert result.error is None
        assert result.state == "ARMED"
        assert result.data == {"key": "value"}

    def test_failure_factory(self):
        result = ServiceResult.failure(error="Something went wrong", state="IDLE")
        assert result.ok is False
        assert result.error == "Something went wrong"
        assert result.state == "IDLE"

    def test_bool_conversion(self):
        success = ServiceResult.success()
        failure = ServiceResult.failure(error="fail")

        assert bool(success) is True
        assert bool(failure) is False

        # Test in if statement
        if success:
            pass  # Should reach here
        else:
            pytest.fail("Success should be truthy")

        if failure:
            pytest.fail("Failure should be falsy")


# ============== StateService Tests ==============


class TestStateService:
    """Tests for StateService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock MaraClient."""
        client = MagicMock()
        client.arm = AsyncMock(return_value=(True, None))
        client.disarm = AsyncMock(return_value=(True, None))
        client.activate = AsyncMock(return_value=(True, None))
        client.deactivate = AsyncMock(return_value=(True, None))
        client.estop = AsyncMock(return_value=(True, None))
        client.clear_estop = AsyncMock(return_value=(True, None))
        client.cmd_stop = AsyncMock(return_value=(True, None))
        return client

    @pytest.fixture
    def state_service(self, mock_client):
        """Create StateService with mock client."""
        return StateService(mock_client)

    def test_initial_state(self, state_service):
        """Test initial state is UNKNOWN."""
        assert state_service.current_state == RobotState.UNKNOWN
        assert state_service.is_armed is False
        assert state_service.is_active is False

    @pytest.mark.asyncio
    async def test_arm_success(self, state_service, mock_client):
        """Test successful arm operation."""
        result = await state_service.arm()

        assert result.ok is True
        assert result.state == "ARMED"
        assert state_service.current_state == RobotState.ARMED
        assert state_service.is_armed is True
        mock_client.arm.assert_called_once()

    @pytest.mark.asyncio
    async def test_arm_failure(self, state_service, mock_client):
        """Test arm operation failure."""
        mock_client.arm.return_value = (False, "Motor not ready")

        result = await state_service.arm()

        assert result.ok is False
        assert "Motor not ready" in result.error
        assert state_service.current_state == RobotState.UNKNOWN

    @pytest.mark.asyncio
    async def test_disarm_success(self, state_service, mock_client):
        """Test successful disarm operation."""
        # First arm
        await state_service.arm()

        # Then disarm
        result = await state_service.disarm()

        assert result.ok is True
        assert result.state == "IDLE"
        assert state_service.current_state == RobotState.IDLE
        assert state_service.is_armed is False

    @pytest.mark.asyncio
    async def test_activate_success(self, state_service, mock_client):
        """Test successful activate operation."""
        await state_service.arm()
        result = await state_service.activate()

        assert result.ok is True
        assert result.state == "ACTIVE"
        assert state_service.current_state == RobotState.ACTIVE
        assert state_service.is_active is True

    @pytest.mark.asyncio
    async def test_deactivate_success(self, state_service, mock_client):
        """Test successful deactivate operation."""
        await state_service.arm()
        await state_service.activate()
        result = await state_service.deactivate()

        assert result.ok is True
        assert result.state == "ARMED"
        assert state_service.current_state == RobotState.ARMED
        assert state_service.is_active is False
        assert state_service.is_armed is True

    @pytest.mark.asyncio
    async def test_estop_always_succeeds_locally(self, state_service, mock_client):
        """Test E-STOP always marks local state as ESTOP."""
        result = await state_service.estop()

        assert result.ok is True
        assert result.state == "ESTOP"
        assert state_service.current_state == RobotState.ESTOP
        assert state_service.is_estopped is True

    @pytest.mark.asyncio
    async def test_estop_with_comms_failure(self, state_service, mock_client):
        """Test E-STOP with communication failure still sets local state."""
        mock_client.estop.return_value = (False, "Connection lost")

        result = await state_service.estop()

        # E-STOP should still succeed locally
        assert result.ok is True
        assert state_service.current_state == RobotState.ESTOP
        # But error should be noted
        assert "comms" in result.error.lower()

    @pytest.mark.asyncio
    async def test_clear_estop_success(self, state_service, mock_client):
        """Test clearing E-STOP."""
        await state_service.estop()
        result = await state_service.clear_estop()

        assert result.ok is True
        assert result.state == "IDLE"
        assert state_service.current_state == RobotState.IDLE

    @pytest.mark.asyncio
    async def test_stop_motion(self, state_service, mock_client):
        """Test soft stop (doesn't change state)."""
        await state_service.arm()
        await state_service.activate()

        result = await state_service.stop()

        assert result.ok is True
        # State should remain ACTIVE (soft stop)
        assert state_service.current_state == RobotState.ACTIVE

    @pytest.mark.asyncio
    async def test_safe_shutdown(self, state_service, mock_client):
        """Test safe shutdown sequence."""
        await state_service.arm()
        await state_service.activate()

        result = await state_service.safe_shutdown()

        assert result.ok is True
        assert state_service.current_state == RobotState.IDLE

    @pytest.mark.asyncio
    async def test_safe_shutdown_ignores_errors(self, state_service, mock_client):
        """Test safe shutdown completes despite errors."""
        mock_client.cmd_stop.side_effect = Exception("Network error")
        mock_client.deactivate.return_value = (False, "Already idle")

        result = await state_service.safe_shutdown()

        # Should still succeed
        assert result.ok is True
        assert state_service.current_state == RobotState.IDLE

    def test_sync_from_telemetry(self, state_service):
        """Test state sync from telemetry data."""
        state_service.sync_from_telemetry("ARMED")
        assert state_service.current_state == RobotState.ARMED

        state_service.sync_from_telemetry("active")  # lowercase
        assert state_service.current_state == RobotState.ACTIVE

        state_service.sync_from_telemetry("INVALID")
        assert state_service.current_state == RobotState.UNKNOWN


# ============== MotionService Tests ==============


class TestMotionService:
    """Tests for MotionService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock MaraClient."""
        client = MagicMock()
        client.send_stream = AsyncMock(return_value=(True, None))
        client.set_vel = AsyncMock(return_value=(True, None))
        client.cmd_stop = AsyncMock(return_value=(True, None))
        return client

    @pytest.fixture
    def motion_service(self, mock_client):
        """Create MotionService with mock client."""
        return MotionService(mock_client)

    @pytest.mark.asyncio
    async def test_set_velocity(self, motion_service, mock_client):
        """Test setting velocity."""
        await motion_service.set_velocity(0.5, 0.2)

        mock_client.send_stream.assert_called_once()
        call_args = mock_client.send_stream.call_args
        assert call_args[0][0] == "CMD_SET_VEL"
        assert call_args[0][1] == {"vx": 0.5, "omega": 0.2}

        assert motion_service.last_velocity.vx == 0.5
        assert motion_service.last_velocity.omega == 0.2

    @pytest.mark.asyncio
    async def test_velocity_clamping(self, motion_service, mock_client):
        """Test velocity is clamped to limits."""
        motion_service.velocity_limit_linear = 1.0
        motion_service.velocity_limit_angular = 2.0

        await motion_service.set_velocity(5.0, 10.0)  # Over limits

        # Should be clamped
        assert motion_service.last_velocity.vx == 1.0
        assert motion_service.last_velocity.omega == 2.0

    @pytest.mark.asyncio
    async def test_velocity_clamping_disabled(self, motion_service, mock_client):
        """Test velocity clamping can be disabled."""
        await motion_service.set_velocity(5.0, 10.0, clamp=False)

        # Should NOT be clamped
        assert motion_service.last_velocity.vx == 5.0
        assert motion_service.last_velocity.omega == 10.0

    @pytest.mark.asyncio
    async def test_set_velocity_reliable(self, motion_service, mock_client):
        """Test reliable velocity command."""
        result = await motion_service.set_velocity_reliable(0.3, 0.1)

        assert result.ok is True
        assert result.data["vx"] == 0.3
        assert result.data["omega"] == 0.1
        mock_client.set_vel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, motion_service, mock_client):
        """Test stop command."""
        await motion_service.set_velocity(0.5, 0.2)
        result = await motion_service.stop()

        assert result.ok is True
        assert motion_service.last_velocity.vx == 0.0
        assert motion_service.last_velocity.omega == 0.0

    @pytest.mark.asyncio
    async def test_forward(self, motion_service, mock_client):
        """Test forward helper."""
        await motion_service.forward(0.8)

        assert motion_service.last_velocity.vx == 0.8
        assert motion_service.last_velocity.omega == 0.0

    @pytest.mark.asyncio
    async def test_backward(self, motion_service, mock_client):
        """Test backward helper."""
        await motion_service.backward(0.6)

        assert motion_service.last_velocity.vx == -0.6
        assert motion_service.last_velocity.omega == 0.0

    @pytest.mark.asyncio
    async def test_rotate_left(self, motion_service, mock_client):
        """Test rotate left helper."""
        await motion_service.rotate_left(0.5)

        assert motion_service.last_velocity.vx == 0.0
        assert motion_service.last_velocity.omega == 0.5

    @pytest.mark.asyncio
    async def test_rotate_right(self, motion_service, mock_client):
        """Test rotate right helper."""
        await motion_service.rotate_right(0.5)

        assert motion_service.last_velocity.vx == 0.0
        assert motion_service.last_velocity.omega == -0.5

    def test_compute_arcade_drive(self, motion_service):
        """Test arcade drive computation."""
        # Full forward
        vel = motion_service.compute_arcade_drive(1.0, 0.0)
        assert vel.vx == 1.0
        assert vel.omega == 0.0

        # Full left turn
        vel = motion_service.compute_arcade_drive(0.0, 1.0)
        assert vel.vx == 0.0
        assert vel.omega == 2.0  # Default angular limit

        # Half forward, half right
        vel = motion_service.compute_arcade_drive(0.5, -0.5)
        assert vel.vx == 0.5
        assert vel.omega == -1.0

    def test_compute_arcade_drive_custom_limits(self, motion_service):
        """Test arcade drive with custom limits."""
        vel = motion_service.compute_arcade_drive(
            1.0, 1.0, max_linear=0.5, max_angular=1.0
        )
        assert vel.vx == 0.5
        assert vel.omega == 1.0

    @pytest.mark.asyncio
    async def test_arcade_drive(self, motion_service, mock_client):
        """Test arcade drive command."""
        await motion_service.arcade_drive(0.5, 0.3)

        # Check last velocity (actual values depend on limits)
        assert motion_service.last_velocity.vx == 0.5
        assert motion_service.last_velocity.omega == pytest.approx(0.6, rel=0.01)


class TestVelocity:
    """Tests for Velocity dataclass."""

    def test_zero_factory(self):
        vel = Velocity.zero()
        assert vel.vx == 0.0
        assert vel.omega == 0.0

    def test_construction(self):
        vel = Velocity(vx=1.5, omega=-0.5)
        assert vel.vx == 1.5
        assert vel.omega == -0.5

"""
Integration tests for the compiled libmara_capi.so binary.

These tests load the real shared library (not mocks) and exercise the C API
directly. They run on any Linux machine — no hardware (GPIO/I2C/PWM) required.

Tests that need hardware are marked @pytest.mark.hil and skipped by default.

Run with:
    pytest host/tests/test_linux_integration.py -v
    pytest host/tests/test_linux_integration.py -v -m hil  # hardware tests
"""

import pytest
from pathlib import Path

from mara_host.bindings.mara_bindings import (
    MaraBindings,
    MaraBindingsError,
    MaraError,
    MaraState,
)


# ---------------------------------------------------------------------------
# Library fixture — skip entire module if the binary hasn't been built yet
# ---------------------------------------------------------------------------

LIB_PATH = Path(__file__).resolve().parents[2] / "firmware" / "mcu" / "build" / "libmara_capi.so"


def pytest_configure(config):
    pass  # markers already registered in pyproject.toml


@pytest.fixture(scope="module")
def lib() -> MaraBindings:
    """Load the real libmara_capi.so once for the whole module."""
    if not LIB_PATH.exists():
        pytest.skip(f"libmara_capi.so not found at {LIB_PATH} — run: mara build compile --profile linux_full --build-backend cmake")
    return MaraBindings(str(LIB_PATH))


# ---------------------------------------------------------------------------
# Utility API (no runtime handle needed)
# ---------------------------------------------------------------------------

class TestUtilityFunctions:
    """Stateless C API helpers — always work, no hardware needed."""

    def test_version_returns_semver(self, lib):
        v = lib.version()
        assert isinstance(v, str)
        parts = v.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    @pytest.mark.parametrize("code,expected", [
        (MaraError.OK,              "Success"),
        (MaraError.INVALID_ARG,     "Invalid argument"),
        (MaraError.NOT_INITIALIZED, "Runtime not initialized"),
        (MaraError.NOT_ARMED,       "Robot not armed"),
        (MaraError.HARDWARE,        "Hardware error"),
        (MaraError.NOT_SUPPORTED,   "Operation not supported"),
    ])
    def test_error_string(self, lib, code, expected):
        assert lib.error_string(int(code)) == expected

    @pytest.mark.parametrize("state,expected", [
        (MaraState.IDLE,    "IDLE"),
        (MaraState.ARMED,   "ARMED"),
        (MaraState.ACTIVE,  "ACTIVE"),
        (MaraState.FAULT,   "FAULT"),
        (MaraState.UNKNOWN, "UNKNOWN"),
    ])
    def test_state_string(self, lib, state, expected):
        assert lib.state_string(int(state)) == expected


# ---------------------------------------------------------------------------
# Runtime lifecycle without hardware
# ---------------------------------------------------------------------------

class TestRuntimeLifecycle:
    """Lifecycle tests using the real library — hardware init will fail on devboxes."""

    @pytest.fixture
    def handle(self, lib):
        """Create a runtime handle and destroy it after the test."""
        h = lib.create()
        yield h
        try:
            lib.destroy(h)
        except MaraBindingsError:
            pass  # already destroyed or never initialised — that's fine

    def test_create_returns_handle(self, lib):
        h = lib.create()
        assert h is not None
        lib.destroy(h)

    def test_create_destroy_cycle(self, lib):
        """Multiple create/destroy cycles must not crash or leak."""
        for _ in range(5):
            h = lib.create()
            assert h is not None
            lib.destroy(h)

    def test_init_without_hardware_returns_hardware_error(self, lib, handle):
        """On a devbox with no /dev/gpiochip0, init must fail with HARDWARE, not crash."""
        try:
            lib.init(handle, "{}")
            # If we have hardware (CI with GPIO passthrough, etc.) that's also valid
        except MaraBindingsError as e:
            assert e.error_code == MaraError.HARDWARE, (
                f"Expected HARDWARE error, got {e.error_code.name}: {e}"
            )

    def test_operations_before_init_return_not_initialized(self, lib, handle):
        """State-machine operations that require init must fail with NOT_INITIALIZED."""
        # estop/clear_estop intentionally bypass the initialized check (safety design)
        for op in (lib.arm, lib.disarm, lib.activate, lib.deactivate):
            with pytest.raises(MaraBindingsError) as exc:
                op(handle)
            assert exc.value.error_code == MaraError.NOT_INITIALIZED, (
                f"{op.__name__} returned {exc.value.error_code.name} instead of NOT_INITIALIZED"
            )

    def test_estop_works_before_init(self, lib, handle):
        """estop must work regardless of init state — it's a safety override."""
        # Should not raise; estop bypasses the initialized check by design
        lib.estop(handle)
        assert lib.get_state(handle) == MaraState.FAULT

    def test_clear_estop_works_before_init(self, lib, handle):
        """clear_estop must work regardless of init state."""
        # No fault → clear_estop is a no-op that returns OK
        lib.clear_estop(handle)
        # After estop → clear_estop resets to IDLE
        lib.estop(handle)
        lib.clear_estop(handle)
        assert lib.get_state(handle) == MaraState.IDLE

    def test_get_state_before_init(self, lib, handle):
        """get_state must be callable before init and return a valid MaraState."""
        state = lib.get_state(handle)
        assert isinstance(state, MaraState)

    def test_get_state_string_before_init(self, lib, handle):
        """get_state_string must succeed before init."""
        s = lib.get_state_string(handle)
        assert isinstance(s, str)
        assert len(s) > 0

    def test_destroy_without_init_is_safe(self, lib):
        """destroy() on a handle that was never init'd must not crash."""
        h = lib.create()
        lib.destroy(h)  # should not raise


# ---------------------------------------------------------------------------
# State machine — requires successful init (hardware-in-the-loop)
# ---------------------------------------------------------------------------

@pytest.mark.hil
class TestStateMachineHil:
    """State machine tests — require actual hardware (GPIO/I2C/PWM present)."""

    @pytest.fixture
    def started(self, lib):
        h = lib.create()
        lib.init(handle, "{}")
        lib.start(handle)
        yield h
        lib.stop(h)
        lib.destroy(h)

    def test_initial_state_is_idle(self, lib, started):
        assert lib.get_state(started) == MaraState.IDLE

    def test_arm_transitions_to_armed(self, lib, started):
        lib.arm(started)
        assert lib.get_state(started) == MaraState.ARMED

    def test_disarm_returns_to_idle(self, lib, started):
        lib.arm(started)
        lib.disarm(started)
        assert lib.get_state(started) == MaraState.IDLE

    def test_activate_requires_armed(self, lib, started):
        with pytest.raises(MaraBindingsError) as exc:
            lib.activate(started)
        assert exc.value.error_code == MaraError.INVALID_STATE

    def test_arm_activate_cycle(self, lib, started):
        lib.arm(started)
        lib.activate(started)
        assert lib.get_state(started) == MaraState.ACTIVE
        lib.deactivate(started)
        assert lib.get_state(started) == MaraState.ARMED

    def test_estop_from_active(self, lib, started):
        lib.arm(started)
        lib.activate(started)
        lib.estop(started)
        assert lib.get_state(started) == MaraState.FAULT

    def test_clear_estop_returns_to_idle(self, lib, started):
        lib.estop(started)
        lib.clear_estop(started)
        assert lib.get_state(started) == MaraState.IDLE

    def test_identity_json_is_valid(self, lib, started):
        import json
        identity = lib.get_identity(started)
        data = json.loads(identity)
        assert "version" in data
        assert "platform" in data
        assert data["platform"] == "linux"

    def test_health_json_is_valid(self, lib, started):
        import json
        health = lib.get_health(started)
        data = json.loads(health)
        assert "healthy" in data
        assert "state" in data
        assert "uptime_ms" in data

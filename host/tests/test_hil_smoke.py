# tests/test_hil_smoke.py
import asyncio
import os
import pytest

from mara_host.command.client import BaseAsyncRobotClient
from mara_host.transport.serial_transport import SerialTransport


def _get_mcu_port(request) -> str | None:
    """
    Prefer: CLI option --mcu-port, then env var MCU_PORT.
    Return None if no port is configured or if the port doesn't exist.
    """
    port = None
    try:
        port = request.config.getoption("--mcu-port")
    except Exception:
        port = None

    port = port or os.getenv("MCU_PORT")

    # Don't return a default - require explicit configuration for serial tests
    if not port:
        return None

    # Verify port exists
    if not os.path.exists(port):
        return None

    return port


async def _wait_until(predicate, timeout_s: float, interval_s: float = 0.02) -> bool:
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < timeout_s:
        if predicate():
            return True
        await asyncio.sleep(interval_s)
    return False


@pytest.mark.hil
@pytest.mark.asyncio
async def test_hil_handshake_and_basic_commands(request):
    port = _get_mcu_port(request)
    if not port:
        pytest.skip("No MCU port provided. Use --mcu-port=/dev/tty.usbserial-XXX or set MCU_PORT")

    transport = SerialTransport(port=port, baudrate=115200)

    # Real hardware needs looser timing than unit tests.
    client = BaseAsyncRobotClient(
        transport=transport,
        heartbeat_interval_s=0.2,
        connection_timeout_s=5.0,
        command_timeout_s=0.6,
        max_retries=2,
        require_version_match=True,
        handshake_timeout_s=5.0,
    )

    try:
        await client.start()

        # Handshake assertions
        assert client.version_verified is True
        assert client.protocol_version is not None
        assert client.robot_name is not None

        # ---- Stabilize link before issuing safety-state commands ----
        # Encourage some inbound traffic early.
        await client.send_ping()

        # If your client toggles connected only after receiving traffic, give it a moment.
        await _wait_until(lambda: client.is_connected, timeout_s=2.0)

        # Clear ESTOP defensively (safe even if not set)
        ok, err = await client.clear_estop()
        assert ok, err

        # Give heartbeat loop a moment to run at least once
        await asyncio.sleep(0.25)

        # ---- Safety-friendly command sequence ----
        ok, err = await client.arm()
        assert ok, err

        ok, err = await client.activate()
        assert ok, err

        ok, err = await client.set_vel(0.1, 0.0)
        assert ok, err

        # IMPORTANT: this is the ROBOT command stop, not the lifecycle stop()
        # If you renamed it, use client.cmd_stop() instead.
        ok, err = await client.cmd_stop() if hasattr(client, "cmd_stop") else await client.send_reliable("CMD_STOP")
        assert ok, err

        ok, err = await client.deactivate()
        assert ok, err

        ok, err = await client.disarm()
        assert ok, err

    finally:
        # ALWAYS close the serial port even if an assertion fails
        await client.stop()


@pytest.mark.hil
@pytest.mark.asyncio
async def test_hil_reboot_recovery(request):
    """
    Optional: If you can reset the board via DTR/RTS or external control,
    verify the host recovers cleanly. This version uses stop/start as a proxy,
    and guarantees cleanup via finally.
    """
    port = _get_mcu_port(request)
    if not port:
        pytest.skip("No MCU port provided. Use --mcu-port=/dev/tty.usbserial-XXX or set MCU_PORT")

    transport = SerialTransport(port=port, baudrate=115200)

    client = BaseAsyncRobotClient(
        transport=transport,
        heartbeat_interval_s=0.2,
        connection_timeout_s=5.0,
        command_timeout_s=0.6,
        max_retries=2,
        require_version_match=True,
        handshake_timeout_s=5.0,
    )

    try:
        await client.start()
        assert client.version_verified is True

        # Proxy for disconnect/reset: stop transport briefly
        await client.stop()
        await asyncio.sleep(0.5)

        # Restart and re-handshake
        await client.start()
        assert client.version_verified is True

    finally:
        # Ensure port is closed no matter what
        await client.stop()

@pytest.mark.hil
@pytest.mark.asyncio
async def test_hil_handshake_and_basic_commands(request):
    port = _get_mcu_port(request)
    if not port:
        pytest.skip("No MCU port provided")

    transport = SerialTransport(port=port, baudrate=115200)

    client = BaseAsyncRobotClient(
        transport=transport,
        heartbeat_interval_s=0.2,
        connection_timeout_s=5.0,
        command_timeout_s=0.6,
        max_retries=2,
        require_version_match=True,
        handshake_timeout_s=5.0,
    )

    try:
        await client.start()

        assert client.version_verified is True

        # Wait for heartbeats to transition robot DISCONNECTED → IDLE
        await asyncio.sleep(0.6)

        # Clear any E-stop
        ok, err = await client.clear_estop()
        # clear_estop may fail if not estopped, that's ok
        
        # Now arm should work
        ok, err = await client.arm()
        assert ok, f"arm failed: {err}, robot may still be in DISCONNECTED"

        ok, err = await client.activate()
        assert ok, f"activate failed: {err}"

        # Stop motion
        ok, err = await client.send_reliable("CMD_STOP", {}, wait_for_ack=True)
        assert ok, err

        ok, err = await client.deactivate()
        assert ok, err

        ok, err = await client.disarm()
        assert ok, err

    finally:
        await client.stop()
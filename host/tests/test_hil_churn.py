import asyncio
import os
import pytest
import contextlib

from mara_host.command.client import BaseAsyncRobotClient
from mara_host.transport.serial_transport import SerialTransport


def _get_mcu_port(request) -> str | None:
    """Return serial port if configured and exists, else None."""
    try:
        port = request.config.getoption("--mcu-port")
    except Exception:
        port = None
    port = port or os.getenv("MCU_PORT")
    if not port or not os.path.exists(port):
        return None
    return port


def _get_churn_cycles(request) -> int:
    try:
        v = request.config.getoption("--churn-cycles")
        if v:
            return int(v)
    except Exception:
        pass
    return int(os.getenv("CHURN_CYCLES", "10"))


async def _sleep_release_port():
    # macOS can take a moment to fully release /dev/cu.* handles
    await asyncio.sleep(0.25)


async def _wait_until(pred, timeout_s: float = 2.0, poll_s: float = 0.05):
    start = asyncio.get_running_loop().time()
    while True:
        if pred():
            return True
        if (asyncio.get_running_loop().time() - start) > timeout_s:
            return False
        await asyncio.sleep(poll_s)


@pytest.mark.hil
@pytest.mark.asyncio
async def test_hil_churn_connect_disconnect(request):
    """
    Churn test: repeatedly open/handshake/do a tiny safe command/close.
    Fails if any cycle can't handshake or leaves the port stuck.

    Run:
      pytest -m hil -q
      pytest -m hil --mcu-port=/dev/cu.usbserial-0001 --churn-cycles=25 -q
    """
    port = _get_mcu_port(request)
    if not port:
        pytest.skip("No MCU port provided. Use --mcu-port=... or set MCU_PORT")

    cycles = _get_churn_cycles(request)

    for i in range(cycles):
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

        # -------------------------------
        # NEW: Debug subscriptions
        # -------------------------------
        last_state = {"value": None}

        def _on_state(evt):
            # evt is {"state": "..."} per your client.py publish
            s = None
            if isinstance(evt, dict):
                s = evt.get("state")
            last_state["value"] = s
            print(f"[HIL][cycle {i}] STATE = {s}")

        client.bus.subscribe("state.changed", _on_state)

        # Print key ACKs verbatim so we see "state"/"error"/etc from firmware
        client.bus.subscribe("cmd.CMD_CLEAR_ESTOP_ACK", lambda obj: print(f"[HIL][cycle {i}] ACK CLEAR_ESTOP: {obj}"))
        client.bus.subscribe("cmd.CMD_STOP_ACK",       lambda obj: print(f"[HIL][cycle {i}] ACK STOP: {obj}"))
        client.bus.subscribe("cmd.CMD_DEACTIVATE_ACK", lambda obj: print(f"[HIL][cycle {i}] ACK DEACTIVATE: {obj}"))
        client.bus.subscribe("cmd.CMD_DISARM_ACK",     lambda obj: print(f"[HIL][cycle {i}] ACK DISARM: {obj}"))
        client.bus.subscribe("cmd.CMD_ARM_ACK",        lambda obj: print(f"[HIL][cycle {i}] ACK ARM: {obj}"))
        client.bus.subscribe("cmd.CMD_ACTIVATE_ACK",   lambda obj: print(f"[HIL][cycle {i}] ACK ACTIVATE: {obj}"))

        try:
            await client.start()

            assert client.version_verified is True
            assert client.protocol_version is not None
            assert client.robot_name is not None

            # Encourage immediate inbound traffic (helps MCU leave DISCONNECTED)
            await client.send_ping()
            ok_connected = await _wait_until(lambda: client.is_connected, timeout_s=2.0)
            print(f"[HIL][cycle {i}] connected={client.is_connected} (wait_ok={ok_connected})")

            # Give MCU a beat to publish its first state transition, if it does
            await asyncio.sleep(0.2)

            # Minimal safe interaction
            ok, err = await client.clear_estop()
            # If your firmware returns "not_estopped" or similar, you can allow it:
            assert ok, err

            # If ARM is racy right after connect, retry briefly
            arm_ok = False
            arm_err = None
            for _ in range(10):
                ok, err = await client.arm()
                if ok:
                    arm_ok = True
                    break
                arm_err = err
                await asyncio.sleep(0.1)

            assert arm_ok, f"arm failed: {arm_err} (last_state={last_state['value']})"

            ok, err = await client.activate()
            assert ok, err

            ok, err = await client.set_vel(0.0, 0.0)
            assert ok, err

            ok, err = await client.deactivate()
            assert ok, err

            ok, err = await client.disarm()
            assert ok, err

        finally:
            # IMPORTANT: close client/transport even if asserts fail
            # Prefer the public lifecycle stop() so heartbeat/monitor loops stop cleanly
            with pytest.raises(Exception) if False else contextlib.suppress(Exception):
                await client.stop()

            await _sleep_release_port()

        # Give the MCU a beat between cycles (USB/serial stacks can be touchy)
        await asyncio.sleep(0.1)

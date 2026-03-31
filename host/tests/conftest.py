# tests/conftest.py

import pytest
from tests.fakes.fake_async_transport import FakeAsyncTransport
from tests.helpers import CapturingBus
import os
import json
import time
from pathlib import Path
import asyncio


# ============== Existing Fixtures ==============

@pytest.fixture
def bus():
    return CapturingBus()


@pytest.fixture
def transport():
    return FakeAsyncTransport(auto_ack=True)


# ============== Pytest Configuration ==============

def pytest_addoption(parser):
    parser.addoption("--mcu-port", action="store", default=os.getenv("MCU_PORT", ""))
    parser.addoption("--mara-host", action="store", default=os.getenv("MARA_HOST", "10.0.0.60"))
    parser.addoption("--mara-port", action="store", type=int, default=int(os.getenv("MARA_PORT", "3333")))
    parser.addoption("--run-hil", action="store_true", default=False, help="Run HIL tests")
    parser.addoption("--hil-timeout", action="store", type=float, default=5.0, help="HIL command timeout")
    parser.addoption("--skip-dc-motor", action="store_true", default=False, help="Skip DC motor tests")
    parser.addoption("--skip-stepper", action="store_true", default=False, help="Skip stepper motor tests")
    parser.addoption("--skip-encoder", action="store_true", default=False, help="Skip encoder tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "hil: hardware-in-the-loop tests (requires MCU connected)")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "motion: tests that cause physical motion")


def pytest_collection_modifyitems(config, items):
    """Skip HIL tests unless --run-hil is specified, and hardware-specific tests if opted out."""
    if not config.getoption("--run-hil"):
        skip_hil = pytest.mark.skip(reason="Need --run-hil option to run HIL tests")
        for item in items:
            if "hil" in item.keywords:
                item.add_marker(skip_hil)

    # Skip hardware-specific tests if opted out
    skip_markers = {
        "dc_motor": ("--skip-dc-motor", "DC motor tests skipped (use --skip-dc-motor=false to enable)"),
        "stepper": ("--skip-stepper", "Stepper tests skipped"),
        "encoder": ("--skip-encoder", "Encoder tests skipped"),
    }

    for marker, (option, reason) in skip_markers.items():
        if config.getoption(option):
            skip = pytest.mark.skip(reason=reason)
            for item in items:
                if marker in item.keywords:
                    item.add_marker(skip)


# ============== HIL Fixtures ==============

@pytest.fixture(scope="session")
def mara_host(request) -> str:
    return request.config.getoption("--mara-host")


@pytest.fixture(scope="session")
def mara_port(request) -> int:
    return request.config.getoption("--mara-port")


@pytest.fixture(scope="session")
def hil_timeout(request) -> float:
    return request.config.getoption("--hil-timeout")


def _find_serial_port() -> str:
    """Auto-detect serial port for MCU."""
    import glob
    import sys

    if sys.platform == "darwin":
        # macOS: prefer usbmodem (ESP32-S3 native USB) over usbserial
        patterns = ["/dev/tty.usbmodem*", "/dev/tty.usbserial*", "/dev/tty.SLAB*"]
    elif sys.platform == "linux":
        patterns = ["/dev/ttyACM*", "/dev/ttyUSB*"]
    else:
        # Windows - return empty, user must specify
        return ""

    for pattern in patterns:
        ports = sorted(glob.glob(pattern))
        if ports:
            return ports[0]
    return ""


@pytest.fixture
async def mcu(request, hil_timeout, tmp_path):
    """
    Connected MaraClient for HIL tests.
    Defaults to serial transport. Use --mcu-port to specify port.
    Ensures safe state on setup and teardown.
    """
    from mara_host.transport.serial_transport import SerialTransport
    from mara_host.command.client import MaraClient

    # Get port from CLI or auto-detect
    port = request.config.getoption("--mcu-port")
    if not port:
        port = _find_serial_port()
    if not port:
        pytest.skip("No serial port found. Use --mcu-port to specify.")

    transport = SerialTransport(port, baudrate=115200)
    client = MaraClient(
        transport,
        command_timeout_s=hil_timeout,
        handshake_timeout_s=hil_timeout * 2,
        verbose=True,
    )

    # Attach event logging
    test_name = request.node.name
    log_path = tmp_path / f"hil_{test_name}.log"
    close_log = attach_bus_dump(client, str(log_path))

    try:
        await client.start()

        # Ensure clean starting state
        for cmd in ["CMD_CLEAR_ESTOP", "CMD_STOP", "CMD_DEACTIVATE", "CMD_DISARM"]:
            try:
                await client.send_reliable(cmd)
            except Exception:
                pass

        yield client

    finally:
        # Safe teardown
        for cmd in ["CMD_STOP", "CMD_DEACTIVATE", "CMD_DISARM"]:
            try:
                await client.send_reliable(cmd)
            except Exception:
                pass

        try:
            await client.stop()
        except Exception:
            pass

        close_log()


@pytest.fixture
async def armed_mcu(mcu):
    """MCU in ARMED state."""
    ok, err = await mcu.send_reliable("CMD_ARM")
    assert ok, f"Failed to arm: {err}"
    yield mcu


@pytest.fixture
async def active_mcu(armed_mcu):
    """MCU in ACTIVE state."""
    ok, err = await armed_mcu.send_reliable("CMD_ACTIVATE")
    assert ok, f"Failed to activate: {err}"
    yield armed_mcu


# ============== HIL Assertion Helper ==============

@pytest.fixture
def hil(mcu):
    """Helper for cleaner HIL assertions."""
    class HIL:
        def __init__(self, client):
            self.client = client
            self._capabilities = None

        async def get_capabilities(self):
            """Get MCU capabilities (cached). Returns features list from handshake."""
            if self._capabilities is None:
                # Features are populated during client handshake
                # Access directly from client instead of sending a command
                self._capabilities = self.client.features or []
            return self._capabilities

        async def has_capability(self, cap: str) -> bool:
            """Check if MCU has a capability (e.g., 'dc_motor', 'servo')."""
            features = await self.get_capabilities()
            cap_lower = cap.lower()
            return cap_lower in features or cap in features

        async def require_capability(self, cap: str):
            """Skip test if capability not available."""
            if not await self.has_capability(cap):
                pytest.skip(f"MCU does not have {cap} capability")

        async def send(self, cmd, payload=None):
            """Send command and return response."""
            ok, err = await self.client.send_reliable(cmd, payload or {})
            return {"ok": ok, "error": err}

        async def assert_ok(self, cmd, payload=None, msg=""):
            ok, err = await self.client.send_reliable(cmd, payload or {})
            assert ok, f"{cmd} failed: {err}. {msg}"
            return ok, err

        async def assert_fails(self, cmd, payload=None, expected_error=None):
            ok, err = await self.client.send_reliable(cmd, payload or {})
            assert not ok, f"{cmd} should have failed"
            if expected_error:
                assert expected_error in str(err)
            return ok, err

        async def clear_signals(self):
            """Clear all signals from the signal bus."""
            try:
                resp = await self.send("CMD_CTRL_SIGNALS_LIST", {})
                if resp and resp.get("ok"):
                    # Get signals from response - adjust based on actual response format
                    ok, err = await self.client.send_reliable("CMD_CTRL_SIGNALS_LIST", {})
                    # For now just try to delete common test IDs
                    for sig_id in [100, 101, 102, 110, 200, 201, 202, 203, 300, 301, 302, 303, 310, 311]:
                        try:
                            await self.client.send_reliable("CMD_CTRL_SIGNAL_DELETE", {"id": sig_id})
                        except:
                            pass
            except Exception:
                pass

    return HIL(mcu)


# ============== Clear Signals Fixture ==============

@pytest.fixture
async def clear_signals(hil):
    """Fixture to clear signals - use in test classes that need it."""
    await hil.clear_signals()
    yield
    await hil.clear_signals()


# ============== Event Loop ==============

@pytest.fixture
def event_loop():
    """Fresh loop per test."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        pending = asyncio.all_tasks(loop)
        for t in pending:
            t.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


# ============== Bus Dump Helper ==============

def attach_bus_dump(client, path: str, cycle: int | None = None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a", buffering=1)

    def _ser(x):
        try:
            return json.dumps(x, default=str, ensure_ascii=False)
        except Exception:
            return repr(x)

    def log(topic, obj):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cyc = f"cycle={cycle} " if cycle is not None else ""
        f.write(f"{ts} {cyc}{topic} {_ser(obj)}\n")

    sub = getattr(client.bus, "subscribe", None)
    if not callable(sub):
        return lambda: f.close()

    wildcard = getattr(client.bus, "subscribe_all", None)
    if callable(wildcard):
        wildcard(lambda topic, obj: log(topic, obj))
    else:
        for t in ["state.changed", "connection.lost", "connection.restored",
                  "telemetry", "telemetry.raw", "telemetry.binary"]:
            try:
                sub(t, lambda obj, tt=t: log(tt, obj))
            except Exception:
                pass

    return lambda: f.close()

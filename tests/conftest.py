# tests/conftest.py

import pytest
from tests.fakes.fake_async_transport import FakeAsyncTransport
from tests.helpers import CapturingBus
import os
import json
import time
from pathlib import Path
import asyncio
from typing import Optional


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
    parser.addoption("--robot-host", action="store", default=os.getenv("ROBOT_HOST", "10.0.0.60"))
    parser.addoption("--robot-port", action="store", type=int, default=int(os.getenv("ROBOT_PORT", "3333")))
    parser.addoption("--run-hil", action="store_true", default=False, help="Run HIL tests")
    parser.addoption("--hil-timeout", action="store", type=float, default=5.0, help="HIL command timeout")


def pytest_configure(config):
    config.addinivalue_line("markers", "hil: hardware-in-the-loop tests (requires MCU connected)")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "motion: tests that cause physical motion")


def pytest_collection_modifyitems(config, items):
    """Skip HIL tests unless --run-hil is specified."""
    if not config.getoption("--run-hil"):
        skip_hil = pytest.mark.skip(reason="Need --run-hil option to run HIL tests")
        for item in items:
            if "hil" in item.keywords:
                item.add_marker(skip_hil)


# ============== HIL Fixtures ==============

@pytest.fixture(scope="session")
def mara_host(request) -> str:
    return request.config.getoption("--robot-host")


@pytest.fixture(scope="session")
def robot_port(request) -> int:
    return request.config.getoption("--robot-port")


@pytest.fixture(scope="session")
def hil_timeout(request) -> float:
    return request.config.getoption("--hil-timeout")


@pytest.fixture
async def robot(request, mara_host, robot_port, hil_timeout, tmp_path):
    """
    Connected AsyncRobotClient for HIL tests.
    Ensures safe state on setup and teardown.
    """
    from mara_host.transport.tcp_transport import AsyncTcpTransport
    from mara_host.command.client import AsyncRobotClient
    
    transport = AsyncTcpTransport(mara_host, robot_port)
    client = AsyncRobotClient(
        transport,
        command_timeout_s=hil_timeout,
        handshake_timeout_s=hil_timeout * 2,
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
async def armed_robot(robot):
    """Robot in ARMED state."""
    ok, err = await robot.send_reliable("CMD_ARM")
    assert ok, f"Failed to arm: {err}"
    yield robot


@pytest.fixture
async def active_robot(armed_robot):
    """Robot in ACTIVE state."""
    ok, err = await armed_robot.send_reliable("CMD_ACTIVATE")
    assert ok, f"Failed to activate: {err}"
    yield armed_robot


# ============== HIL Assertion Helper ==============

@pytest.fixture
def hil(robot):
    """Helper for cleaner HIL assertions."""
    class HIL:
        def __init__(self, r):
            self.robot = r
        
        async def send(self, cmd, payload=None):
            """Send command and return response."""
            ok, err = await self.robot.send_reliable(cmd, payload or {})
            return {"ok": ok, "error": err}
        
        async def assert_ok(self, cmd, payload=None, msg=""):
            ok, err = await self.robot.send_reliable(cmd, payload or {})
            assert ok, f"{cmd} failed: {err}. {msg}"
            return ok, err
        
        async def assert_fails(self, cmd, payload=None, expected_error=None):
            ok, err = await self.robot.send_reliable(cmd, payload or {})
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
                    ok, err = await self.robot.send_reliable("CMD_CTRL_SIGNALS_LIST", {})
                    # For now just try to delete common test IDs
                    for sig_id in [100, 101, 102, 110, 200, 201, 202, 203, 300, 301, 302, 303, 310, 311]:
                        try:
                            await self.robot.send_reliable("CMD_CTRL_SIGNAL_DELETE", {"id": sig_id})
                        except:
                            pass
            except Exception:
                pass
    
    return HIL(robot)


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
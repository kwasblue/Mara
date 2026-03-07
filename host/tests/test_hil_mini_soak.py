# tests/test_hil_mini_soak.py
import asyncio
import os
import json
import time
from pathlib import Path
from collections import deque
import pytest

from mara_host.command.client import BaseMaraClient
from mara_host.transport.serial_transport import SerialTransport


def pytest_addoption(parser):
    parser.addoption("--mcu-port", action="store", default=None,
                     help="MCU serial port (e.g. /dev/cu.usbserial-0001)")
    parser.addoption("--soak-seconds", action="store", default=None,
                     help="Mini soak duration in seconds (default: 120)")

    # Must be < motion_timeout_ms (yours is 500ms)
    parser.addoption("--cmd-interval", action="store", default=None,
                     help="Seconds between motion keepalives (default: 0.2)")
    parser.addoption("--ping-interval", action="store", default=None,
                     help="Seconds between pings (default: 1.0)")
    parser.addoption("--vel-eps", action="store", default=None,
                     help="Tiny non-zero linear velocity to satisfy MCU watchdog (default: 0.01)")

    parser.addoption("--hil-log-dir", action="store", default=None,
                     help="Directory for HIL logs (default: ./logs)")
    parser.addoption("--hil-dump-events", action="store_true", default=False,
                     help="If set, dumps selected bus events to a log file")


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


def _get_float_opt(request, cli_name: str, env_name: str, default: float) -> float:
    v = None
    try:
        v = request.config.getoption(cli_name)
    except Exception:
        v = None
    if v is None:
        ev = os.getenv(env_name)
        return float(ev) if ev is not None else float(default)
    return float(v)


def _get_log_dir(request) -> str:
    try:
        d = request.config.getoption("--hil-log-dir")
    except Exception:
        d = None
    return d or os.getenv("HIL_LOG_DIR", "logs")


def _want_event_dump(request) -> bool:
    try:
        v = request.config.getoption("--hil-dump-events")
    except Exception:
        v = False
    env = os.getenv("HIL_DUMP_EVENTS", "").strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(v or env)


def _ensure_dir(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


def _now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe_json(obj) -> str:
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        return repr(obj)


async def _wait_until(predicate, timeout_s: float, interval_s: float = 0.05) -> bool:
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < timeout_s:
        if predicate():
            return True
        await asyncio.sleep(interval_s)
    return False


def _attach_bus_dump(client, filepath: str, tag: str = ""):
    _ensure_dir(str(Path(filepath).parent))
    f = open(filepath, "a", buffering=1)

    def _write(topic: str, payload):
        t = f"{tag} " if tag else ""
        f.write(f"{_now_ts()} {t}{topic} {_safe_json(payload)}\n")

    sub = getattr(client.bus, "subscribe", None)
    sub_all = getattr(client.bus, "subscribe_all", None)

    if callable(sub_all):
        try:
            sub_all(lambda topic, payload: _write(str(topic), payload))
        except Exception:
            pass

    if callable(sub):
        for topic in (
            "connection.lost",
            "connection.restored",
            "state.changed",
            "mode.changed",
            "safety.triggered",
            "safety.cleared",
            "cmd.ack",
            "cmd.nack",
            "telemetry",
        ):
            try:
                sub(topic, lambda payload, t=topic: _write(t, payload))
            except Exception:
                pass

    def close():
        try:
            f.close()
        except Exception:
            pass

    return close


def _dump_snapshot(client, filepath: str, reason: str, recent: list[dict] | None = None, extra: dict | None = None):
    _ensure_dir(str(Path(filepath).parent))

    snap = {
        "ts": _now_ts(),
        "reason": reason,
        "client": {
            "is_connected": bool(getattr(client, "is_connected", False)),
            "version_verified": getattr(client, "version_verified", None),
            "protocol_version": getattr(client, "protocol_version", None),
            "robot_name": getattr(client, "robot_name", None),
        },
    }

    try:
        snap["stats"] = client.get_stats()
    except Exception as e:
        snap["stats_error"] = repr(e)

    if recent:
        snap["recent"] = recent[-200:]

    if extra:
        snap["extra"] = extra

    with open(filepath, "a", buffering=1) as f:
        f.write(_safe_json(snap) + "\n")


@pytest.mark.hil
@pytest.mark.asyncio
async def test_hil_mini_soak_link_stability(request):
    """
    Mini soak test:
      - handshake
      - clear_estop -> arm -> activate
      - keepalive motion with a tiny NON-ZERO velocity to satisfy MCU motion watchdog
      - ping periodically
      - fail on connection drops
      - dump cmd trace + snapshots on failure
    """
    await asyncio.sleep(1.0)
    port = _get_mcu_port(request)
    if not port:
        pytest.skip("No MCU port provided. Use --mcu-port=... or set MCU_PORT")

    soak_s = _get_float_opt(request, "--soak-seconds", "SOAK_SECONDS", 120.0)
    cmd_interval = _get_float_opt(request, "--cmd-interval", "CMD_INTERVAL", 0.05)
    ping_interval = _get_float_opt(request, "--ping-interval", "PING_INTERVAL", 1.0)
    vel_eps = _get_float_opt(request, "--vel-eps", "VEL_EPS", 0.01)

    log_dir = _get_log_dir(request)
    _ensure_dir(log_dir)

    cmd_log_path = str(Path(log_dir) / "hil_cmd_trace.jsonl")
    snap_log_path = str(Path(log_dir) / "hil_fail_snapshot.jsonl")
    bus_log_path = str(Path(log_dir) / "hil_bus_dump.log")

    transport = SerialTransport(port=port, baudrate=115200)

    client = BaseMaraClient(
        transport=transport,
        heartbeat_interval_s=0.2,
        connection_timeout_s=5.0,
        command_timeout_s=0.6,
        max_retries=2,
        require_version_match=True,
        handshake_timeout_s=5.0,
    )

    recent = deque(maxlen=400)

    def _log_cmd(entry: dict):
        recent.append(entry)
        with open(cmd_log_path, "a", buffering=1) as f:
            f.write(_safe_json(entry) + "\n")

    close_bus_dump = None
    if _want_event_dump(request):
        close_bus_dump = _attach_bus_dump(client, bus_log_path, tag="mini_soak")

    lost_count = 0

    def _on_lost(_evt=None):
        nonlocal lost_count
        lost_count += 1

    sub = getattr(client.bus, "subscribe", None)
    if callable(sub):
        sub("connection.lost", lambda evt: _on_lost(evt))

    def _pending_size() -> int | None:
        try:
            stats = client.get_stats()
        except Exception:
            return None
        if not isinstance(stats, dict):
            return None
        for k in ("pending", "pending_count", "inflight"):
            v = stats.get(k)
            if isinstance(v, int):
                return v
        return None

    async def call(name: str, coro, payload: dict | None = None):
        t0 = asyncio.get_event_loop().time()
        _log_cmd({"ts": _now_ts(), "dir": "tx", "cmd": name, "payload": payload})
        try:
            res = await coro
        except Exception as e:
            _log_cmd({"ts": _now_ts(), "dir": "rx", "cmd": name, "ok": False, "err": repr(e)})
            raise
        dt = asyncio.get_event_loop().time() - t0

        if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], bool):
            ok, err = res
            _log_cmd({"ts": _now_ts(), "dir": "rx", "cmd": name, "ok": ok, "err": err, "dt_s": dt})
            return ok, err
        else:
            _log_cmd({"ts": _now_ts(), "dir": "rx", "cmd": name, "result": res, "dt_s": dt})
            return res

    async def _robot_cmd_stop() -> tuple[bool, str | None]:
        try:
            return await client.send_reliable("CMD_STOP", {}, wait_for_ack=True)
        except TypeError:
            return await client.send_reliable("CMD_STOP")

    started = False
    armed = False
    activated = False

    try:
        await call("client.start", client.start())
        started = True
        # Ensure robot is in clean IDLE state (previous tests may have left it elsewhere)
        await asyncio.sleep(0.3)
        try:
            await client.send_reliable("CMD_STOP", {})
        except:
            pass
        try:
            await client.deactivate()
        except:
            pass  
        try:
            await client.disarm()
        except:
            pass
        await asyncio.sleep(0.2)

        assert client.version_verified is True
        assert client.protocol_version is not None
        assert client.robot_name is not None

        await call("ping", client.send_ping())
        await _wait_until(lambda: client.is_connected, timeout_s=2.0)

        ok, err = await call("clear_estop", client.clear_estop())
        assert ok, err

        ok, err = await call("arm", client.arm())
        assert ok, err
        armed = True

        ok, err = await call("activate", client.activate())
        assert ok, err
        activated = True

        # Critical: verify we can send a motion command NOW (using non-zero eps).
        ok, err = await call(
            "set_vel_keepalive",
            client.set_vel(vel_eps, 0.0),
        )
        if not ok:
            _dump_snapshot(client, snap_log_path, "post_activate_motion_rejected",
                           recent=list(recent), extra={"err": err, "vel_eps": vel_eps})
        assert ok, err

        baseline_pending = _pending_size()

        start_t = asyncio.get_event_loop().time()
        end_t = start_t + soak_s

        next_ping = start_t
        next_cmd = start_t
        next_pending_check = start_t

        # Alternate sign to avoid "walking" away over time (still tiny).
        sign = 1.0

        while asyncio.get_event_loop().time() < end_t:
            now = asyncio.get_event_loop().time()

            if now >= next_ping:
                await call("ping", client.send_ping())
                next_ping = now + ping_interval

            if now >= next_cmd:
                v = sign * vel_eps
                sign *= -1.0

                ok, err = await call(
                    "set_vel_keepalive",
                    client.set_vel(v, 0.0),
                )
                if not ok:
                    _dump_snapshot(client, snap_log_path, "set_vel_failed",
                                   recent=list(recent),
                                   extra={"err": err, "cmd_interval": cmd_interval, "vel_eps": vel_eps})
                assert ok, err
                next_cmd = now + cmd_interval

            if lost_count != 0:
                _dump_snapshot(client, snap_log_path, "connection_lost",
                               recent=list(recent), extra={"lost_count": lost_count})
            assert lost_count == 0, f"Connection dropped {lost_count} times during soak"

            if now >= next_pending_check:
                p = _pending_size()
                if p is not None and baseline_pending is not None and p > baseline_pending + 3:
                    _dump_snapshot(client, snap_log_path, "pending_grew",
                                   recent=list(recent), extra={"pending": p, "baseline": baseline_pending})
                    assert p <= baseline_pending + 3, f"Pending grew unexpectedly: {p} (baseline {baseline_pending})"
                next_pending_check = now + 1.0

            await asyncio.sleep(0.02)

        ok, err = await call("CMD_STOP", _robot_cmd_stop())
        assert ok, err

        ok, err = await call("deactivate", client.deactivate())
        assert ok, err
        activated = False

        ok, err = await call("disarm", client.disarm())
        assert ok, err
        armed = False

    finally:
        try:
            if close_bus_dump:
                close_bus_dump()
        except Exception:
            pass

        try:
            if started:
                if activated:
                    await client.deactivate()
                if armed:
                    await client.disarm()
        except Exception:
            pass

        try:
            if started:
                await client.stop()
        except Exception:
            pass
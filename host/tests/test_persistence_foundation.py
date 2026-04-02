import asyncio
from pathlib import Path

import pytest

from mara_host.config import RobotConfig
from mara_host.services.control.control_graph_service import ControlGraphService
from mara_host.services.persistence import McuDiagnosticsService
from mara_host.services.persistence.store import CalibrationStore, ControlGraphStore, DiagnosticRecordStore
from tests.fakes.fake_mara_server import FakeMaraTcpServer
from mara_host.command.client import MaraClient
from mara_host.transport.tcp_transport import AsyncTcpTransport
from mara_host.services.transport.connection_service import ConnectionConfig, ConnectionService, TransportType


async def _build_service(fake_server, store=None):
    transport = AsyncTcpTransport(fake_server.host, fake_server.port)
    client = MaraClient(transport, verbose=False)
    await client.start()
    return client, ControlGraphService(client, persistence_store=store)


@pytest.mark.asyncio
async def test_control_graph_restore_from_persistence_forces_safe_disabled_state(tmp_path: Path):
    store = ControlGraphStore(tmp_path)
    store.save_graph(
        {
            "schema_version": 1,
            "slots": [
                {
                    "id": "persisted_graph",
                    "enabled": True,
                    "rate_hz": 20,
                    "source": {"type": "constant", "params": {"value": 1.0}},
                    "transforms": [],
                    "sink": {"type": "gpio_write", "params": {"channel": 0}},
                }
            ],
        }
    )

    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server, store=store)
    try:
        result = await service.restore_from_persistence()
        assert result.ok
        assert result.data["restored"] is True
        assert result.data["restored_safely"] is True
        assert result.data["restored_from_enabled_state"] is True
        assert result.data["enabled"] is False
        assert result.data["graph"]["slots"][0]["enabled"] is False

        status = await service.status()
        assert status.ok
        assert status.data["present"] is True
        assert status.data["enabled"] is False
        assert status.data["slots"][0]["enabled"] is False

        persisted = store.load_graph()
        assert persisted is not None
        assert persisted["slots"][0]["enabled"] is False
    finally:
        await client.stop()
        await fake_mara_server.stop()


def test_robot_config_parses_persistence_policy_and_flags_live_state_restore():
    cfg = RobotConfig.from_dict(
        {
            "name": "testbot",
            "transport": {"type": "serial", "port": "/dev/null"},
            "persistence": {
                "root_dir": "/tmp/mara-persistence",
                "control_graph": {"enabled": True, "backend": "host_file", "restore": True},
                "calibrations": {"enabled": True, "backend": "host_file"},
            },
        }
    )
    assert cfg.persistence.root_dir == "/tmp/mara-persistence"
    assert cfg.persistence.control_graph.enabled is True
    assert cfg.persistence.calibrations.enabled is True

    invalid = RobotConfig.from_dict(
        {
            "name": "testbot",
            "transport": {"type": "serial", "port": "/dev/null"},
            "persistence": {
                "control_graph": {"enabled": True, "restore_live_state": True},
            },
        },
        validate=False,
    )
    report = invalid.validate_report()
    assert any("restore_live_state must remain false" in err for err in report.errors)


def test_calibration_and_diagnostic_stores_round_trip(tmp_path: Path):
    calibration_store = CalibrationStore(tmp_path)
    diagnostic_store = DiagnosticRecordStore(tmp_path)

    calibration_store.upsert("servo0", {"min_us": 500, "max_us": 2500}, calibration_type="servo")
    diagnostic_store.append("boot_check", {"ok": True, "temperature_c": 31.2})

    calibration_payload = calibration_store.load()
    diagnostic_payload = diagnostic_store.load()

    assert calibration_payload["records"]["servo0"]["type"] == "servo"
    assert calibration_payload["records"]["servo0"]["values"]["max_us"] == 2500
    assert diagnostic_payload["records"][0]["name"] == "boot_check"
    assert diagnostic_payload["records"][0]["details"]["ok"] is True


@pytest.mark.asyncio
async def test_mcu_diagnostics_service_reads_persistence_telemetry_and_can_clear_host_records(tmp_path: Path):
    diagnostic_store = DiagnosticRecordStore(tmp_path)
    fake_mara_server = await FakeMaraTcpServer().start()
    transport = AsyncTcpTransport(fake_mara_server.host, fake_mara_server.port)
    client = MaraClient(transport, verbose=False)
    await client.start()

    service = McuDiagnosticsService(client, diagnostics_store=diagnostic_store)
    try:
        telemetry = {
            "type": "TELEMETRY",
            "persistence": {
                "ready": True,
                "diagnostics": {
                    "boot_count": 3,
                    "last_reset_reason": 7,
                    "host_timeout_count": 2,
                    "estop_count": 1,
                },
                "config_mirror": {
                    "valid": True,
                    "version": 1,
                },
            },
        }
        client.bus.publish("telemetry", telemetry)

        result = await service.read()
        assert result.ok
        assert result.data["ready"] is True
        assert result.data["diagnostics"]["boot_count"] == 3
        assert result.data["diagnostics"]["estop_count"] == 1
        assert result.data["config_mirror"]["valid"] is True

        persisted = diagnostic_store.load()
        assert persisted is not None
        assert persisted["records"][-1]["name"] == "mcu_persistence"
        assert persisted["records"][-1]["details"]["diagnostics"]["host_timeout_count"] == 2

        cleared = service.clear_persisted_records()
        assert cleared.ok
        assert cleared.data["scope"] == "host_store"
        assert diagnostic_store.load() is None
    finally:
        service.close()
        await client.stop()
        await fake_mara_server.stop()


def test_mcu_diagnostics_service_clear_host_records_explains_missing_store():
    class _Bus:
        def subscribe(self, *_args, **_kwargs):
            return None
        def unsubscribe(self, *_args, **_kwargs):
            return None
    class _Client:
        bus = _Bus()
    service = McuDiagnosticsService(_Client(), diagnostics_store=None)
    try:
        result = service.clear_persisted_records()
        assert not result.ok
        assert "--clear-host-records" in result.error
        assert "persistence.diagnostics" in result.error
    finally:
        service.close()


@pytest.mark.asyncio
async def test_mcu_diagnostics_service_can_query_and_reset_firmware_snapshot(tmp_path: Path):
    diagnostic_store = DiagnosticRecordStore(tmp_path)
    fake_mara_server = await FakeMaraTcpServer().start()
    transport = AsyncTcpTransport(fake_mara_server.host, fake_mara_server.port)
    client = MaraClient(transport, verbose=False)
    await client.start()

    service = McuDiagnosticsService(client, diagnostics_store=diagnostic_store)
    try:
        queried = await service.query()
        assert queried.ok
        assert queried.data["ready"] is True
        assert queried.data["diagnostics"]["boot_count"] == 3
        assert queried.data["diagnostics"]["host_timeout_count"] == 2
        assert queried.data["config_mirror"]["network"]["device_name"] == "fake-mara"

        reset = await service.reset(clear_host_records=True)
        assert reset.ok
        assert reset.data["reset"] is True
        assert reset.data["host_records_cleared"] is True
        assert reset.data["diagnostics"]["boot_count"] == 3
        assert reset.data["diagnostics"]["host_timeout_count"] == 0
        assert reset.data["snapshot"]["diagnostics"]["estop_count"] == 0

        cached = service.read_cached()
        assert cached.ok
        assert cached.data["diagnostics"]["motion_timeout_count"] == 0

        persisted = diagnostic_store.load()
        assert persisted is None
    finally:
        service.close()
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_mcu_diagnostics_service_falls_back_to_telemetry_when_ack_payload_is_late():
    class _Bus:
        def __init__(self):
            self._subs = {}

        def subscribe(self, topic, handler):
            self._subs.setdefault(topic, []).append(handler)

        def unsubscribe(self, topic, handler):
            handlers = self._subs.get(topic, [])
            if handler in handlers:
                handlers.remove(handler)

        def publish(self, topic, data):
            for handler in list(self._subs.get(topic, [])):
                handler(data)

    class _Client:
        def __init__(self):
            self.bus = _Bus()
            self.calls = 0

        async def send_reliable(self, _command, _payload):
            self.calls += 1
            return True, None

    client = _Client()
    service = McuDiagnosticsService(
        client,
        ack_timeout_s=0.01,
        retry_count=2,
        retry_delay_s=0.0,
        refresh_timeout_s=0.1,
    )
    try:
        async def _emit_telemetry():
            await asyncio.sleep(0.03)
            client.bus.publish(
                "telemetry",
                {
                    "type": "TELEMETRY",
                    "persistence": {
                        "ready": True,
                        "diagnostics": {"boot_count": 9, "host_timeout_count": 1},
                    },
                },
            )

        task = asyncio.create_task(_emit_telemetry())
        result = await service.query()
        await task

        assert result.ok
        assert result.data["diagnostics"]["boot_count"] == 9
        assert result.data["fallback"] == "telemetry"
        assert client.calls == 2
    finally:
        service.close()


def test_connection_config_defaults_to_more_tolerant_handshake_budget():
    config = ConnectionConfig(transport_type=TransportType.SERIAL)
    assert config.handshake_timeout_s == 2.0


@pytest.mark.asyncio
async def test_connection_service_passes_handshake_timeout_to_client(monkeypatch):
    captured = {}

    class _DummyClient:
        def __init__(self, transport, **kwargs):
            captured["transport"] = transport
            captured.update(kwargs)
            self.firmware_version = "fw"
            self.protocol_version = 1
            self.board = "board"
            self.platform_name = "name"
            self.features = []
            self.capabilities = 0

        async def start(self):
            return None

        async def stop(self):
            return None

    monkeypatch.setattr("mara_host.command.client.MaraClient", _DummyClient)

    service = ConnectionService(
        ConnectionConfig(
            transport_type=TransportType.SERIAL,
            port="/dev/null",
            handshake_timeout_s=6.5,
            verbose=False,
        )
    )
    monkeypatch.setattr(service, "_create_transport", lambda: object())

    info = await service.connect()
    assert info.firmware_version == "fw"
    assert captured["handshake_timeout_s"] == 6.5

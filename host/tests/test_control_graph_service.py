import pytest

from mara_host.command.client import MaraClient
from mara_host.core.result import ServiceResult
from mara_host.services.control.control_graph_service import ControlGraphService
from mara_host.transport.tcp_transport import AsyncTcpTransport
from tests.fakes.fake_mara_server import FakeMaraTcpServer


class _PolicyFacade:
    def __init__(self, ok: bool = True, decisions: list[dict] | None = None, required_kinds: list[str] | None = None):
        self._ok = ok
        self._decisions = decisions or []
        self._required_kinds = required_kinds or []

    def evaluate_graph_requirements(self, _graph):
        class Report:
            pass

        report = Report()
        report.ok = self._ok
        report.required_kinds = list(self._required_kinds)
        report.decisions = list(self._decisions)
        return report


async def _build_service(fake_server, sensor_policy_provider=None):
    transport = AsyncTcpTransport(fake_server.host, fake_server.port)
    client = MaraClient(transport, verbose=False)
    await client.start()
    return client, ControlGraphService(client, sensor_policy_provider=sensor_policy_provider)


@pytest.fixture
def sample_graph():
    return {
        "schema_version": 1,
        "slots": [
            {
                "id": "imu_pitch_servo",
                "enabled": True,
                "rate_hz": 20,
                "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                "transforms": [
                    {"type": "deadband", "params": {"threshold": 1.0}},
                    {"type": "scale", "params": {"factor": 3.0}},
                    {"type": "delta_gate", "params": {"threshold": 0.75}},
                    {"type": "slew_rate", "params": {"rate": 90.0}},
                ],
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            }
        ],
    }


@pytest.mark.asyncio
async def test_control_graph_upload_and_clear(sample_graph):
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        result = await service.upload(sample_graph)
        assert result.ok
        assert result.data["graph"]["slots"][0]["id"] == "imu_pitch_servo"
        assert result.data["present"] is True
        assert result.data["slot_count"] == 1

        clear_result = await service.clear()
        assert clear_result.ok
        assert clear_result.data["cleared"] is True
        assert service.cached_graph is None
        assert service.cached_policy is None
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_apply_enable_and_status(sample_graph):
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        apply_result = await service.apply(sample_graph)
        assert apply_result.ok
        assert apply_result.data["enabled"] is True
        assert apply_result.data["graph"]["slots"][0]["enabled"] is True

        disable_result = await service.disable()
        assert disable_result.ok
        assert disable_result.data["enabled"] is False
        assert service.cached_graph["slots"][0]["enabled"] is False

        status_result = await service.status()
        assert status_result.ok
        assert status_result.data["present"] is True
        assert status_result.data["schema_version"] == 1
        assert "slots" in status_result.data
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_upload_rejects_invalid_graph():
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        result = await service.upload({"slots": [{"id": "bad"}]})
        assert not result.ok
        assert "source" in result.error or "sink" in result.error
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_apply_fails_when_status_disagrees(sample_graph, monkeypatch):
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        async def fake_status():
            return ServiceResult.success(
                data={
                    "present": False,
                    "enabled": False,
                    "schema_version": 0,
                    "slot_count": 0,
                    "slots": [],
                }
            )

        monkeypatch.setattr(service, "status", fake_status)
        result = await service.apply(sample_graph)
        assert not result.ok
        assert "graph-status disagrees" in result.error
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_upload_includes_non_blocking_policy(sample_graph):
    fake_mara_server = await FakeMaraTcpServer().start()
    facade = _PolicyFacade(
        ok=True,
        required_kinds=["imu"],
        decisions=[
            {
                "name": "imu",
                "kind": "imu",
                "sensor_id": 0,
                "usable": True,
                "blocking": False,
                "reason": "available",
                "fallback": "none",
                "fail_open": False,
            }
        ],
    )
    client, service = await _build_service(fake_mara_server, sensor_policy_provider=lambda: facade)
    try:
        result = await service.upload(sample_graph)
        assert result.ok
        assert result.data["policy"]["ok"] is True
        assert result.data["policy"]["required_kinds"] == ["imu"]
        assert result.data["policy"]["blocking"] == []
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_apply_blocks_when_sensor_policy_blocks(sample_graph):
    fake_mara_server = await FakeMaraTcpServer().start()
    facade = _PolicyFacade(
        ok=False,
        required_kinds=["imu"],
        decisions=[
            {
                "name": "imu",
                "kind": "imu",
                "sensor_id": 0,
                "usable": False,
                "blocking": True,
                "reason": "stale",
                "fallback": "hold_last",
                "fail_open": False,
            }
        ],
    )
    client, service = await _build_service(fake_mara_server, sensor_policy_provider=lambda: facade)
    try:
        result = await service.apply(sample_graph)
        assert not result.ok
        assert result.error == "Control graph blocked by sensor policy"
        assert result.data["policy"]["blocking"][0]["reason"] == "stale"
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_enable_rechecks_policy_for_cached_graph(sample_graph):
    fake_mara_server = await FakeMaraTcpServer().start()
    facade = _PolicyFacade(ok=True, decisions=[])
    client, service = await _build_service(fake_mara_server, sensor_policy_provider=lambda: facade)
    try:
        upload_result = await service.upload(sample_graph)
        assert upload_result.ok

        facade._ok = False
        facade._required_kinds = ["imu"]
        facade._decisions = [
            {
                "name": "imu",
                "kind": "imu",
                "sensor_id": 0,
                "usable": False,
                "blocking": True,
                "reason": "missing",
                "fallback": "hold_last",
                "fail_open": False,
            }
        ]
        result = await service.enable(True)
        assert not result.ok
        assert result.error == "Control graph enable blocked by sensor policy"
        assert result.data["policy"]["blocking"][0]["reason"] == "missing"
    finally:
        await client.stop()
        await fake_mara_server.stop()

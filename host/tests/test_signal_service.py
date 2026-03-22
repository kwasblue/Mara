# tests/test_signal_service.py
"""Tests for SignalService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from mara_host.services.control.signal_service import (
    SignalService,
    Signal,
    SignalKind,
)
from mara_host.core.result import ServiceResult


class TestSignalService:
    """Tests for SignalService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock MaraClient."""
        client = MagicMock()
        client.send_reliable = AsyncMock(return_value=(True, None))
        return client

    @pytest.fixture
    def signal_service(self, mock_client):
        """Create SignalService with mock client."""
        return SignalService(mock_client)

    def test_initial_state(self, signal_service):
        """Test initial state has no signals."""
        assert len(signal_service.signals) == 0

    @pytest.mark.asyncio
    async def test_define_signal_success(self, signal_service, mock_client):
        """Test successful signal definition."""
        result = await signal_service.define(
            signal_id=0,
            name="velocity_ref",
            kind="continuous",
            initial_value=0.0,
        )

        assert result.ok
        assert result.data["signal_id"] == 0
        assert result.data["name"] == "velocity_ref"

        # Check signal is cached
        assert 0 in signal_service.signals
        assert signal_service.signals[0].name == "velocity_ref"

        # Check correct command sent
        mock_client.send_reliable.assert_called_once_with(
            "CMD_CTRL_SIGNAL_DEFINE",
            {
                "signal_id": 0,
                "name": "velocity_ref",
                "signal_kind": "continuous",
                "initial_value": 0.0,
            },
        )

    @pytest.mark.asyncio
    async def test_define_signal_failure(self, signal_service, mock_client):
        """Test signal definition failure."""
        mock_client.send_reliable = AsyncMock(
            return_value=(False, "signal_id_in_use")
        )

        result = await signal_service.define(
            signal_id=0,
            name="test",
        )

        assert not result.ok
        assert "signal_id_in_use" in result.error
        assert 0 not in signal_service.signals

    @pytest.mark.asyncio
    async def test_delete_signal_success(self, signal_service, mock_client):
        """Test successful signal deletion."""
        # First define a signal
        await signal_service.define(0, "test")
        assert 0 in signal_service.signals

        # Delete it
        result = await signal_service.delete(0)

        assert result.ok
        assert 0 not in signal_service.signals

    @pytest.mark.asyncio
    async def test_set_signal_success(self, signal_service, mock_client):
        """Test successful signal set."""
        # Define a signal first
        await signal_service.define(0, "test")

        # Set its value
        result = await signal_service.set(0, 1.5)

        assert result.ok
        assert result.data["signal_id"] == 0
        assert result.data["value"] == 1.5

        # Check cached value is updated
        assert signal_service.signals[0].value == 1.5

    @pytest.mark.asyncio
    async def test_set_signal_updates_cache(self, signal_service, mock_client):
        """Test that set updates cached signal value."""
        await signal_service.define(0, "test", initial_value=0.0)
        assert signal_service.signals[0].value == 0.0

        await signal_service.set(0, 3.14)
        assert signal_service.signals[0].value == 3.14

    @pytest.mark.asyncio
    async def test_list_signals(self, signal_service, mock_client):
        """Test list signals."""
        await signal_service.define(0, "sig0")
        await signal_service.define(1, "sig1")

        result = await signal_service.list()

        assert result.ok
        assert 0 in result.data["signals"]
        assert 1 in result.data["signals"]

    @pytest.mark.asyncio
    async def test_clear_signals(self, signal_service, mock_client):
        """Test clear all signals."""
        await signal_service.define(0, "sig0")
        await signal_service.define(1, "sig1")
        assert len(signal_service.signals) == 2

        result = await signal_service.clear()

        assert result.ok
        assert len(signal_service.signals) == 0

    def test_get_cached(self, signal_service):
        """Test get_cached returns cached signal."""
        # No signal cached
        assert signal_service.get_cached(0) is None

    @pytest.mark.asyncio
    async def test_get_cached_after_define(self, signal_service, mock_client):
        """Test get_cached returns signal after define."""
        await signal_service.define(0, "test", kind="continuous", initial_value=1.0)

        cached = signal_service.get_cached(0)
        assert cached is not None
        assert cached.name == "test"
        assert cached.kind == SignalKind.CONTINUOUS
        assert cached.value == 1.0

    @pytest.mark.asyncio
    async def test_signals_property_returns_copy(self, signal_service, mock_client):
        """Test signals property returns a copy."""
        await signal_service.define(0, "test")

        signals1 = signal_service.signals
        signals2 = signal_service.signals

        # Should be different dict instances
        assert signals1 is not signals2


class TestSignalDataclasses:
    """Tests for Signal and SignalKind."""

    def test_signal_creation(self):
        """Test Signal dataclass."""
        sig = Signal(
            signal_id=1,
            name="test_signal",
            kind=SignalKind.CONTINUOUS,
            value=0.5,
        )

        assert sig.signal_id == 1
        assert sig.name == "test_signal"
        assert sig.kind == SignalKind.CONTINUOUS
        assert sig.value == 0.5

    def test_signal_defaults(self):
        """Test Signal default values."""
        sig = Signal(signal_id=0, name="test")

        assert sig.kind == SignalKind.CONTINUOUS
        assert sig.value == 0.0

    def test_signal_kind_values(self):
        """Test SignalKind enum values."""
        assert SignalKind.CONTINUOUS.value == "continuous"
        assert SignalKind.DISCRETE.value == "discrete"
        assert SignalKind.EVENT.value == "event"

    def test_signal_kind_from_string(self):
        """Test creating SignalKind from string."""
        assert SignalKind("continuous") == SignalKind.CONTINUOUS
        assert SignalKind("discrete") == SignalKind.DISCRETE
        assert SignalKind("event") == SignalKind.EVENT

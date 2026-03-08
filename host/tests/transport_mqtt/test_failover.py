# tests/transport_mqtt/test_failover.py
"""Tests for broker failover logic."""

from unittest.mock import AsyncMock, patch
import pytest

from mara_host.transport.mqtt.broker_failover import (
    BrokerFailover,
    BrokerConfig,
    BrokerState,
)


class TestBrokerConfig:
    """Tests for BrokerConfig."""

    def test_defaults(self):
        """Test default configuration values."""
        config = BrokerConfig(host="localhost")

        assert config.host == "localhost"
        assert config.port == 1883
        assert config.username is None
        assert config.password is None
        assert config.name == "broker"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = BrokerConfig(
            host="mqtt.example.com",
            port=8883,
            username="user",
            password="pass",
            name="primary",
        )

        assert config.host == "mqtt.example.com"
        assert config.port == 8883
        assert config.username == "user"
        assert config.password == "pass"
        assert config.name == "primary"


class TestBrokerFailover:
    """Tests for BrokerFailover class."""

    def test_init_primary_only(self):
        """Test initialization with primary broker only."""
        primary = BrokerConfig(host="primary.local", name="primary")
        failover = BrokerFailover(primary=primary)

        assert failover.current_broker == primary
        assert failover.state == BrokerState.DISCONNECTED
        assert not failover.is_using_fallback
        assert failover.retry_count == 0

    def test_init_with_fallback(self):
        """Test initialization with fallback broker."""
        primary = BrokerConfig(host="primary.local", name="primary")
        fallback = BrokerConfig(host="fallback.local", name="fallback")
        failover = BrokerFailover(primary=primary, fallback=fallback)

        assert failover.current_broker == primary
        assert failover._fallback == fallback

    def test_notify_connected(self):
        """Test connection success notification."""
        primary = BrokerConfig(host="primary.local")
        failover = BrokerFailover(primary=primary)

        failover._retry_count = 5
        failover.notify_connected()

        assert failover.state == BrokerState.CONNECTED
        assert failover.retry_count == 0

    def test_notify_disconnected(self):
        """Test disconnection notification."""
        primary = BrokerConfig(host="primary.local")
        failover = BrokerFailover(primary=primary)

        failover.notify_disconnected()
        assert failover.state == BrokerState.DISCONNECTED

    def test_notify_connection_failed(self):
        """Test connection failure notification."""
        primary = BrokerConfig(host="primary.local")
        failover = BrokerFailover(primary=primary)

        failover.notify_connection_failed()
        assert failover.state == BrokerState.FAILING
        assert failover.retry_count == 1

        failover.notify_connection_failed()
        assert failover.retry_count == 2

    @pytest.mark.asyncio
    async def test_get_next_broker_no_failover(self):
        """Test getting next broker without failover configured."""
        primary = BrokerConfig(host="primary.local")
        failover = BrokerFailover(primary=primary, max_retries=3)

        # First attempt - no delay
        broker, delay = await failover.get_next_broker()
        assert broker == primary
        assert delay == 0.0

        # Simulate failures
        failover.notify_connection_failed()
        broker, delay = await failover.get_next_broker()
        assert broker == primary
        assert delay > 0  # Should have backoff

    @pytest.mark.asyncio
    async def test_get_next_broker_switches_to_fallback(self):
        """Test automatic switch to fallback after max retries."""
        primary = BrokerConfig(host="primary.local", name="primary")
        fallback = BrokerConfig(host="fallback.local", name="fallback")

        callback_data = []
        failover = BrokerFailover(
            primary=primary,
            fallback=fallback,
            max_retries=3,
            on_broker_change=lambda b: callback_data.append(b),
        )

        # Simulate max_retries failures
        for _ in range(3):
            failover.notify_connection_failed()

        broker, delay = await failover.get_next_broker()

        assert broker == fallback
        assert failover.is_using_fallback
        assert failover.retry_count == 0
        assert len(callback_data) == 1
        assert callback_data[0] == fallback

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        primary = BrokerConfig(host="primary.local")
        failover = BrokerFailover(
            primary=primary,
            base_delay_s=1.0,
            max_delay_s=30.0,
        )

        delays = []
        for i in range(6):
            failover.notify_connection_failed()
            _, delay = await failover.get_next_broker()
            delays.append(delay)

        # Should be exponential: 1, 2, 4, 8, 16, 30 (capped)
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
        assert delays[3] == 8.0
        assert delays[4] == 16.0
        assert delays[5] == 30.0  # Capped at max

    @pytest.mark.asyncio
    async def test_check_primary_available(self):
        """Test primary availability check."""
        primary = BrokerConfig(host="primary.local")
        fallback = BrokerConfig(host="fallback.local")
        failover = BrokerFailover(primary=primary, fallback=fallback)

        # Not using fallback - should return True
        result = await failover.check_primary_available()
        assert result is True

        # Switch to fallback
        failover._using_fallback = True
        failover._current_broker = fallback

        # Mock the connection check
        with patch("mara_host.transport.mqtt.broker_failover.aiomqtt.Client") as mock_client:
            # Successful connection
            mock_client.return_value.__aenter__ = AsyncMock()
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await failover.check_primary_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_switch_to_primary(self):
        """Test switching back to primary broker."""
        primary = BrokerConfig(host="primary.local", name="primary")
        fallback = BrokerConfig(host="fallback.local", name="fallback")

        callback_data = []
        failover = BrokerFailover(
            primary=primary,
            fallback=fallback,
            on_broker_change=lambda b: callback_data.append(b),
        )

        # Simulate being on fallback
        failover._using_fallback = True
        failover._current_broker = fallback

        # Mock successful primary check
        with patch.object(failover, 'check_primary_available', return_value=True):
            result = await failover.switch_to_primary()

        assert result is True
        assert failover.current_broker == primary
        assert not failover.is_using_fallback
        assert len(callback_data) == 1

    @pytest.mark.asyncio
    async def test_switch_to_primary_fails(self):
        """Test switch to primary when primary is unavailable."""
        primary = BrokerConfig(host="primary.local")
        fallback = BrokerConfig(host="fallback.local")
        failover = BrokerFailover(primary=primary, fallback=fallback)

        failover._using_fallback = True
        failover._current_broker = fallback

        with patch.object(failover, 'check_primary_available', return_value=False):
            result = await failover.switch_to_primary()

        assert result is False
        assert failover.is_using_fallback
        assert failover.current_broker == fallback

    def test_state_change_callback(self):
        """Test state change callback is called."""
        primary = BrokerConfig(host="primary.local")

        states = []
        failover = BrokerFailover(
            primary=primary,
            on_state_change=lambda s: states.append(s),
        )

        failover.notify_connected()
        failover.notify_disconnected()
        failover.notify_connection_failed()

        assert states == [
            BrokerState.CONNECTED,
            BrokerState.DISCONNECTED,
            BrokerState.FAILING,
        ]

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop lifecycle."""
        primary = BrokerConfig(host="primary.local")
        failover = BrokerFailover(primary=primary)

        await failover.start()
        assert failover._running
        assert failover._monitor_task is not None

        await failover.stop()
        assert not failover._running
        assert failover._monitor_task is None

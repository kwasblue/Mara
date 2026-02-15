# tests/mqtt/test_transport.py
"""Tests for MQTTTransport."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from robot_host.core import protocol
from robot_host.mqtt.transport import MQTTTransport
from robot_host.mqtt.models import get_cmd_topic, get_ack_topic, get_telemetry_topic


class TestMQTTTransport:
    """Tests for MQTTTransport class."""

    def test_init(self):
        """Test transport initialization."""
        transport = MQTTTransport(
            broker_host="localhost",
            broker_port=1883,
            node_id="node0",
        )

        assert transport.node_id == "node0"
        assert not transport.is_connected
        assert transport._cmd_topic == "mara/node0/cmd"
        assert transport._ack_topic == "mara/node0/ack"
        assert transport._telemetry_topic == "mara/node0/telemetry"

    def test_init_with_auth(self):
        """Test transport initialization with authentication."""
        transport = MQTTTransport(
            broker_host="broker.example.com",
            broker_port=8883,
            node_id="robot1",
            username="user",
            password="pass",
        )

        assert transport._config.broker_host == "broker.example.com"
        assert transport._config.broker_port == 8883
        assert transport._config.username == "user"
        assert transport._config.password == "pass"

    def test_set_frame_handler(self):
        """Test setting frame handler."""
        transport = MQTTTransport(broker_host="localhost", node_id="node0")

        frames_received = []
        transport.set_frame_handler(lambda f: frames_received.append(f))

        # Simulate receiving a frame
        test_frame = protocol.encode(0x01, b"test")
        transport._rx_buffer.extend(test_frame)
        protocol.extract_frames(transport._rx_buffer, transport._frame_handler)

        assert len(frames_received) == 1
        assert frames_received[0][0] == 0x01  # msg_type
        assert frames_received[0][1:] == b"test"  # payload

    @pytest.mark.asyncio
    async def test_send_bytes_not_connected(self):
        """Test send_bytes raises timeout when not connected."""
        transport = MQTTTransport(broker_host="localhost", node_id="node0")

        with pytest.raises(TimeoutError):
            await transport.send_bytes(b"test")

    @pytest.mark.asyncio
    async def test_send_frame(self):
        """Test send_frame encodes and sends properly."""
        transport = MQTTTransport(broker_host="localhost", node_id="node0")

        # Mock the client and set connected state
        mock_client = AsyncMock()
        transport._client = mock_client
        transport._connected_evt.set()

        await transport.send_frame(0x50, b'{"type":"CMD_TEST"}')

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "mara/node0/cmd"
        # Verify it's a valid frame
        data = call_args[0][1]
        assert data[0] == protocol.HEADER

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop lifecycle."""
        transport = MQTTTransport(broker_host="localhost", node_id="node0")

        # Start the transport (don't wait for connection)
        transport._running = True
        transport._task = asyncio.create_task(asyncio.sleep(10))  # Dummy task

        assert transport._running
        assert transport._task is not None

        await transport.stop()
        assert not transport._running
        assert transport._task is None


class TestTopicHelpers:
    """Tests for topic helper functions."""

    def test_get_cmd_topic(self):
        assert get_cmd_topic("node0") == "mara/node0/cmd"
        assert get_cmd_topic("robot_1") == "mara/robot_1/cmd"

    def test_get_ack_topic(self):
        assert get_ack_topic("node0") == "mara/node0/ack"

    def test_get_telemetry_topic(self):
        assert get_telemetry_topic("node0") == "mara/node0/telemetry"

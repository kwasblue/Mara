# tests/test_client_safety.py

import pytest
import asyncio
import time

from mara_host.command.coms.connection_monitor import ConnectionMonitor
from mara_host.command.coms.reliable_commander import ReliableCommander


# -----------------------------------------------------------------------------
# Connection Monitor Tests
# -----------------------------------------------------------------------------

class TestConnectionMonitor:
    
    def test_initial_state_is_disconnected(self):
        monitor = ConnectionMonitor(timeout_s=1.0)
        assert monitor.connected is False
        assert monitor.time_since_last_message is None
    
    def test_message_received_sets_connected(self):
        monitor = ConnectionMonitor(timeout_s=1.0)
        monitor.on_message_received()
        assert monitor.connected is True
    
    def test_timeout_triggers_disconnect(self):
        disconnected = []
        
        monitor = ConnectionMonitor(timeout_s=0.1, on_disconnect=lambda: disconnected.append(True))
        monitor.on_message_received()
        assert monitor.connected is True
        
        time.sleep(0.15)
        monitor.check()
        
        assert monitor.connected is False
        assert len(disconnected) == 1
    
    def test_message_prevents_timeout(self):
        disconnected = []
        
        monitor = ConnectionMonitor(timeout_s=0.1, on_disconnect=lambda: disconnected.append(True))
        monitor.on_message_received()
        
        time.sleep(0.05)
        monitor.on_message_received()
        
        time.sleep(0.05)
        monitor.check()
        
        assert monitor.connected is True
        assert len(disconnected) == 0
    
    def test_reconnect_callback_fires(self):
        reconnected = []
        
        monitor = ConnectionMonitor(
            timeout_s=0.05,
            on_disconnect=lambda: None,
            on_reconnect=lambda: reconnected.append(True),
        )
        
        monitor.on_message_received()
        assert len(reconnected) == 1
        
        time.sleep(0.1)
        monitor.check()
        assert monitor.connected is False
        
        monitor.on_message_received()
        assert len(reconnected) == 2
    
    def test_reset_clears_state(self):
        monitor = ConnectionMonitor(timeout_s=1.0)
        monitor.on_message_received()
        assert monitor.connected is True
        
        monitor.reset()
        assert monitor.connected is False
        assert monitor.time_since_last_message is None


# -----------------------------------------------------------------------------
# Reliable Commander Tests
# Fixed to match actual implementation signature
# -----------------------------------------------------------------------------

class TestReliableCommander:
    
    @pytest.fixture
    def mock_send(self):
        """Mock that matches actual send_func signature: (cmd_type, payload, callback) -> seq"""
        seq = [0]
        async def send_func(cmd_type, payload, callback=None):
            seq[0] += 1
            return seq[0]
        return send_func
    
    @pytest.mark.asyncio
    async def test_send_fire_and_forget_not_tracked(self, mock_send):
        commander = ReliableCommander(send_func=mock_send, timeout_s=1.0, max_retries=3)
        
        seq = await commander.send_fire_and_forget("HEARTBEAT", {})
        
        assert seq == 1
        assert commander.pending_count() == 0
    
    def test_stats_structure(self, mock_send):
        commander = ReliableCommander(send_func=mock_send, timeout_s=1.0, max_retries=3)
        
        stats = commander.stats()
        
        assert "commands_sent" in stats
        assert "acks_received" in stats
        assert "timeouts" in stats
        assert "retries" in stats
        assert "pending" in stats
    
    @pytest.mark.asyncio
    async def test_send_and_ack_flow(self, mock_send):
        commander = ReliableCommander(send_func=mock_send, timeout_s=1.0, max_retries=3)
        # Must start update loop for ACK processing (queue-based since Phase 5)
        await commander.start_update_loop(interval_s=0.01)

        try:
            # Send command in background
            task = asyncio.create_task(commander.send("TEST", {}, wait_for_ack=True))

            # Give it time to register
            await asyncio.sleep(0.02)

            # Should have 1 pending
            assert commander.pending_count() == 1

            # Ack it (queued for async processing)
            commander.on_ack(1, ok=True, error=None)

            # Give time for ACK to be processed from queue
            await asyncio.sleep(0.05)

            # Should complete
            ok, err = await asyncio.wait_for(task, timeout=1.0)
            assert ok is True
            assert err is None
            assert commander.pending_count() == 0
        finally:
            await commander.stop_update_loop()
    
    @pytest.mark.asyncio
    async def test_ack_with_error(self, mock_send):
        commander = ReliableCommander(send_func=mock_send, timeout_s=1.0, max_retries=3)
        # Must start update loop for ACK processing (queue-based since Phase 5)
        await commander.start_update_loop(interval_s=0.01)

        try:
            task = asyncio.create_task(commander.send("TEST", {}, wait_for_ack=True))
            await asyncio.sleep(0.02)

            commander.on_ack(1, ok=False, error="not_armed")

            # Give time for ACK to be processed from queue
            await asyncio.sleep(0.05)

            ok, err = await asyncio.wait_for(task, timeout=1.0)
            assert ok is False
            assert err == "not_armed"
        finally:
            await commander.stop_update_loop()
    
    @pytest.mark.asyncio
    async def test_clear_pending_resolves_all(self, mock_send):
        commander = ReliableCommander(send_func=mock_send, timeout_s=10.0, max_retries=3)

        task1 = asyncio.create_task(commander.send("TEST1", {}, wait_for_ack=True))
        task2 = asyncio.create_task(commander.send("TEST2", {}, wait_for_ack=True))
        await asyncio.sleep(0.02)

        assert commander.pending_count() == 2

        # Use async clear_pending (not sync version)
        await commander.clear_pending()

        ok1, err1 = await asyncio.wait_for(task1, timeout=1.0)
        ok2, err2 = await asyncio.wait_for(task2, timeout=1.0)

        assert ok1 is False
        assert err1 == "CLEARED"
        assert ok2 is False
        assert err2 == "CLEARED"
    
    @pytest.mark.asyncio
    async def test_timeout_then_fail(self, mock_send):
        commander = ReliableCommander(send_func=mock_send, timeout_s=0.03, max_retries=1)
        await commander.start_update_loop(interval_s=0.01)
        
        task = asyncio.create_task(commander.send("TEST", {}, wait_for_ack=True))
        
        # Wait for timeout + retries to exhaust
        await asyncio.sleep(0.2)
        
        ok, err = await task
        assert ok is False
        assert err == "TIMEOUT"
        
        await commander.stop_update_loop()


# -----------------------------------------------------------------------------
# Integration: Disconnect clears pending
# -----------------------------------------------------------------------------

class TestDisconnectClearsPending:

    @pytest.mark.asyncio
    async def test_disconnect_clears_commander(self):
        seq = [0]
        async def send_func(cmd_type, payload, callback=None):
            seq[0] += 1
            return seq[0]

        cleared = []

        def on_disconnect():
            # Use sync version since this callback is called from sync context
            commander.clear_pending_sync()
            cleared.append(True)

        monitor = ConnectionMonitor(timeout_s=0.05, on_disconnect=on_disconnect)
        commander = ReliableCommander(send_func=send_func, timeout_s=10.0, max_retries=3)

        monitor.on_message_received()

        task = asyncio.create_task(commander.send("TEST", {}, wait_for_ack=True))
        await asyncio.sleep(0.02)
        assert commander.pending_count() == 1

        # Disconnect
        await asyncio.sleep(0.1)
        monitor.check()

        assert len(cleared) == 1

        ok, err = await asyncio.wait_for(task, timeout=1.0)
        assert ok is False
        assert err == "CLEARED"
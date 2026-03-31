# MARA Systemic Fixes Plan - Phase 2

This plan addresses the 24 systemic issues identified in the architectural review.

---

## Phase 1: Critical Error Handling (High Priority)

### 1.1 Replace Bare `except:` Clauses in CLI
**Files:** `host/mara_host/cli/commands/logs/*.py`
**Issue:** Bare `except:` catches KeyboardInterrupt/SystemExit
**Fix:** Replace with `except Exception:` and add logging

```python
# Before
try:
    ...
except:
    pass

# After
except Exception as e:
    logger.warning("Operation failed: %s", e)
```

### 1.2 Add Logging to Suppressed Callback Exceptions
**File:** `host/mara_host/command/coms/connection_monitor.py:174,185,196`
**Issue:** Silent `except Exception: pass`
**Fix:** Log warnings for callback failures

```python
# Before
try:
    self.on_state_change(event)
except Exception:
    pass

# After
try:
    self.on_state_change(event)
except Exception as e:
    _log.warning("State change callback failed: %s", e)
```

### 1.3 Improve Version Response Error Handling
**File:** `host/mara_host/command/client.py:330-333`
**Issue:** Parse errors silently converted to empty dict
**Fix:** Log warning and include parse error context

---

## Phase 2: Resource Management (High Priority)

### 2.1 Fix Heartbeat Task Leak on Startup Failure
**File:** `host/mara_host/command/client.py`
**Issue:** Heartbeat task not cancelled if handshake fails
**Fix:** Move task creation after handshake, or add cleanup in exception handler

```python
async def start(self) -> None:
    # ... transport start ...

    if self._require_version_match:
        try:
            await self._perform_handshake()
        except Exception:
            self._running = False
            await self._stop_transport()
            raise

    # Only create tasks AFTER successful handshake
    await self.commander.start_update_loop(interval_s=0.05)
    await self.connection.start_monitoring(interval_s=0.1)
    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
```

### 2.2 Add Timeout to ThreadPoolExecutor Shutdown
**File:** `host/mara_host/transport/stream_transport.py:84-86`
**Issue:** `shutdown(wait=True)` can hang indefinitely
**Fix:** Use `shutdown(wait=True, cancel_futures=True)` or add timeout wrapper

```python
async def stop(self) -> None:
    self._stop = True
    if self._write_executor is not None:
        # Python 3.9+: cancel_futures=True prevents hang
        self._write_executor.shutdown(wait=False, cancel_futures=True)
        self._write_executor = None
```

### 2.3 Handle Daemon Thread Graceful Shutdown
**File:** `host/mara_host/transport/stream_transport.py:71`
**Issue:** Daemon thread abruptly terminated
**Fix:** Add stop flag check and join with timeout

```python
def stop(self) -> None:
    self._stop = True
    if self._thread is not None:
        self._thread.join(timeout=1.0)  # Wait up to 1s for clean exit
        self._thread = None
```

### 2.4 Fix Cached Event Loop Validation
**File:** `host/mara_host/transport/tcp_transport.py:125-128`
**Issue:** Cached loop reference can become invalid
**Fix:** Always validate loop is running, not just not closed

```python
loop = self._cached_loop
if loop is None or loop.is_closed() or not loop.is_running():
    try:
        loop = asyncio.get_running_loop()
        self._cached_loop = loop
    except RuntimeError:
        return  # No running loop, skip callback
```

---

## Phase 3: Concurrency Fixes (Medium Priority)

### 3.1 Fix ConnectionMonitor State Race
**File:** `host/mara_host/command/coms/connection_monitor.py:210-213`
**Issue:** Direct state mutation without lock
**Fix:** Always use lock for state changes

```python
def on_message_received(self) -> None:
    self._last_message_ns = time.monotonic_ns()

    with self._lock:
        if self._state == ConnectionState.DISCONNECTED:
            # Must transition through CONNECTING
            self._state = ConnectionState.CONNECTING
            self._transition_to_unlocked(ConnectionState.CONNECTED, "unexpected_message")
        elif self._state == ConnectionState.CONNECTING:
            self._transition_to_unlocked(ConnectionState.CONNECTED, "message_received")
```

### 3.2 Add ACK Queue Size Limit with Warning
**File:** `host/mara_host/command/coms/reliable_commander.py`
**Issue:** Unbounded queue or silent drops
**Fix:** Use bounded queue with explicit size, log warning on near-full

```python
# In __init__
self._ack_queue: asyncio.Queue[...] = asyncio.Queue(maxsize=1000)

def on_ack(self, seq: int, ok: bool, error: Optional[str] = None) -> None:
    ack_ns = time.monotonic_ns()
    try:
        self._ack_queue.put_nowait((seq, ok, error, ack_ns))
    except asyncio.QueueFull:
        _log.error("ACK queue full! Dropping ACK for seq=%d", seq)
        self._emit("cmd.ack_dropped", seq=seq, reason="queue_full")
```

### 3.3 Add Re-entrancy Protection to Motion Service
**File:** `host/mara_host/services/control/motion_service.py`
**Issue:** Concurrent calls may interleave
**Fix:** Add asyncio.Lock for command serialization

```python
def __init__(self, client):
    super().__init__(client)
    self._command_lock = asyncio.Lock()

async def set_velocity(self, vx: float, omega: float) -> ServiceResult:
    async with self._command_lock:
        return await self._send_velocity(vx, omega)
```

---

## Phase 4: Memory/Performance Fixes (Medium Priority)

### 4.1 Replace List with Deque for Latency Tracking
**File:** `host/mara_host/command/coms/reliable_commander.py:157-180`
**Issue:** `list.pop(0)` is O(n)
**Fix:** Use `collections.deque(maxlen=N)`

```python
from collections import deque

# In __init__
self._latencies_ms: deque[float] = deque(maxlen=1000)

def _record_latency(self, latency_ms: float) -> None:
    self._latencies_ms.append(latency_ms)  # O(1), auto-evicts old
```

### 4.2 Replace List with Deque for Event History
**File:** `host/mara_host/command/coms/connection_monitor.py:157-159`
**Issue:** Same O(n) problem
**Fix:** Same deque solution

```python
self._event_history: deque[ConnectionEvent] = deque(maxlen=100)
```

### 4.3 Add Service Cache Invalidation
**File:** `host/mara_host/services/control/control_graph_service.py`
**Issue:** Caches never invalidated
**Fix:** Add invalidation method, subscribe to relevant events

```python
def __init__(self, client, ...):
    super().__init__(client)
    self._cached_graph_model = None
    self._cached_policy = None
    # Subscribe to graph change events from MCU
    self._client.bus.subscribe("ctrl_graph.changed", self._on_graph_changed)

def _on_graph_changed(self, data: dict) -> None:
    self._cached_graph_model = None
    self._cached_policy = None

def invalidate_cache(self) -> None:
    """Manually invalidate caches."""
    self._cached_graph_model = None
    self._cached_policy = None
```

---

## Phase 5: Protocol Robustness (Medium Priority)

### 5.1 Add Message Type Validation
**File:** `host/mara_host/core/protocol.py`
**Issue:** Invalid msg_type accepted
**Fix:** Validate msg_type is in known set

```python
_VALID_MSG_TYPES = {
    MSG_HEARTBEAT, MSG_PING, MSG_PONG, MSG_VERSION_REQUEST,
    MSG_VERSION_RESPONSE, MSG_WHOAMI, MSG_TELEMETRY_BIN,
    MSG_CMD_JSON, MSG_CMD_BIN, MSG_ACK_BIN,
}

def extract_frames(buffer: bytearray, on_frame: Callable[[bytes], None]) -> None:
    # ... existing code ...

    msg_type = body[0]
    if msg_type not in _VALID_MSG_TYPES:
        # Unknown message type, skip and resync
        i += 1
        continue
```

### 5.2 Add Telemetry Section Size Limit
**File:** `host/mara_host/telemetry/binary_parser.py`
**Issue:** No upper bound on section_len
**Fix:** Add sanity check

```python
MAX_SECTION_SIZE = 4096  # Reasonable max for any telemetry section

section_id, section_len = _SECTION_HDR.unpack_from(payload, off)
if section_len > MAX_SECTION_SIZE:
    pkt.raw["error"] = f"section_too_large:{section_len}"
    return pkt
```

### 5.3 Improve CRC Resync Strategy
**File:** `host/mara_host/core/protocol.py:189-191`
**Issue:** Only advances 1 byte on CRC error
**Fix:** Skip entire bad frame length to avoid repeated false matches

```python
if expected_crc == recv_crc:
    on_frame(bytes(body))
    i += frame_total
else:
    # Skip past this header, but also skip obvious garbage
    # Advance by frame_total to avoid re-parsing same corrupt data
    _log.debug("CRC mismatch, skipping %d bytes", frame_total)
    i += frame_total
```

---

## Phase 6: Logging Improvements (Medium Priority)

### 6.1 Add Frame Handler Error Logging
**File:** `host/mara_host/transport/stream_transport.py:103-114`
**Issue:** Frame handler crashes not logged
**Fix:** Wrap callback in try/except

```python
def _reader_loop(self) -> None:
    while not self._stop:
        try:
            data = self._read_raw(256)
            if data:
                self._rx_buffer.extend(data)
                protocol.extract_frames(self._rx_buffer, self._safe_handle_body)
            else:
                time.sleep(0.01)
        except Exception as e:
            _log.warning("Reader loop error: %s", e)
            time.sleep(0.5)

def _safe_handle_body(self, body: bytes) -> None:
    try:
        self._handle_body(body)
    except Exception as e:
        _log.error("Frame handler error: %s", e, exc_info=True)
```

### 6.2 Elevate TCP Drain Timeout to Warning
**File:** `host/mara_host/transport/tcp_transport.py:93-97`
**Issue:** Debug-level hides important info
**Fix:** Use warning level

```python
except asyncio.TimeoutError:
    _log.warning("Write drain timeout - data may be buffered")
    return False
```

### 6.3 Add Service Error Logging
**File:** `host/mara_host/services/control/service_base.py`
**Issue:** Service failures not logged
**Fix:** Add logging in base class

```python
async def _send_command(self, cmd_type: str, payload: dict) -> ServiceResult:
    ok, error = await self._client.send_reliable(cmd_type, payload)
    if not ok:
        _log.warning("Service command %s failed: %s", cmd_type, error)
    return ServiceResult(success=ok, error=error)
```

---

## Phase 7: Service Cleanup (Medium Priority)

### 7.1 Add Service Cleanup Method
**File:** `host/mara_host/services/control/service_base.py`
**Issue:** No cleanup on service destruction
**Fix:** Add close() method pattern

```python
class ConfigurableService:
    def __init__(self, client):
        self._client = client
        self._subscriptions: list[tuple[str, Callable]] = []

    def _subscribe(self, topic: str, handler: Callable) -> None:
        """Track subscription for cleanup."""
        self._client.bus.subscribe(topic, handler)
        self._subscriptions.append((topic, handler))

    def close(self) -> None:
        """Clean up subscriptions."""
        for topic, handler in self._subscriptions:
            self._client.bus.unsubscribe(topic, handler)
        self._subscriptions.clear()
```

### 7.2 Update Robot.disconnect() to Close Services
**File:** `host/mara_host/robot.py`
**Issue:** Services not closed on disconnect
**Fix:** Call close() on services that have it

```python
async def disconnect(self, validate_cleanup: bool = False) -> None:
    # Close services with cleanup methods
    for service in [
        self._control_graph_service,
        self._mcu_diagnostics_service,
        self._motion,
        self._motor_service,
        self._servo_service,
    ]:
        if service is not None and hasattr(service, 'close'):
            service.close()

    # ... existing cleanup ...
```

---

## Phase 8: Additional Improvements (Low Priority)

### 8.1 Add TCP Reconnect Exponential Backoff
**File:** `host/mara_host/transport/tcp_transport.py`
**Issue:** Fixed reconnect delay floods network
**Fix:** Add exponential backoff

```python
def __init__(self, ...):
    self._reconnect_delay = reconnect_delay
    self._current_delay = reconnect_delay
    self._max_delay = 30.0

async def _reconnect(self) -> None:
    await asyncio.sleep(self._current_delay)
    # Exponential backoff with cap
    self._current_delay = min(self._current_delay * 2, self._max_delay)
    # Reset on successful connect

def _on_connected(self) -> None:
    self._current_delay = self._reconnect_delay  # Reset backoff
```

### 8.2 Add Binary Encoder Value Bounds Validation
**File:** `host/mara_host/command/json_to_binary.py`
**Issue:** No physics bounds checking
**Fix:** Add configurable bounds per command

```python
_VALUE_BOUNDS = {
    "vx": (-10.0, 10.0),      # m/s
    "omega": (-10.0, 10.0),   # rad/s
    "angle": (-360.0, 360.0), # degrees
}

def _validate_bounds(value: float, name: str) -> float:
    bounds = _VALUE_BOUNDS.get(name)
    if bounds and not (bounds[0] <= value <= bounds[1]):
        raise ValueError(f"{name}={value} outside bounds {bounds}")
    return value
```

---

## Implementation Order

| Phase | Priority | Estimated Effort | Dependencies |
|-------|----------|------------------|--------------|
| 1. Error Handling | High | Low | None |
| 2. Resource Management | High | Medium | None |
| 3. Concurrency | Medium | Medium | None |
| 4. Memory/Performance | Medium | Low | None |
| 5. Protocol | Medium | Low | None |
| 6. Logging | Medium | Low | None |
| 7. Service Cleanup | Medium | Medium | Phase 4.3 |
| 8. Additional | Low | Low | None |

**Recommended order:** 1 → 2 → 4 → 3 → 5 → 6 → 7 → 8

---

## Testing Checklist

- [ ] Module detach/attach cycle doesn't leak subscriptions
- [ ] Disconnect during handshake doesn't leave orphan tasks
- [ ] High-frequency commands (50+ Hz) don't degrade performance
- [ ] WiFi reconnection doesn't flood network
- [ ] Malformed telemetry packets don't crash parser
- [ ] CRC errors resync correctly
- [ ] Service caches invalidate on MCU changes
- [ ] All exceptions are logged (no silent failures)

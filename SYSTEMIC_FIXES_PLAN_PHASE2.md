# MARA Systemic Fixes Plan - Phase 2

This plan addresses the 31 additional systemic issues identified in the deep dive review.

---

## Phase 9: Async Safety (High Priority)

### 9.1 Fix deprecated `asyncio.get_event_loop()` usage
**Files:** `reliable_commander.py:259`, `client.py:630`
**Issue:** Deprecated in Python 3.10+, fails in 3.12+
**Fix:** Replace with `asyncio.get_running_loop()`

```python
# Before
loop = asyncio.get_event_loop()

# After
loop = asyncio.get_running_loop()
```

### 9.2 Add warning when async handlers called via sync publish()
**File:** `core/event_bus.py:79-85`
**Issue:** Async handlers silently don't execute when called via `publish()`
**Fix:** Add warning log when async handler is closed

```python
if h in async_handlers and asyncio.iscoroutine(result):
    result.close()
    _log.warning(
        "Async handler on '%s' called via publish(). "
        "Use publish_async() for async handlers. Handler: %s",
        topic, h.__name__ if hasattr(h, '__name__') else repr(h)
    )
```

---

## Phase 10: Resource Limits (High Priority)

### 10.1 Add pending command limit
**File:** `reliable_commander.py`
**Issue:** `_pending` dict can grow to 65536 entries
**Fix:** Add max pending limit and reject new commands when at limit

```python
MAX_PENDING_COMMANDS = 256  # Class constant

async def send(self, cmd_type: str, ...):
    if len(self._pending) >= self.MAX_PENDING_COMMANDS:
        self._emit("cmd.rejected", reason="too_many_pending", count=len(self._pending))
        return False, "TOO_MANY_PENDING"
    # ... rest of send logic
```

### 10.2 Prevent service subscription leaks
**File:** `core/event_bus.py`
**Issue:** Subscriptions can leak if service recreated without close()
**Fix:** Add subscription counting and warning on high count

```python
def subscribe(self, topic: str, handler: Handler) -> None:
    self._subs[topic].append(handler)
    # Warn on suspicious subscription counts
    if len(self._subs[topic]) > 10:
        logger.warning(
            "High subscription count on '%s': %d handlers (possible leak?)",
            topic, len(self._subs[topic])
        )
```

---

## Phase 11: State Consistency (High Priority)

### 11.1 Add lock to ControlGraphService cache
**File:** `control_graph_service.py`
**Issue:** Cache accessed without locks from multiple async contexts
**Fix:** Add asyncio.Lock for cache operations

```python
def __init__(self, ...):
    # ...
    self._cache_lock = asyncio.Lock()

async def _get_cached_graph(self) -> ControlGraphConfig | None:
    async with self._cache_lock:
        return self._cached_graph_model

async def _set_cached_graph(self, model: ControlGraphConfig | None) -> None:
    async with self._cache_lock:
        self._cached_graph_model = model
```

### 11.2 Fix handshake cache race condition
**File:** `client.py:262-267`
**Issue:** `_cached_identity` accessed without synchronization
**Fix:** Use asyncio.Lock or atomic check-and-set

```python
# In __init__:
self._handshake_lock = asyncio.Lock()

async def _perform_handshake(self) -> None:
    async with self._handshake_lock:
        if self._cached_identity is not None:
            if not self._handshake_future.done():
                self._handshake_future.set_result(self._cached_identity)
            self._cached_identity = None
```

---

## Phase 12: Error Recovery (Medium Priority)

### 12.1 Add telemetry parse error logging
**File:** `binary_parser.py`
**Issue:** Parse errors silently return partial data
**Fix:** Add logging for parse errors

```python
import logging
_log = logging.getLogger(__name__)

def parse_telemetry_bin(payload: bytes) -> TelemetryPacket:
    if len(payload) < _PKT_HDR.size:
        _log.warning("Telemetry packet too short: %d bytes", len(payload))
        return _make_empty(0, len(payload), {"error": "short_header"})
    # ... rest with similar logging for other error paths
```

### 12.2 Add connection reset on repeated reader errors
**File:** `stream_transport.py`
**Issue:** Reader loop swallows errors and keeps spinning
**Fix:** Track error count and trigger reconnect

```python
def _reader_loop(self) -> None:
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5

    while not self._stop:
        try:
            data = self._read_raw(256)
            if data:
                consecutive_errors = 0  # Reset on success
                # ... process data
            else:
                time.sleep(0.01)
        except Exception as e:
            consecutive_errors += 1
            _log.warning("Reader loop error (%d/%d): %s",
                        consecutive_errors, MAX_CONSECUTIVE_ERRORS, e)
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                _log.error("Too many consecutive errors, stopping reader")
                self._stop = True
                break
            time.sleep(0.5)
```

---

## Phase 13: Configuration Validation (Medium Priority)

### 13.1 Add JSON command validation (match binary encoder)
**File:** `client.py`
**Issue:** JSON commands skip NaN/bounds validation
**Fix:** Validate critical fields before sending JSON commands

```python
def _validate_command_payload(self, cmd_type: str, payload: dict) -> None:
    """Validate command payload before sending."""
    import math

    # Validate velocity commands
    if cmd_type == "CMD_SET_VEL":
        vx = payload.get("vx", 0.0)
        omega = payload.get("omega", 0.0)
        if math.isnan(vx) or math.isnan(omega):
            raise ValueError("Velocity values cannot be NaN")
        if math.isinf(vx) or math.isinf(omega):
            raise ValueError("Velocity values cannot be Inf")
```

### 13.2 Add automatic config validation on load
**File:** `robot_config.py`
**Issue:** Validation is optional and often skipped
**Fix:** Always validate, make skip explicit

```python
@classmethod
def load(cls, path: Path | str, *, validate: bool = True, profile: str | None = None):
    # ... load yaml ...
    config = cls.from_dict(data, validate=validate)

    if validate:
        report = config.validate_report()
        if report.errors:
            raise ConfigValidationError(f"Config validation failed: {report.errors}")

    return config
```

### 13.3 Validate numeric bounds in config
**File:** `robot_config.py`
**Issue:** Negative wheel_radius, max_linear_vel not validated
**Fix:** Add explicit bounds validation

```python
@classmethod
def from_dict(cls, data: dict, validate: bool = True) -> "DriveConfig":
    wheel_radius = float(data.get("wheel_radius", 0.05))
    if wheel_radius <= 0:
        raise ValueError(f"wheel_radius must be positive, got {wheel_radius}")

    max_linear_vel = float(data.get("max_linear_vel", 1.0))
    if max_linear_vel <= 0:
        raise ValueError(f"max_linear_vel must be positive, got {max_linear_vel}")
    # ...
```

---

## Phase 14: Thread Safety (Medium Priority)

### 14.1 Make clear_pending_sync atomic
**File:** `reliable_commander.py:555-565`
**Issue:** Non-atomic iteration and clear can lose ACKs
**Fix:** Use try_lock pattern or accept the race

```python
def clear_pending_sync(self) -> None:
    """
    Clear all pending commands synchronously.

    Note: This is inherently racy when called concurrently with on_ack().
    Use clear_pending() (async) when possible.
    """
    # Atomic swap: replace dict with empty, process old
    old_pending = self._pending
    self._pending = {}

    for cmd in old_pending.values():
        if cmd.future and not cmd.future.done():
            cmd.future.set_result((False, "CLEARED"))
```

### 14.2 Fix executor shutdown race in stream_transport
**File:** `stream_transport.py:84-87`
**Issue:** Shutdown while write in progress loses data
**Fix:** Wait briefly for in-flight writes

```python
def stop(self) -> None:
    self._stop = True

    # Wait for reader thread
    if self._thread and self._thread.is_alive():
        self._thread.join(timeout=2.0)
    self._thread = None

    # Give in-flight writes a chance to complete
    if self._write_executor is not None:
        self._write_executor.shutdown(wait=True, cancel_futures=False)
        self._write_executor = None
    # ...
```

---

## Phase 15: Edge Cases (Low Priority)

### 15.1 Fix zero distance handling in telemetry
**File:** `binary_parser.py:132,138`
**Issue:** Zero distance incorrectly treated as "no measurement"
**Fix:** Use sentinel value (0xFFFF) for no measurement instead

```python
# Use 0xFFFF (65535) as "no measurement" sentinel
NO_MEASUREMENT = 0xFFFF

pkt.ultrasonic = UltrasonicTelemetry(
    ...,
    distance_cm=(dist_mm * 0.1) if dist_mm != NO_MEASUREMENT else None,
    ...
)
```

### 15.2 Add rate_limit_hz validation
**File:** `motion_service.py:99-107`
**Issue:** Division by zero possible if rate set to 0 internally
**Fix:** Validate in setter with guard

```python
@rate_limit_hz.setter
def rate_limit_hz(self, value: float) -> None:
    if value <= 0:
        raise ValueError(f"rate_limit_hz must be positive, got {value}")
    self._rate_limit_hz = value
    self._min_interval_s = 1.0 / self._rate_limit_hz
```

---

## Phase 16: API Consistency (Low Priority)

### 16.1 Document exception types in docstrings
**File:** `robot_config.py`
**Issue:** Undocumented exceptions can crash callers
**Fix:** Add Raises section to docstrings

```python
@classmethod
def load(cls, path: Path | str, ...) -> "RobotConfig":
    """
    Load configuration from YAML file.

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        ConfigValidationError: If config fails validation
        ValueError: If required fields are missing or invalid
    """
```

### 16.2 Standardize boolean parsing in config
**File:** `robot_config.py`
**Issue:** String booleans like "yes"/"no" coerced incorrectly
**Fix:** Use explicit boolean parsing

```python
def _parse_bool(value: Any, default: bool = False) -> bool:
    """Parse boolean from various formats."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on')
    return bool(value)

# Usage:
enabled = _parse_bool(data.get("enabled"), default=True)
```

---

## Implementation Order

| Phase | Priority | Effort | Risk if Not Fixed |
|-------|----------|--------|-------------------|
| 9. Async Safety | High | Low | Breaks on Python 3.12+, silent failures |
| 10. Resource Limits | High | Low | OOM on sustained load |
| 11. State Consistency | High | Medium | Race conditions, stale data |
| 12. Error Recovery | Medium | Medium | Silent failures, zombie threads |
| 13. Config Validation | Medium | Medium | Unsafe robot configs |
| 14. Thread Safety | Medium | Low | Lost commands, data races |
| 15. Edge Cases | Low | Low | Rare crashes |
| 16. API Consistency | Low | Low | Developer confusion |

**Recommended order:** 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16

---

## Testing Checklist

- [ ] Python 3.12 compatibility (async loop deprecation)
- [ ] High-frequency command stress test (1000+ pending)
- [ ] Service recreation without close() (subscription leak)
- [ ] Concurrent cache access under load
- [ ] Config with negative values rejected
- [ ] Zero distance telemetry handled correctly
- [ ] Reader thread error recovery

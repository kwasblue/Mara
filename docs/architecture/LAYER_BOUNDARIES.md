# MARA Layer Boundaries

<div align="center">

*Architectural boundaries between API, Services, Client, and Transport*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Layer Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User / Application                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
╔═════════════════════════════════════════════════════════════════════════╗
║                              API Layer                                  ║
║  api/{gpio,servo,pwm,motor,encoder}.py                                 ║
║  ─────────────────────────────────────                                  ║
║  • User-facing interface                                                ║
║  • Validates inputs, raises exceptions                                  ║
║  • Routes to Service layer                                              ║
╚═════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═════════════════════════════════════════════════════════════════════════╗
║                            Service Layer                                ║
║  services/control/{gpio,motion,servo,motor,state}_service.py           ║
║  ─────────────────────────────────────────────────────────              ║
║  • Business logic                                                       ║
║  • State tracking                                                       ║
║  • Returns ServiceResult                                                ║
║  • Calls client.send_reliable() or client.send_stream()                ║
╚═════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═════════════════════════════════════════════════════════════════════════╗
║                            Client Layer                                 ║
║  command/client.py + command/coms/reliable_commander.py                ║
║  ───────────────────────────────────────────────────────                ║
║  • MaraClient: coordinator, routing, handshake                         ║
║  • ReliableCommander: ALL commands flow through here                   ║
║  • Protocol encoding (JSON or binary)                                   ║
║  • Event emission for debugging                                         ║
╚═════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═════════════════════════════════════════════════════════════════════════╗
║                           Transport Layer                               ║
║  transport/{serial,tcp,bluetooth,mqtt,can}_transport.py                ║
║  ───────────────────────────────────────────────────────                ║
║  • Raw byte I/O                                                         ║
║  • Connection management                                                ║
║  • Frame buffering                                                      ║
╚═════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            MCU Firmware                                 │
│  firmware/mcu/ (C++)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### API Layer

```python
# api/gpio.py
class GPIO:
    async def write(self, channel: int, value: int) -> None:
        """
        Write a digital value to a channel.

        Raises:
            ValueError: If channel is not registered
            RuntimeError: If write fails
        """
        # ✅ Validation in API
        if not self.is_registered(channel):
            raise ValueError(f"Channel {channel} is not registered")

        # ✅ Delegate to Service
        result = await self._service.write(channel, value)

        # ✅ Convert result to exception
        if not result.ok:
            raise RuntimeError(result.error)
```

| Does | Does NOT |
|:-----|:---------|
| Validate user inputs | Implement business logic |
| Raise exceptions | Format output |
| Route to services | Manage state |
| Provide clean interface | Access transport directly |

---

### Service Layer

```python
# services/control/gpio_service.py
class GpioService:
    async def write(self, channel: int, value: int) -> ServiceResult:
        """
        Write a digital value to a GPIO channel.

        Returns:
            ServiceResult with success/failure
        """
        # ✅ Business logic
        value = 1 if value else 0

        # ✅ Call client
        ok, error = await self.client.send_reliable(
            "CMD_GPIO_WRITE",
            {"channel": channel, "value": value},
        )

        # ✅ Track state
        if ok:
            ch = self._channels.get(channel)
            if ch:
                ch.value = value
            return ServiceResult.success(data={"channel": channel, "value": value})
        else:
            return ServiceResult.failure(error=error or "Failed")
```

| Does | Does NOT |
|:-----|:---------|
| Business logic | Raise exceptions (returns ServiceResult) |
| State tracking | Format for display |
| Call client methods | Parse arguments |
| Validate domain rules | Handle user interaction |

---

### Client Layer

```python
# command/client.py
class MaraClient:
    async def send_stream(self, cmd_type: str, payload: dict,
                          request_ack: bool = False, binary: bool = False):
        """
        Streaming-friendly send. All commands flow through ReliableCommander.
        """
        if request_ack:
            return await self.send_reliable(cmd_type, payload)

        # ✅ Route through commander (binary or JSON)
        await self.commander.send_fire_and_forget(cmd_type, payload, binary=binary)
        return True, None
```

| Does | Does NOT |
|:-----|:---------|
| Route commands | Know about specific hardware |
| Manage connection | Implement business logic |
| Handle protocol encoding | Track domain state |
| Emit events for debugging | Format user output |

---

### Transport Layer

```python
# transport/stream_transport.py
class StreamTransport:
    async def send_bytes(self, data: bytes) -> None:
        """Send bytes with asyncio coordination."""
        async with self._async_lock:
            await loop.run_in_executor(self._write_executor, self._send_bytes_sync, data)
```

| Does | Does NOT |
|:-----|:---------|
| Raw byte I/O | Parse commands |
| Connection lifecycle | Know about JSON/binary |
| Frame buffering | Track state |
| Thread safety | Business logic |

---

## Data Flow Examples

### GPIO Write

```
User: await gpio.write(0, 1)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  API Layer: gpio.write()                                │
│  • Validate: is_registered(0)? ✓                       │
│  • Call: self._service.write(0, 1)                     │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Service Layer: GpioService.write()                     │
│  • Normalize: value = 1                                 │
│  • Call: client.send_reliable("CMD_GPIO_WRITE", {...}) │
│  • Track: ch.value = 1                                  │
│  • Return: ServiceResult.success()                      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Client Layer: MaraClient.send_reliable()               │
│  • Route: commander.send("CMD_GPIO_WRITE", {...})      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Commander: ReliableCommander.send()                    │
│  • Encode: JSON                                         │
│  • Track: seq=42, pending[42]=Future                   │
│  • Send: transport.send_bytes(frame)                   │
│  • Wait: await future                                  │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Transport: send_bytes()                                │
│  • Serialize: async_lock                               │
│  • Write: _send_bytes(data)                            │
└─────────────────────────────────────────────────────────┘
```

### High-Rate Velocity Streaming

```
User: await motion.set_velocity(0.5, 0.0, binary=True)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Service Layer: MotionService.set_velocity()            │
│  • Clamp: vx = clamp(0.5, -1.0, 1.0)                   │
│  • Call: client.send_stream(..., binary=True)          │
│  • Track: _last_velocity = Velocity(0.5, 0.0)          │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Commander: send_fire_and_forget(binary=True)           │
│  • Encode: struct.pack("<Bff", OPCODE, 0.5, 0.0)       │
│  • Emit: "cmd.sent" event                              │
│  • Stats: commands_sent_binary += 1                    │
│  • Send: transport.send_bytes(frame)                   │
└─────────────────────────────────────────────────────────┘
         │
         ▼
   9 bytes payload → ~15 bytes on wire
   (vs ~50 bytes JSON)
```

---

## Anti-Patterns

### ❌ API doing business logic

```python
# BAD - validation logic in API
class GPIO:
    async def write(self, channel, value):
        if channel in BOOT_PINS:  # ← Business logic!
            raise ValueError("Boot pin")
```

### ❌ Service raising exceptions

```python
# BAD - service raises instead of returning result
class GpioService:
    async def write(self, channel, value):
        if error:
            raise RuntimeError("Failed")  # ← Should return ServiceResult
```

### ❌ Client containing domain logic

```python
# BAD - client knows about specific hardware
class MaraClient:
    async def set_gpio(self, pin, value):
        if pin in self.FLASH_PINS:  # ← Domain knowledge!
            raise ValueError("Flash pin")
```

### ❌ Transport parsing commands

```python
# BAD - transport understands protocol semantics
class SerialTransport:
    async def send_bytes(self, data):
        cmd = json.loads(data)  # ← Should be opaque bytes
        if cmd["type"] == "CMD_ARM":
            ...
```

---

## Testing Strategy

| Layer | Test Type | Dependencies |
|:------|:----------|:-------------|
| API | Integration | Mock services |
| Service | Unit | Mock client |
| Client | Unit | Fake transport |
| Transport | Integration | Hardware/simulator |

```python
# Service unit test (no hardware)
async def test_motion_service_clamps_velocity():
    mock_client = Mock()
    service = MotionService(mock_client)

    await service.set_velocity(vx=10.0, omega=0.0)  # Exceeds limit

    # Verify clamping
    mock_client.send_stream.assert_called_with(
        "CMD_SET_VEL",
        {"vx": 1.0, "omega": 0.0},  # Clamped to limit
        request_ack=False,
        binary=True,
    )
```

---

## Summary

```
┌────────────┬──────────────────────────────────────────────────────────┐
│   Layer    │                      Responsibility                      │
├────────────┼──────────────────────────────────────────────────────────┤
│    API     │  Validation, exceptions, user-facing interface          │
├────────────┼──────────────────────────────────────────────────────────┤
│  Service   │  Business logic, state tracking, ServiceResult          │
├────────────┼──────────────────────────────────────────────────────────┤
│  Client    │  Protocol encoding, routing, event emission             │
├────────────┼──────────────────────────────────────────────────────────┤
│ Commander  │  Single chokepoint for all commands                     │
├────────────┼──────────────────────────────────────────────────────────┤
│ Transport  │  Raw bytes, connection management                       │
└────────────┴──────────────────────────────────────────────────────────┘
```

**Golden rule:** Keep each layer focused. When in doubt, push logic down to services.

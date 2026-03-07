# MARA Layer Boundaries

This document clarifies the architectural boundaries between CLI, Services, and Client layers.

## Layer Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User / Application                           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                               │
│  cli/commands/{test,run,calibrate,pins}/                            │
│  - Argument parsing                                                  │
│  - User interaction (prompts, tables, progress)                      │
│  - Output formatting (rich console)                                  │
│  - Orchestrates services                                             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Service Layer                              │
│  services/{pins,testing,recording,codegen}/                          │
│  - Business logic                                                    │
│  - Stateful operations                                               │
│  - Validation and conflict detection                                 │
│  - Persistence (file I/O)                                            │
│  - Creates and manages clients                                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Command Layer                              │
│  command/{client,factory,interfaces}/                                │
│  - MaraClient - connection lifecycle                                 │
│  - Protocol handling (JSON commands, ACK/retry)                      │
│  - Transport abstraction                                             │
│  - Event bus for telemetry                                           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Transport Layer                             │
│  transport/{serial,tcp,can,mqtt,bluetooth}/                          │
│  - Raw byte I/O                                                      │
│  - Connection management                                             │
│  - Frame protocol (STX/ETX)                                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           MCU Firmware                               │
│  firmware/mcu/ (C++)                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### CLI Layer (`cli/commands/`)

**What it does:**
- Parses command-line arguments
- Displays output (tables, progress bars, prompts)
- Handles user interaction (confirmations, wizards)
- Orchestrates calls to services
- Returns exit codes

**What it does NOT do:**
- Business logic
- Direct hardware communication
- File I/O (delegates to services)
- State management

**Example:**
```python
# cli/commands/pins/assign.py
def cmd_assign(args):
    service = PinService()  # Create service

    # CLI handles user interaction
    if info.warning and not args.force:
        print_warning(info.warning)
        if not confirm("Continue?"):
            return 0

    # Delegate to service
    success, message = service.assign(args.name, args.gpio)

    # CLI handles output
    if success:
        print_success(message)
    else:
        print_error(message)
```

### Service Layer (`services/`)

**What it does:**
- Implements business logic
- Manages state and persistence
- Validates inputs
- Creates clients when hardware access needed
- Encapsulates domain knowledge

**What it does NOT do:**
- User interaction (prompts, formatting)
- Argument parsing
- Console output

**Example:**
```python
# services/pins/pin_service.py
class PinService:
    def assign(self, name: str, gpio: int) -> tuple[bool, str]:
        # Validation
        if self.is_flash_pin(gpio):
            return False, f"GPIO {gpio} is a flash pin"

        # Conflict detection
        if name in self._assignments:
            return False, f"{name} already assigned"

        # Persistence
        self._assignments[name] = gpio
        self._save()

        return True, f"Assigned {name} to GPIO {gpio}"
```

### Command Layer (`command/`)

**What it does:**
- Manages connection lifecycle
- Sends commands with retry logic
- Parses responses
- Routes telemetry to event bus
- Provides transport abstraction

**What it does NOT do:**
- Business logic
- User interaction
- Domain-specific knowledge

**Key classes:**
- `MaraClient` - Main client interface
- `MaraClientFactory` - Client creation
- `IMaraClient` - Abstract interface
- `ReliableCommander` - ACK/retry logic

### Transport Layer (`transport/`)

**What it does:**
- Raw byte I/O
- Connection/disconnection
- Frame protocol (STX/ETX wrapping)
- Transport-specific details

**What it does NOT do:**
- Command semantics
- Parsing JSON
- Business logic

## When to Use Each Layer

### CLI should call Services when:
- The operation involves business logic
- State needs to be managed
- Validation is required
- The operation might be reused outside CLI

### CLI can call Client directly when:
- Simple pass-through commands
- Interactive shells where service layer adds no value
- Real-time streaming

### Services should create Clients when:
- Hardware communication is needed
- Multiple commands need coordination
- Error handling needs business context

## Anti-Patterns to Avoid

### ❌ CLI doing business logic
```python
# BAD: CLI contains validation logic
def cmd_assign(args):
    if args.gpio in FLASH_PINS:
        print_error("Flash pin!")
        return 1
```

### ❌ Service doing user interaction
```python
# BAD: Service prompts user
class PinService:
    def assign(self, name, gpio):
        if self.is_boot_pin(gpio):
            if input("Continue? ") != "y":  # BAD!
                return False
```

### ❌ Client containing business logic
```python
# BAD: Client knows about pin constraints
class MaraClient:
    def set_gpio(self, pin, value):
        if pin in self.BOOT_PINS:  # BAD!
            raise ValueError("Boot pin")
```

## File Organization

```
mara_host/
├── cli/
│   └── commands/
│       ├── pins/           # Pin management CLI
│       │   ├── _registry.py    # Argument registration
│       │   ├── _common.py      # Shared CLI helpers
│       │   ├── list.py         # List commands
│       │   ├── assign.py       # Assignment commands
│       │   └── wizard.py       # Interactive wizards
│       ├── test/           # Hardware test CLI
│       ├── run/            # Connection CLI
│       └── calibrate/      # Calibration CLI
│
├── services/
│   ├── pins/               # Pin business logic
│   │   └── pin_service.py
│   ├── testing/            # Test orchestration
│   │   └── test_service.py
│   ├── recording/          # Session recording
│   │   └── recording_service.py
│   └── codegen/            # Code generation
│       └── generator_service.py
│
├── command/
│   ├── client.py           # MaraClient
│   ├── factory.py          # MaraClientFactory
│   ├── interfaces.py       # IMaraClient
│   └── coms/
│       ├── reliable_commander.py
│       └── connection_monitor.py
│
└── transport/
    ├── serial_transport.py
    ├── tcp_transport.py
    ├── can_transport.py
    └── mqtt/
```

## Testing Implications

| Layer | Test Type | Dependencies |
|-------|-----------|--------------|
| CLI | Integration | Mock services |
| Service | Unit | Mock client/transport |
| Command | Unit | Fake transport |
| Transport | Integration | Hardware/simulator |

## Summary

1. **CLI** = presentation + user interaction
2. **Service** = business logic + state
3. **Command** = protocol + connection
4. **Transport** = bytes + hardware

Keep each layer focused. When in doubt, push logic down to services.

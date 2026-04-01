# Tooling Backends

MARA's build, flash, and test operations are abstracted through pluggable backends.
This allows swapping the entire toolchain without changing CLI commands or services.

## Architecture

```
backends/
├── interfaces.py           # Abstract base classes (BuildBackend, FlashBackend, TestBackend)
├── models.py               # Data models (BuildRequest, BuildOutcome, etc.)
├── registry.py             # Backend registration and lookup
├── _generated_loaders.py   # Auto-generated loader (do not edit)
│
└── implementations/        # <-- All backend implementations go here
    ├── __init__.py         # Documentation and discovery
    ├── platformio/         # PlatformIO implementation
    │   ├── __init__.py     # Exports + register_backends()
    │   ├── build_backend.py
    │   ├── flash_backend.py
    │   └── test_backend.py
    └── cmake/              # CMake/ESP-IDF implementation
        ├── __init__.py     # Exports + register_backends()
        ├── build_backend.py
        ├── flash_backend.py
        └── test_backend.py
```

The separation is intentional:
- **Top level**: Interfaces, models, registry (the contract)
- **implementations/**: All concrete implementations (the adapters)

## Interface Contracts

### BuildBackend

```python
class BuildBackend(ABC):
    @abstractmethod
    def build(self, request: BuildRequest) -> BuildOutcome:
        """Compile firmware. Returns success status, output, and size info."""

    @abstractmethod
    def clean(self, environment: str | None = None) -> BuildOutcome:
        """Remove build artifacts."""

    @abstractmethod
    def get_version(self) -> str | None:
        """Return backend version string (e.g., 'PlatformIO Core, version 6.1.11')."""
```

### FlashBackend

```python
class FlashBackend(ABC):
    @abstractmethod
    def flash(self, request: FlashRequest) -> FlashOutcome:
        """Upload compiled firmware to device."""

    @abstractmethod
    def detect_devices(self) -> list[str]:
        """Return list of serial ports with connected devices."""
```

### TestBackend

```python
class TestBackend(ABC):
    @abstractmethod
    def run_tests(self, request: TestRequest) -> TestOutcome:
        """Execute firmware tests. Returns results with pass/fail counts."""
```

## Data Models

```python
# Build
@dataclass
class BuildRequest:
    environment: str           # Target environment (e.g., "esp32dev")
    project_dir: Path | None   # Project path (default: firmware/mcu)
    features: dict[str, bool]  # Feature flags as -D definitions
    verbose: bool              # Stream output to console

@dataclass
class BuildOutcome:
    success: bool
    return_code: int
    output: str
    error: str
    firmware_size: int | None  # Flash usage in bytes
    ram_usage: int | None      # RAM usage in bytes

# Flash
@dataclass
class FlashRequest:
    port: str                  # Serial port (e.g., "/dev/ttyUSB0")
    environment: str           # Target environment
    project_dir: Path | None
    baud_rate: int             # Upload baud rate
    verbose: bool

@dataclass
class FlashOutcome:
    success: bool
    return_code: int
    output: str
    error: str

# Test
@dataclass
class TestRequest:
    environment: TestEnvironment  # native, esp32, or hil
    filter_pattern: str | None    # Test name filter (e.g., "test_imu*")
    verbose: bool
    project_dir: Path | None

@dataclass
class TestOutcome:
    success: bool
    return_code: int
    output: str
    passed: int
    failed: int
    skipped: int
```

## Adding a New Backend

### Step 1: Create Directory Structure

```bash
mkdir -p host/mara_host/services/tooling/backends/implementations/mybackend
```

### Step 2: Implement Backend Classes

**build_backend.py:**
```python
from ..interfaces import BuildBackend
from ..models import BuildRequest, BuildOutcome

class MyBuildBackend(BuildBackend):
    def build(self, request: BuildRequest) -> BuildOutcome:
        # Your build logic here
        # Use request.environment, request.project_dir, request.features
        # Return BuildOutcome with success, output, firmware_size, ram_usage
        ...

    def clean(self, environment: str | None = None) -> BuildOutcome:
        # Clean build artifacts
        ...

    def get_version(self) -> str | None:
        # Return version string or None
        ...
```

**flash_backend.py:**
```python
from ..interfaces import FlashBackend
from ..models import FlashRequest, FlashOutcome

class MyFlashBackend(FlashBackend):
    def flash(self, request: FlashRequest) -> FlashOutcome:
        # Your flash logic here
        ...

    def detect_devices(self) -> list[str]:
        # Return list of serial ports
        ...
```

**test_backend.py:**
```python
from ..interfaces import TestBackend
from ..models import TestRequest, TestOutcome

class MyTestBackend(TestBackend):
    def run_tests(self, request: TestRequest) -> TestOutcome:
        # Your test logic here
        ...
```

### Step 3: Create Package Init

**\_\_init\_\_.py:**
```python
"""My backend adapter."""

from .build_backend import MyBuildBackend
from .flash_backend import MyFlashBackend
from .test_backend import MyTestBackend

__all__ = [
    "MyBuildBackend",
    "MyFlashBackend",
    "MyTestBackend",
    "register_backends",
]


def register_backends(registry) -> None:
    """Register all backends with the registry."""
    registry.register_build("mybackend", MyBuildBackend())
    registry.register_flash("mybackend", MyFlashBackend())
    registry.register_test("mybackend", MyTestBackend())
```

### Step 4: Regenerate Loaders

```bash
cd host
mara generate tooling
# or
python -m mara_host.tools.gen_tooling_backends
```

This discovers your new backend directory and updates `_generated_loaders.py`.

### Step 5: Configure as Default (Optional)

Edit `host/mara_host/cli/cli_config.py`:

```python
def get_tooling_backend() -> str:
    return os.environ.get("MARA_TOOLING_BACKEND", "mybackend")
```

Or set environment variable:
```bash
export MARA_TOOLING_BACKEND=mybackend
```

## Testing Your Backend

Run the backend tests:

```bash
cd host
pytest tests/test_tooling_backends.py -v
```

The test suite validates:
- Interface compliance (all abstract methods implemented)
- Registry discovery
- Integration tests (if the backend tool is installed)

## Backend Selection at Runtime

Backends are selected via:

1. **Environment variable**: `MARA_TOOLING_BACKEND=cmake`
2. **CLI config**: `cli_config.get_tooling_backend()`
3. **Default**: `platformio`

The registry loads all discovered backends on first access:

```python
from mara_host.services.tooling.backends import get_registry

registry = get_registry()
build = registry.get_build("cmake")  # or "platformio"
result = build.build(request)
```

## Partial Implementations

You can implement only some backends. For example, if your tool only builds:

```python
def register_backends(registry) -> None:
    registry.register_build("mybackend", MyBuildBackend())
    # Skip flash and test if not supported
```

The CLI will fall back to another backend for unsupported operations.

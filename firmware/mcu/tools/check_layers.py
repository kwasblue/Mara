#!/usr/bin/env python3
"""
Firmware Layer Architecture Checker

Enforces include dependencies between firmware layers to prevent
architectural violations. Run as part of CI or via `make check-firmware-layers`.

Layer Hierarchy (lower layers cannot depend on higher layers):
    Tier 0: hal/        - Hardware abstraction (platform only)
    Tier 1: core/       - Core utilities
    Tier 2: motor/      - Motor control
            sensor/     - Sensors (peer to motor)
    Tier 3: control/    - Control algorithms
            telemetry/  - Telemetry
            transport/  - Communication
    Tier 4: command/    - Command handling
            module/     - Higher-level modules
    Tier 5: setup/      - Initialization
            loop/       - Main loops
            config/     - Configuration
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field

# =============================================================================
# LAYER ARCHITECTURE
# =============================================================================
#
# config/     - Compile-time configuration (FeatureFlags, PinConfig, etc.)
#               Can be included by ANY layer - it's not runtime code.
#
# hal/        - Hardware abstraction (GPIO, PWM, I2C interfaces)
#               Should only include config/ and platform headers.
#
# core/       - Core infrastructure (EventBus, Protocol, ServiceContext)
#               Can include: hal/, config/
#               Exception: ServiceStorage.h is the composition root.
#
# motor/      - Motor actuators (DC, Servo, Stepper)
# sensor/     - Sensors (IMU, Encoder, Ultrasonic)
# hw/         - Hardware managers (GPIO, PWM managers)
#               Can include: hal/, core/, config/
#               motor/ and sensor/ are peers - should not cross-include.
#
# control/    - Control algorithms (PID, observers, signal bus)
#               Can include: hal/, core/, motor/, sensor/, config/
#
# transport/  - Communication (UART, WiFi, BLE, MQTT, CAN)
#               Can include: hal/, core/, config/
#               Should NOT include motor/, sensor/, control/.
#
# telemetry/  - Telemetry formatting and transmission
#               Can include: hal/, core/, sensor/, motor/, config/
#
# command/    - Command handling (registry, handlers, router)
#               Can include most layers.
#
# module/     - High-level modules (Heartbeat, Logging, Identity)
#               Can include most layers.
#
# setup/      - Initialization and composition
# loop/       - Main loop functions
#               Can include everything (orchestration layer).
#
# =============================================================================

# All recognized layer directories
ALL_LAYERS = {
    "hal", "core", "motor", "sensor", "hw", "audio",
    "control", "transport", "telemetry",
    "command", "module",
    "setup", "loop", "config",
}

# Layers that can be included by ANYONE (compile-time only, no runtime deps)
UNIVERSAL_LAYERS = {"config"}

# Files that are "composition roots" - allowed to break layer rules
COMPOSITION_ROOTS = {
    "core/ServiceStorage.h",
    "core/ServiceStorage.cpp",
    "core/Runtime.h",
    "core/Runtime.cpp",
    "core/McuHost.cpp",
}

# Forbidden includes: source_layer -> set of layers it cannot include
# config/ is implicitly allowed everywhere via UNIVERSAL_LAYERS
FORBIDDEN_INCLUDES: Dict[str, Set[str]] = {
    # hal cannot include project layers (except config)
    "hal": {"core", "motor", "sensor", "control", "telemetry", "transport", "command", "module", "setup", "loop", "audio", "hw"},

    # core cannot include higher layers (except via composition roots)
    "core": {"motor", "sensor", "control", "telemetry", "transport", "command", "module", "setup", "loop", "audio", "hw"},

    # motor and sensor are peers - shouldn't cross-depend
    "motor": {"sensor", "telemetry", "transport", "command", "module", "setup", "loop"},
    "sensor": {"motor", "telemetry", "transport", "command", "module", "setup", "loop"},

    # hw managers are low-level
    "hw": {"motor", "sensor", "control", "telemetry", "transport", "command", "module", "setup", "loop"},

    # transport shouldn't know about domain logic
    "transport": {"motor", "sensor", "control", "telemetry", "command", "module", "setup", "loop", "audio", "hw"},

    # control can use motor/sensor but not higher layers
    "control": {"telemetry", "transport", "command", "module", "setup", "loop"},

    # telemetry can read from sensors but not command layers
    "telemetry": {"command", "module", "setup", "loop"},
}

# Files to skip (generated, external, etc.)
SKIP_PATTERNS = [
    "test/",
    ".pio/",
    "lib/",
]

@dataclass
class Violation:
    file: str
    line_num: int
    layer: str
    included_layer: str
    include_path: str

@dataclass
class CheckResult:
    files_checked: int = 0
    violations: List[Violation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0


def get_layer(file_path: str) -> str | None:
    """Extract the layer name from a file path."""
    parts = Path(file_path).parts

    # Look for layer directories in include/ or src/
    for i, part in enumerate(parts):
        if part in ("include", "src") and i + 1 < len(parts):
            potential_layer = parts[i + 1]
            if potential_layer in ALL_LAYERS:
                return potential_layer

    return None


def extract_includes(file_path: Path) -> List[Tuple[int, str]]:
    """Extract all #include statements from a file."""
    includes = []
    include_pattern = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]')

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                match = include_pattern.match(line)
                if match:
                    includes.append((line_num, match.group(1)))
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)

    return includes


def get_included_layer(include_path: str) -> str | None:
    """Extract the layer from an include path."""
    # Handle paths like "motor/DcMotorManager.h" or "core/EventBus.h"
    parts = include_path.split("/")
    if len(parts) >= 1 and parts[0] in ALL_LAYERS:
        return parts[0]

    # Handle paths like "../motor/DcMotorManager.h"
    for part in parts:
        if part in ALL_LAYERS:
            return part

    return None


def is_composition_root(rel_path: str) -> bool:
    """Check if a file is a composition root (allowed to break layer rules)."""
    # Normalize path separators
    normalized = rel_path.replace("\\", "/")

    for root in COMPOSITION_ROOTS:
        if normalized.endswith(root) or root in normalized:
            return True

    return False


def check_file(file_path: Path, base_dir: Path) -> List[Violation]:
    """Check a single file for layer violations."""
    violations = []

    rel_path = str(file_path.relative_to(base_dir))

    # Skip test files and external libs
    for pattern in SKIP_PATTERNS:
        if pattern in rel_path:
            return []

    # Skip composition roots - they're allowed to include everything
    if is_composition_root(rel_path):
        return []

    source_layer = get_layer(rel_path)
    if source_layer is None:
        return []

    forbidden = FORBIDDEN_INCLUDES.get(source_layer, set())

    for line_num, include_path in extract_includes(file_path):
        included_layer = get_included_layer(include_path)

        # Universal layers (config/) can be included by anyone
        if included_layer in UNIVERSAL_LAYERS:
            continue

        if included_layer and included_layer in forbidden:
            violations.append(Violation(
                file=rel_path,
                line_num=line_num,
                layer=source_layer,
                included_layer=included_layer,
                include_path=include_path,
            ))

    return violations


def check_directory(base_dir: Path) -> CheckResult:
    """Check all files in a directory for layer violations."""
    result = CheckResult()

    for ext in ("*.h", "*.hpp", "*.cpp", "*.c"):
        for file_path in base_dir.rglob(ext):
            # Skip .pio directory
            if ".pio" in str(file_path):
                continue

            result.files_checked += 1
            violations = check_file(file_path, base_dir)
            result.violations.extend(violations)

    return result


def print_report(result: CheckResult) -> None:
    """Print the check results."""
    print(f"\nFirmware Layer Check")
    print(f"{'=' * 60}")
    print(f"Files checked: {result.files_checked}")
    print(f"Violations: {len(result.violations)}")

    if result.violations:
        print(f"\n{'=' * 60}")
        print("VIOLATIONS:")
        print(f"{'=' * 60}\n")

        # Group by layer
        by_layer: Dict[str, List[Violation]] = {}
        for v in result.violations:
            by_layer.setdefault(v.layer, []).append(v)

        for layer in sorted(by_layer.keys()):
            print(f"\n[{layer}/] cannot include from:")
            for v in by_layer[layer]:
                print(f"  {v.file}:{v.line_num}")
                print(f"    includes [{v.included_layer}/] via: {v.include_path}")
    else:
        print("\nAll layer dependencies are valid.")


def main():
    # Find firmware/mcu directory
    script_dir = Path(__file__).parent
    mcu_dir = script_dir.parent

    if not (mcu_dir / "include").exists():
        print(f"Error: Could not find include/ directory in {mcu_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Checking firmware layers in: {mcu_dir}")

    result = check_directory(mcu_dir)
    print_report(result)

    if not result.passed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

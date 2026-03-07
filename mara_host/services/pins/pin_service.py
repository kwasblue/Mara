# mara_host/services/pins/pin_service.py
"""
Pin management service.

This is the canonical source for all pin-related business logic.
CLI commands should delegate to this service for validation,
conflict detection, and recommendations.

The service returns data structures (not formatted output) so that
clients can format the results appropriately for their context.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from mara_host.tools.pins import (
    ESP32_PINS,
    SAFE_PINS,
    INPUT_ONLY_PINS,
    FLASH_PINS,
    BOOT_PINS,
    Capability,
    PinInfo,
    load_pins,
    save_pins,
    get_assignments,
    generate_pinout,
    cap_str,
)


@dataclass
class PinConflict:
    """Represents a conflict or warning about a pin configuration."""
    gpio: int
    severity: str  # "error", "warning", "info"
    conflict_type: str  # e.g., "i2c_incomplete", "adc2_wifi", "boot_pin"
    message: str
    affected_pins: list[int] = field(default_factory=list)


@dataclass
class PinRecommendation:
    """A recommended pin assignment for a use case."""
    gpio: int
    score: int
    notes: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class GroupRecommendation:
    """Recommendation for a group of related pins (e.g., motor, encoder)."""
    suggested_assignments: dict[str, int]  # name -> gpio
    warnings: list[str] = field(default_factory=list)
    alternatives: list[dict[str, int]] = field(default_factory=list)


# Pin group templates for common configurations
PIN_GROUPS = {
    "motor": {
        "pins": ["PWM", "IN1", "IN2"],
        "capabilities": [
            Capability.PWM | Capability.OUTPUT,
            Capability.OUTPUT,
            Capability.OUTPUT,
        ],
        "description": "DC motor (PWM + direction pins)",
    },
    "encoder": {
        "pins": ["A", "B"],
        "capabilities": [Capability.INPUT, Capability.INPUT],
        "description": "Quadrature encoder (A + B channels)",
    },
    "stepper": {
        "pins": ["STEP", "DIR", "EN"],
        "capabilities": [Capability.OUTPUT, Capability.OUTPUT, Capability.OUTPUT],
        "description": "Stepper motor (STEP + DIR + EN)",
    },
    "servo": {
        "pins": ["SIG"],
        "capabilities": [Capability.PWM | Capability.OUTPUT],
        "description": "Servo motor (PWM signal)",
    },
    "i2c": {
        "pins": ["SDA", "SCL"],
        "capabilities": [Capability.I2C, Capability.I2C],
        "default_gpios": [21, 22],
        "description": "I2C bus (SDA + SCL)",
    },
    "spi": {
        "pins": ["MOSI", "MISO", "CLK", "CS"],
        "capabilities": [Capability.SPI, Capability.SPI, Capability.SPI, Capability.OUTPUT],
        "default_gpios": [23, 19, 18, 5],
        "description": "SPI bus (MOSI, MISO, CLK, CS)",
    },
    "uart": {
        "pins": ["TX", "RX"],
        "capabilities": [Capability.UART, Capability.UART],
        "default_gpios": [17, 16],
        "description": "UART (TX + RX)",
    },
}


class PinService:
    """
    Service for managing GPIO pin assignments.

    This is the business logic layer for pin management.
    All validation, conflict detection, and recommendations
    should go through this service.

    Example:
        service = PinService()

        # Get available pins
        free = service.get_free_pins()

        # Get pin recommendations
        pwm_pins = service.suggest_pins("pwm")

        # Assign a pin
        service.assign("LED_PIN", 2)

        # Detect conflicts
        conflicts = service.detect_conflicts()

        # Get motor pin recommendation
        rec = service.recommend_motor_pins("LEFT")
    """

    def __init__(self, pins_json_path: Optional[Path] = None):
        """
        Initialize pin service.

        Args:
            pins_json_path: Custom path to pins.json. If None, uses default.
        """
        self._pins_path = pins_json_path

    # -------------------------------------------------------------------------
    # Read operations
    # -------------------------------------------------------------------------

    def get_all_pins(self) -> dict[int, PinInfo]:
        """Get information about all ESP32 GPIO pins."""
        return ESP32_PINS.copy()

    def get_pin_info(self, gpio: int) -> Optional[PinInfo]:
        """Get detailed information about a specific GPIO pin."""
        return ESP32_PINS.get(gpio)

    def get_assignments(self) -> dict[str, int]:
        """Get current pin assignments (name -> gpio)."""
        return load_pins()

    def get_assignments_by_gpio(self) -> dict[int, str]:
        """Get current pin assignments (gpio -> name)."""
        return get_assignments()

    def get_free_pins(self, required_caps: Capability = Capability.NONE) -> list[int]:
        """
        Get list of unassigned pins.

        Args:
            required_caps: Only return pins with these capabilities.

        Returns:
            List of GPIO numbers that are free and match requirements.
        """
        assigned = set(self.get_assignments().values())
        free = []

        for gpio, info in ESP32_PINS.items():
            # Skip flash pins and assigned pins
            if info.capabilities == Capability.NONE:
                continue
            if gpio in assigned:
                continue

            # Check capability requirements
            if required_caps != Capability.NONE:
                if not (info.capabilities & required_caps):
                    continue

            free.append(gpio)

        return sorted(free)

    def get_safe_pins(self) -> list[int]:
        """Get pins that are safe to use (no boot/flash restrictions)."""
        safe = []
        for gpio, info in ESP32_PINS.items():
            if info.capabilities == Capability.NONE:
                continue
            if info.warning:
                continue
            safe.append(gpio)
        return sorted(safe)

    def capability_string(self, gpio: int) -> str:
        """Get human-readable capability string for a pin."""
        info = ESP32_PINS.get(gpio)
        if not info:
            return "Unknown"
        return cap_str(info.capabilities)

    # -------------------------------------------------------------------------
    # Pin Classification
    # -------------------------------------------------------------------------

    def is_flash_pin(self, gpio: int) -> bool:
        """Check if GPIO is connected to flash (unusable)."""
        return gpio in FLASH_PINS

    def is_boot_pin(self, gpio: int) -> bool:
        """Check if GPIO is a boot strapping pin."""
        return gpio in BOOT_PINS

    def is_input_only(self, gpio: int) -> bool:
        """Check if GPIO is input-only (GPIO 34-39)."""
        return gpio in INPUT_ONLY_PINS

    def is_safe_pin(self, gpio: int) -> bool:
        """Check if GPIO is safe (no boot/flash restrictions)."""
        return gpio in SAFE_PINS

    def get_flash_pins(self) -> set[int]:
        """Get set of flash-connected pins (unusable)."""
        return FLASH_PINS.copy()

    def get_boot_pins(self) -> set[int]:
        """Get set of boot strapping pins (use with caution)."""
        return BOOT_PINS.copy()

    def get_input_only_pins(self) -> set[int]:
        """Get set of input-only pins (GPIO 34-39)."""
        return INPUT_ONLY_PINS.copy()

    def get_safe_pin_set(self) -> set[int]:
        """Get set of safe pins (no restrictions)."""
        return SAFE_PINS.copy()

    def get_free_pins_by_category(self) -> dict[str, list[int]]:
        """
        Get free pins organized by category.

        Returns:
            Dict with keys: "safe", "input_only", "boot", "other"
            Each value is a list of available GPIO numbers.
        """
        assigned = set(self.get_assignments().values())
        result = {
            "safe": [],
            "input_only": [],
            "boot": [],
            "other": [],
        }

        for gpio in ESP32_PINS:
            if gpio in assigned:
                continue
            if gpio in FLASH_PINS:
                continue  # Never include flash pins

            if gpio in SAFE_PINS:
                result["safe"].append(gpio)
            elif gpio in INPUT_ONLY_PINS:
                result["input_only"].append(gpio)
            elif gpio in BOOT_PINS:
                result["boot"].append(gpio)
            else:
                result["other"].append(gpio)

        # Sort each category
        for key in result:
            result[key].sort()

        return result

    def get_use_case_notes(self, use_case: str) -> list[str]:
        """
        Get informational notes for a use case.

        Args:
            use_case: One of "pwm", "adc", "input", "output", "i2c", etc.

        Returns:
            List of helpful notes/tips for the use case.
        """
        notes = {
            "adc": [
                "ADC2 pins (GPIO 0,2,4,12-15,25-27) don't work when WiFi is active.",
                "ADC1 pins (GPIO 32-39) work with WiFi.",
            ],
            "i2c": [
                "Default I2C pins are GPIO 21 (SDA) and 22 (SCL).",
            ],
            "spi": [
                "Default VSPI pins: MOSI=23, MISO=19, CLK=18, CS=5.",
                "HSPI uses GPIO 12-15 (conflicts with boot strapping).",
            ],
            "uart": [
                "UART0 (GPIO 1,3) is used by USB serial - avoid these.",
                "UART1 default pins may conflict with flash (GPIO 9,10).",
                "UART2 default pins: TX=17, RX=16.",
            ],
            "pwm": [
                "All output-capable GPIO pins support PWM via LEDC.",
                "Input-only pins (GPIO 34-39) cannot output PWM.",
            ],
            "touch": [
                "Touch pins are GPIO 0,2,4,12,13,14,15,27,32,33.",
            ],
            "dac": [
                "Only GPIO 25 (DAC1) and GPIO 26 (DAC2) support analog output.",
            ],
        }
        return notes.get(use_case.lower(), [])

    # -------------------------------------------------------------------------
    # Write operations
    # -------------------------------------------------------------------------

    def assign(self, name: str, gpio: int) -> tuple[bool, str]:
        """
        Assign a name to a GPIO pin.

        Args:
            name: Symbolic name for the pin (e.g., "MOTOR_A_PWM")
            gpio: GPIO number to assign

        Returns:
            Tuple of (success, message)
        """
        # Validate GPIO exists
        if gpio not in ESP32_PINS:
            return False, f"GPIO {gpio} is not a valid ESP32 pin"

        info = ESP32_PINS[gpio]

        # Check if pin is usable
        if info.capabilities == Capability.NONE:
            return False, f"GPIO {gpio} is not usable: {info.warning}"

        # Load current assignments
        pins = load_pins()

        # Check if name already exists
        if name in pins:
            old_gpio = pins[name]
            if old_gpio == gpio:
                return True, f"{name} already assigned to GPIO {gpio}"
            return False, f"{name} already assigned to GPIO {old_gpio}. Remove it first."

        # Check if GPIO already assigned
        for existing_name, existing_gpio in pins.items():
            if existing_gpio == gpio:
                return False, f"GPIO {gpio} already assigned to {existing_name}"

        # Save assignment
        pins[name] = gpio
        save_pins(pins)

        message = f"Assigned {name} to GPIO {gpio}"
        if info.warning:
            message += f" (warning: {info.warning})"

        return True, message

    def remove(self, name: str) -> tuple[bool, str]:
        """
        Remove a pin assignment.

        Args:
            name: Name of the assignment to remove

        Returns:
            Tuple of (success, message)
        """
        pins = load_pins()

        if name not in pins:
            return False, f"No assignment found for '{name}'"

        gpio = pins.pop(name)
        save_pins(pins)

        return True, f"Removed {name} (was GPIO {gpio})"

    def clear_all(self) -> tuple[bool, str]:
        """Remove all pin assignments."""
        pins = load_pins()
        count = len(pins)
        save_pins({})
        return True, f"Cleared {count} pin assignment(s)"

    # -------------------------------------------------------------------------
    # Conflict Detection
    # -------------------------------------------------------------------------

    def detect_conflicts(self) -> list[PinConflict]:
        """
        Detect all conflicts and issues in current pin configuration.

        Returns:
            List of PinConflict objects with severity levels.
        """
        conflicts = []
        assignments = self.get_assignments()

        # Check individual pins
        for name, gpio in assignments.items():
            info = ESP32_PINS.get(gpio)
            if not info:
                conflicts.append(PinConflict(
                    gpio=gpio,
                    severity="error",
                    conflict_type="invalid_gpio",
                    message=f"{name}: GPIO {gpio} is not a valid pin",
                    affected_pins=[gpio]
                ))
                continue

            # Check for boot pin warnings
            if gpio in BOOT_PINS:
                conflicts.append(PinConflict(
                    gpio=gpio,
                    severity="warning",
                    conflict_type="boot_pin",
                    message=f"{name}: GPIO {gpio} is a boot strapping pin - {info.warning}",
                    affected_pins=[gpio]
                ))

            # Check for flash pins
            if gpio in FLASH_PINS:
                conflicts.append(PinConflict(
                    gpio=gpio,
                    severity="error",
                    conflict_type="flash_pin",
                    message=f"{name}: GPIO {gpio} is connected to flash - DO NOT USE",
                    affected_pins=[gpio]
                ))

            # Check for UART0 conflicts
            if gpio in {1, 3}:  # TX0, RX0
                conflicts.append(PinConflict(
                    gpio=gpio,
                    severity="warning",
                    conflict_type="uart0",
                    message=f"{name}: GPIO {gpio} is used by USB serial",
                    affected_pins=[gpio]
                ))

        # Check for incomplete I2C
        conflicts.extend(self._check_i2c_conflicts(assignments))

        # Check for incomplete UART
        conflicts.extend(self._check_uart_conflicts(assignments))

        # Check ADC2 + WiFi conflict
        conflicts.extend(self._check_adc2_conflicts(assignments))

        return conflicts

    def _check_i2c_conflicts(self, assignments: dict[str, int]) -> list[PinConflict]:
        """Check for incomplete I2C configurations."""
        conflicts = []
        i2c_sda = None
        i2c_scl = None

        for name, gpio in assignments.items():
            if "SDA" in name.upper():
                i2c_sda = (name, gpio)
            if "SCL" in name.upper():
                i2c_scl = (name, gpio)

        if i2c_sda and not i2c_scl:
            conflicts.append(PinConflict(
                gpio=i2c_sda[1],
                severity="warning",
                conflict_type="i2c_incomplete",
                message=f"I2C incomplete: SDA assigned ({i2c_sda[0]}=GPIO{i2c_sda[1]}) but SCL missing",
                affected_pins=[i2c_sda[1]]
            ))
        if i2c_scl and not i2c_sda:
            conflicts.append(PinConflict(
                gpio=i2c_scl[1],
                severity="warning",
                conflict_type="i2c_incomplete",
                message=f"I2C incomplete: SCL assigned ({i2c_scl[0]}=GPIO{i2c_scl[1]}) but SDA missing",
                affected_pins=[i2c_scl[1]]
            ))

        return conflicts

    def _check_uart_conflicts(self, assignments: dict[str, int]) -> list[PinConflict]:
        """Check for incomplete UART configurations."""
        conflicts = []
        uart_pins: dict[str, dict[str, tuple[str, int]]] = {}

        for name, gpio in assignments.items():
            upper_name = name.upper()
            if "UART" in upper_name or "TX" in upper_name or "RX" in upper_name:
                # Extract UART number if present
                for i in range(3):
                    if f"UART{i}" in upper_name or f"UART_{i}" in upper_name:
                        uart_id = str(i)
                        if uart_id not in uart_pins:
                            uart_pins[uart_id] = {}
                        if "TX" in upper_name:
                            uart_pins[uart_id]["tx"] = (name, gpio)
                        if "RX" in upper_name:
                            uart_pins[uart_id]["rx"] = (name, gpio)

        for uart_num, pins_dict in uart_pins.items():
            if "tx" in pins_dict and "rx" not in pins_dict:
                conflicts.append(PinConflict(
                    gpio=pins_dict["tx"][1],
                    severity="warning",
                    conflict_type="uart_incomplete",
                    message=f"UART{uart_num} incomplete: TX assigned but RX missing",
                    affected_pins=[pins_dict["tx"][1]]
                ))
            if "rx" in pins_dict and "tx" not in pins_dict:
                conflicts.append(PinConflict(
                    gpio=pins_dict["rx"][1],
                    severity="warning",
                    conflict_type="uart_incomplete",
                    message=f"UART{uart_num} incomplete: RX assigned but TX missing",
                    affected_pins=[pins_dict["rx"][1]]
                ))

        return conflicts

    def _check_adc2_conflicts(self, assignments: dict[str, int]) -> list[PinConflict]:
        """Check for ADC2 + WiFi conflicts."""
        conflicts = []
        adc2_gpio = {0, 2, 4, 12, 13, 14, 15, 25, 26, 27}
        adc2_assigned = []

        for name, gpio in assignments.items():
            if gpio in adc2_gpio:
                info = ESP32_PINS.get(gpio)
                if info and info.adc_channel and "ADC2" in info.adc_channel:
                    if "ADC" in name.upper():
                        adc2_assigned.append((name, gpio))

        if adc2_assigned:
            conflicts.append(PinConflict(
                gpio=adc2_assigned[0][1],
                severity="warning",
                conflict_type="adc2_wifi",
                message=f"ADC2 pins assigned ({', '.join(f'{n}=GPIO{g}' for n, g in adc2_assigned)}). "
                        "These won't work when WiFi is active.",
                affected_pins=[gpio for _, gpio in adc2_assigned]
            ))

        return conflicts

    # -------------------------------------------------------------------------
    # Pin Recommendations
    # -------------------------------------------------------------------------

    def suggest_pins(self, use_case: str, count: int = 5) -> list[PinRecommendation]:
        """
        Suggest best pins for a use case.

        Args:
            use_case: One of "pwm", "adc", "input", "output", "i2c", "spi", "uart", "touch"
            count: Number of recommendations to return

        Returns:
            List of pin recommendations, best first.
        """
        assigned = set(self.get_assignments().values())
        recommendations = []

        # Define capability requirements for use cases
        use_case_caps = {
            "pwm": Capability.PWM | Capability.OUTPUT,
            "adc": Capability.ADC,
            "input": Capability.INPUT,
            "output": Capability.OUTPUT,
            "i2c": Capability.I2C,
            "spi": Capability.SPI,
            "uart": Capability.UART,
            "touch": Capability.TOUCH,
            "dac": Capability.DAC,
            "encoder": Capability.INPUT,
        }

        required = use_case_caps.get(use_case.lower(), Capability.INPUT | Capability.OUTPUT)

        for gpio, info in ESP32_PINS.items():
            # Skip unusable and assigned pins
            if info.capabilities == Capability.NONE:
                continue
            if gpio in assigned:
                continue

            # Check capability match
            if not (info.capabilities & required):
                continue

            # Score the pin (higher = better)
            score = 100
            warnings = []

            # Prefer safe pins
            if gpio in SAFE_PINS:
                score += 20

            # Penalize boot/strapping pins
            if gpio in BOOT_PINS:
                score -= 30
                warnings.append("Boot strapping pin")

            # Heavily penalize UART0 pins
            if gpio in {1, 3}:
                score -= 50
                warnings.append("USB serial pin")

            # Prefer pins with more capabilities (more flexible)
            cap_count = bin(info.capabilities.value).count('1')
            score += cap_count * 2

            # For ADC, prefer ADC1 over ADC2 (WiFi conflict)
            if use_case.lower() == "adc" and info.adc_channel:
                if "ADC1" in info.adc_channel:
                    score += 20
                else:
                    warnings.append("ADC2 conflicts with WiFi")

            # Input-only pins are great for inputs
            if use_case.lower() in ("input", "adc") and gpio in INPUT_ONLY_PINS:
                score += 10

            # Input-only pins can't do output/PWM
            if use_case.lower() in ("output", "pwm") and gpio in INPUT_ONLY_PINS:
                continue  # Skip entirely

            recommendations.append(PinRecommendation(
                gpio=gpio,
                score=score,
                notes=info.notes,
                warnings=warnings
            ))

        # Sort by score descending
        recommendations.sort(key=lambda r: r.score, reverse=True)

        return recommendations[:count]

    def recommend_motor_pins(self, motor_id: str) -> GroupRecommendation:
        """
        Recommend pins for a DC motor.

        Args:
            motor_id: Motor identifier (e.g., "LEFT", "RIGHT", "0")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return self._recommend_group_pins(
            group_type="motor",
            prefix=f"MOTOR_{motor_id.upper()}_"
        )

    def recommend_encoder_pins(self, encoder_id: str) -> GroupRecommendation:
        """
        Recommend pins for a quadrature encoder.

        Args:
            encoder_id: Encoder identifier (e.g., "0", "LEFT")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return self._recommend_group_pins(
            group_type="encoder",
            prefix=f"ENC{encoder_id.upper()}_"
        )

    def recommend_i2c_pins(self) -> GroupRecommendation:
        """
        Recommend pins for I2C bus.

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return self._recommend_group_pins(
            group_type="i2c",
            prefix="I2C_"
        )

    def recommend_spi_pins(self) -> GroupRecommendation:
        """
        Recommend pins for SPI bus.

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return self._recommend_group_pins(
            group_type="spi",
            prefix="SPI_"
        )

    def recommend_uart_pins(self, uart_num: str = "1") -> GroupRecommendation:
        """
        Recommend pins for UART.

        Args:
            uart_num: UART number (e.g., "1", "2")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return self._recommend_group_pins(
            group_type="uart",
            prefix=f"UART{uart_num}_"
        )

    def recommend_stepper_pins(self, stepper_id: str) -> GroupRecommendation:
        """
        Recommend pins for a stepper motor.

        Args:
            stepper_id: Stepper identifier (e.g., "0", "X", "Y")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return self._recommend_group_pins(
            group_type="stepper",
            prefix=f"STEPPER{stepper_id.upper()}_"
        )

    def recommend_servo_pins(self, servo_id: str) -> GroupRecommendation:
        """
        Recommend pins for a servo motor.

        Args:
            servo_id: Servo identifier (e.g., "0", "PAN", "TILT")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return self._recommend_group_pins(
            group_type="servo",
            prefix=f"SERVO{servo_id.upper()}_"
        )

    def _recommend_group_pins(self, group_type: str, prefix: str) -> GroupRecommendation:
        """
        Internal: Recommend pins for a group configuration.

        Args:
            group_type: Key from PIN_GROUPS dict
            prefix: Prefix for pin names

        Returns:
            GroupRecommendation with suggested_assignments.
        """
        group = PIN_GROUPS.get(group_type)
        if not group:
            return GroupRecommendation(
                suggested_assignments={},
                warnings=[f"Unknown group type: {group_type}"]
            )

        assigned = set(self.get_assignments().values())
        suggestions: dict[str, int] = {}
        warnings: list[str] = []
        used_gpios: set[int] = set()

        pin_names = group["pins"]
        capabilities = group["capabilities"]
        defaults = group.get("default_gpios", [])

        for i, pin_suffix in enumerate(pin_names):
            full_name = f"{prefix}{pin_suffix}"
            required_cap = capabilities[i]

            # Try default GPIO first
            if i < len(defaults):
                default_gpio = defaults[i]
                if default_gpio not in assigned and default_gpio not in used_gpios:
                    info = ESP32_PINS.get(default_gpio)
                    if info and (info.capabilities & required_cap):
                        suggestions[full_name] = default_gpio
                        used_gpios.add(default_gpio)
                        if info.warning:
                            warnings.append(f"GPIO {default_gpio}: {info.warning}")
                        continue

            # Find best available pin
            candidates = self.suggest_pins(
                use_case=self._cap_to_use_case(required_cap),
                count=10
            )

            for rec in candidates:
                if rec.gpio not in used_gpios:
                    suggestions[full_name] = rec.gpio
                    used_gpios.add(rec.gpio)
                    warnings.extend(rec.warnings)
                    break
            else:
                warnings.append(f"No available pin for {full_name}")

        return GroupRecommendation(
            suggested_assignments=suggestions,
            warnings=warnings
        )

    def _cap_to_use_case(self, cap: Capability) -> str:
        """Convert capability to use case string for suggest_pins."""
        if Capability.PWM in cap:
            return "pwm"
        if Capability.ADC in cap:
            return "adc"
        if Capability.I2C in cap:
            return "i2c"
        if Capability.SPI in cap:
            return "spi"
        if Capability.UART in cap:
            return "uart"
        if Capability.TOUCH in cap:
            return "touch"
        if Capability.OUTPUT in cap:
            return "output"
        return "input"

    # -------------------------------------------------------------------------
    # Display helpers
    # -------------------------------------------------------------------------

    def generate_pinout_diagram(self) -> str:
        """Generate ASCII pinout diagram of the ESP32 DevKit."""
        return generate_pinout()

    def validate(self) -> list[PinConflict]:
        """
        Validate current pin configuration.

        Alias for detect_conflicts() for backwards compatibility.
        """
        return self.detect_conflicts()

# mara_host/services/pins/service.py
"""
Pin management service.

This is the canonical source for all pin-related business logic.
CLI commands should delegate to this service for validation,
conflict detection, and recommendations.

The service returns data structures (not formatted output) so that
clients can format the results appropriately for their context.
"""

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

from .models import PinConflict, PinRecommendation, GroupRecommendation
from .conflicts import detect_conflicts as _detect_conflicts
from .recommendations import (
    suggest_pins as _suggest_pins,
    recommend_group_pins,
    get_use_case_notes,
)


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
        return get_use_case_notes(use_case)

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
        return _detect_conflicts(self.get_assignments())

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
        return _suggest_pins(use_case, assigned, count)

    def recommend_motor_pins(self, motor_id: str) -> GroupRecommendation:
        """
        Recommend pins for a DC motor.

        Args:
            motor_id: Motor identifier (e.g., "LEFT", "RIGHT", "0")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return recommend_group_pins(
            group_type="motor",
            prefix=f"MOTOR_{motor_id.upper()}_",
            assigned=set(self.get_assignments().values()),
        )

    def recommend_encoder_pins(self, encoder_id: str) -> GroupRecommendation:
        """
        Recommend pins for a quadrature encoder.

        Args:
            encoder_id: Encoder identifier (e.g., "0", "LEFT")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return recommend_group_pins(
            group_type="encoder",
            prefix=f"ENC{encoder_id.upper()}_",
            assigned=set(self.get_assignments().values()),
        )

    def recommend_i2c_pins(self) -> GroupRecommendation:
        """
        Recommend pins for I2C bus.

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return recommend_group_pins(
            group_type="i2c",
            prefix="I2C_",
            assigned=set(self.get_assignments().values()),
        )

    def recommend_spi_pins(self) -> GroupRecommendation:
        """
        Recommend pins for SPI bus.

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return recommend_group_pins(
            group_type="spi",
            prefix="SPI_",
            assigned=set(self.get_assignments().values()),
        )

    def recommend_uart_pins(self, uart_num: str = "1") -> GroupRecommendation:
        """
        Recommend pins for UART.

        Args:
            uart_num: UART number (e.g., "1", "2")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return recommend_group_pins(
            group_type="uart",
            prefix=f"UART{uart_num}_",
            assigned=set(self.get_assignments().values()),
        )

    def recommend_stepper_pins(self, stepper_id: str) -> GroupRecommendation:
        """
        Recommend pins for a stepper motor.

        Args:
            stepper_id: Stepper identifier (e.g., "0", "X", "Y")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return recommend_group_pins(
            group_type="stepper",
            prefix=f"STEPPER{stepper_id.upper()}_",
            assigned=set(self.get_assignments().values()),
        )

    def recommend_servo_pins(self, servo_id: str) -> GroupRecommendation:
        """
        Recommend pins for a servo motor.

        Args:
            servo_id: Servo identifier (e.g., "0", "PAN", "TILT")

        Returns:
            GroupRecommendation with suggested_assignments dict.
        """
        return recommend_group_pins(
            group_type="servo",
            prefix=f"SERVO{servo_id.upper()}_",
            assigned=set(self.get_assignments().values()),
        )

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

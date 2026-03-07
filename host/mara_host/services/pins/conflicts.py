# mara_host/services/pins/conflicts.py
"""Conflict detection for pin configurations."""

from mara_host.tools.pins import (
    ESP32_PINS,
    FLASH_PINS,
    BOOT_PINS,
)
from .models import PinConflict


def detect_conflicts(assignments: dict[str, int]) -> list[PinConflict]:
    """
    Detect all conflicts and issues in current pin configuration.

    Args:
        assignments: Dict of name -> gpio assignments

    Returns:
        List of PinConflict objects with severity levels.
    """
    conflicts = []

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
    conflicts.extend(check_i2c_conflicts(assignments))

    # Check for incomplete UART
    conflicts.extend(check_uart_conflicts(assignments))

    # Check ADC2 + WiFi conflict
    conflicts.extend(check_adc2_conflicts(assignments))

    return conflicts


def check_i2c_conflicts(assignments: dict[str, int]) -> list[PinConflict]:
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


def check_uart_conflicts(assignments: dict[str, int]) -> list[PinConflict]:
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


def check_adc2_conflicts(assignments: dict[str, int]) -> list[PinConflict]:
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

#!/usr/bin/env python3
"""
ESP32 Pin Data and I/O Module

This module provides:
- Pin data structures (Capability, PinInfo)
- ESP32 pin database (ESP32_PINS)
- Pin group constants (SAFE_PINS, FLASH_PINS, etc.)
- I/O functions (load_pins, save_pins, get_assignments)
- Utility functions (cap_str, generate_pinout)

Business logic (validation, recommendations) is in services/pins/PinService.
CLI commands are in cli/commands/pins.py.
"""

import json
from dataclasses import dataclass
from enum import Flag, auto
from pathlib import Path
from typing import Optional

# Paths
PINS_JSON = Path(__file__).parent.parent / "config" / "pins.json"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class Capability(Flag):
    """Pin capabilities for ESP32."""
    NONE = 0
    INPUT = auto()
    OUTPUT = auto()
    ADC = auto()           # Analog input
    DAC = auto()           # Analog output
    TOUCH = auto()         # Capacitive touch
    PWM = auto()           # LEDC PWM output
    I2C = auto()           # I2C capable
    SPI = auto()           # SPI capable
    UART = auto()          # UART capable
    RTC = auto()           # RTC GPIO (wake from deep sleep)
    PULLUP = auto()        # Internal pull-up available
    PULLDOWN = auto()      # Internal pull-down available


@dataclass
class PinInfo:
    """Complete information about an ESP32 GPIO pin."""
    gpio: int
    capabilities: Capability
    adc_channel: Optional[str] = None    # e.g., "ADC1_CH0"
    touch_channel: Optional[int] = None  # Touch sensor number
    rtc_gpio: Optional[int] = None       # RTC GPIO number
    notes: str = ""
    warning: str = ""                    # Boot strapping, restricted, etc.


# =============================================================================
# ESP32 PIN DATABASE
# =============================================================================

# ESP32 (standard) complete pinout reference
# Reference: ESP32 Technical Reference Manual & Datasheet
ESP32_PINS: dict[int, PinInfo] = {
    0: PinInfo(
        gpio=0,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH1",
        touch_channel=1,
        rtc_gpio=11,
        notes="Boot mode select pin",
        warning="BOOT: Must be HIGH during boot. Has internal pull-up. Directly connected to boot button on many boards.",
    ),
    1: PinInfo(
        gpio=1,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.UART | Capability.PWM,
        notes="TX0 - USB Serial TX",
        warning="UART0: Connected to USB-Serial. Debug output. Avoid unless you disable serial.",
    ),
    2: PinInfo(
        gpio=2,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH2",
        touch_channel=2,
        rtc_gpio=12,
        notes="On-board LED on many dev boards",
        warning="BOOT: Must be LOW or floating during boot on some boards.",
    ),
    3: PinInfo(
        gpio=3,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.UART | Capability.PWM,
        notes="RX0 - USB Serial RX",
        warning="UART0: Connected to USB-Serial. Avoid unless you disable serial.",
    ),
    4: PinInfo(
        gpio=4,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH0",
        touch_channel=0,
        rtc_gpio=10,
        notes="Good general purpose GPIO",
    ),
    5: PinInfo(
        gpio=5,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.SPI | Capability.PULLUP | Capability.PULLDOWN,
        notes="VSPI CS0, strapping pin",
        warning="BOOT: Controls timing of SDIO slave. Has internal pull-up.",
    ),
    6: PinInfo(
        gpio=6,
        capabilities=Capability.NONE,
        notes="Flash SPI CLK",
        warning="FLASH: Connected to internal flash. DO NOT USE.",
    ),
    7: PinInfo(
        gpio=7,
        capabilities=Capability.NONE,
        notes="Flash SPI D0",
        warning="FLASH: Connected to internal flash. DO NOT USE.",
    ),
    8: PinInfo(
        gpio=8,
        capabilities=Capability.NONE,
        notes="Flash SPI D1",
        warning="FLASH: Connected to internal flash. DO NOT USE.",
    ),
    9: PinInfo(
        gpio=9,
        capabilities=Capability.NONE,
        notes="Flash SPI D2",
        warning="FLASH: Connected to internal flash. DO NOT USE.",
    ),
    10: PinInfo(
        gpio=10,
        capabilities=Capability.NONE,
        notes="Flash SPI D3",
        warning="FLASH: Connected to internal flash. DO NOT USE.",
    ),
    11: PinInfo(
        gpio=11,
        capabilities=Capability.NONE,
        notes="Flash SPI CMD",
        warning="FLASH: Connected to internal flash. DO NOT USE.",
    ),
    12: PinInfo(
        gpio=12,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH5",
        touch_channel=5,
        rtc_gpio=15,
        notes="HSPI MISO, strapping pin",
        warning="BOOT: Sets flash voltage. Must be LOW during boot for 3.3V flash (most boards).",
    ),
    13: PinInfo(
        gpio=13,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH4",
        touch_channel=4,
        rtc_gpio=14,
        notes="HSPI MOSI. Good general purpose GPIO.",
    ),
    14: PinInfo(
        gpio=14,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH6",
        touch_channel=6,
        rtc_gpio=16,
        notes="HSPI CLK. Good general purpose GPIO.",
    ),
    15: PinInfo(
        gpio=15,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH3",
        touch_channel=3,
        rtc_gpio=13,
        notes="HSPI CS0, strapping pin",
        warning="BOOT: Controls debug log output at boot. Outputs PWM at boot.",
    ),
    16: PinInfo(
        gpio=16,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.UART | Capability.PULLUP | Capability.PULLDOWN,
        notes="UART2 RX. Good general purpose GPIO.",
    ),
    17: PinInfo(
        gpio=17,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.UART | Capability.PULLUP | Capability.PULLDOWN,
        notes="UART2 TX. Good general purpose GPIO.",
    ),
    18: PinInfo(
        gpio=18,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.SPI | Capability.PULLUP | Capability.PULLDOWN,
        notes="VSPI CLK. Excellent general purpose GPIO.",
    ),
    19: PinInfo(
        gpio=19,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.SPI | Capability.PULLUP | Capability.PULLDOWN,
        notes="VSPI MISO. Excellent general purpose GPIO.",
    ),
    21: PinInfo(
        gpio=21,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.I2C | Capability.PULLUP | Capability.PULLDOWN,
        notes="I2C SDA (default). Excellent general purpose GPIO.",
    ),
    22: PinInfo(
        gpio=22,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.I2C | Capability.PULLUP | Capability.PULLDOWN,
        notes="I2C SCL (default). Excellent general purpose GPIO.",
    ),
    23: PinInfo(
        gpio=23,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.PWM | Capability.SPI | Capability.PULLUP | Capability.PULLDOWN,
        notes="VSPI MOSI. Excellent general purpose GPIO.",
    ),
    25: PinInfo(
        gpio=25,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.DAC | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH8",
        rtc_gpio=6,
        notes="DAC1 output. Good general purpose GPIO.",
    ),
    26: PinInfo(
        gpio=26,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.DAC | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH9",
        rtc_gpio=7,
        notes="DAC2 output. Good general purpose GPIO.",
    ),
    27: PinInfo(
        gpio=27,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC2_CH7",
        touch_channel=7,
        rtc_gpio=17,
        notes="Good general purpose GPIO.",
    ),
    32: PinInfo(
        gpio=32,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC1_CH4",
        touch_channel=9,
        rtc_gpio=9,
        notes="ADC1 - works with WiFi. Good for analog input.",
    ),
    33: PinInfo(
        gpio=33,
        capabilities=Capability.INPUT | Capability.OUTPUT | Capability.ADC | Capability.TOUCH | Capability.PWM | Capability.RTC | Capability.PULLUP | Capability.PULLDOWN,
        adc_channel="ADC1_CH5",
        touch_channel=8,
        rtc_gpio=8,
        notes="ADC1 - works with WiFi. Good for analog input.",
    ),
    34: PinInfo(
        gpio=34,
        capabilities=Capability.INPUT | Capability.ADC | Capability.RTC,
        adc_channel="ADC1_CH6",
        rtc_gpio=4,
        notes="Input only, no pull-up/pull-down",
        warning="INPUT ONLY: Cannot be used as output. No internal pull resistors.",
    ),
    35: PinInfo(
        gpio=35,
        capabilities=Capability.INPUT | Capability.ADC | Capability.RTC,
        adc_channel="ADC1_CH7",
        rtc_gpio=5,
        notes="Input only, no pull-up/pull-down",
        warning="INPUT ONLY: Cannot be used as output. No internal pull resistors.",
    ),
    36: PinInfo(
        gpio=36,
        capabilities=Capability.INPUT | Capability.ADC | Capability.RTC,
        adc_channel="ADC1_CH0",
        rtc_gpio=0,
        notes="VP (Sensor_VP). Input only, no pull-up/pull-down",
        warning="INPUT ONLY: Cannot be used as output. No internal pull resistors.",
    ),
    37: PinInfo(
        gpio=37,
        capabilities=Capability.INPUT | Capability.ADC | Capability.RTC,
        adc_channel="ADC1_CH1",
        rtc_gpio=1,
        notes="Input only (not exposed on most dev boards)",
        warning="INPUT ONLY: Cannot be used as output. Not on most dev boards.",
    ),
    38: PinInfo(
        gpio=38,
        capabilities=Capability.INPUT | Capability.ADC | Capability.RTC,
        adc_channel="ADC1_CH2",
        rtc_gpio=2,
        notes="Input only (not exposed on most dev boards)",
        warning="INPUT ONLY: Cannot be used as output. Not on most dev boards.",
    ),
    39: PinInfo(
        gpio=39,
        capabilities=Capability.INPUT | Capability.ADC | Capability.RTC,
        adc_channel="ADC1_CH3",
        rtc_gpio=3,
        notes="VN (Sensor_VN). Input only, no pull-up/pull-down",
        warning="INPUT ONLY: Cannot be used as output. No internal pull resistors.",
    ),
}


# =============================================================================
# PIN GROUP CONSTANTS
# =============================================================================

# Pins that are generally safe and recommended for most uses
SAFE_PINS = {4, 13, 14, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33}

# Input-only pins (34-39)
INPUT_ONLY_PINS = {34, 35, 36, 37, 38, 39}

# Pins connected to flash (6-11) - never use
FLASH_PINS = {6, 7, 8, 9, 10, 11}

# Boot strapping pins - be careful
BOOT_PINS = {0, 2, 5, 12, 15}


# =============================================================================
# I/O FUNCTIONS
# =============================================================================

def load_pins() -> dict[str, int]:
    """Load current pin assignments from pins.json."""
    if PINS_JSON.exists():
        return json.loads(PINS_JSON.read_text())
    return {}


def save_pins(pins: dict[str, int]) -> None:
    """Save pin assignments to pins.json."""
    PINS_JSON.write_text(json.dumps(pins, indent=2) + "\n")


def get_assignments() -> dict[int, str]:
    """Get mapping of GPIO number -> assigned name."""
    pins = load_pins()
    return {v: k for k, v in pins.items()}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def cap_str(cap: Capability) -> str:
    """Format capabilities as a compact string."""
    parts = []
    if Capability.INPUT in cap:
        parts.append("IN")
    if Capability.OUTPUT in cap:
        parts.append("OUT")
    if Capability.ADC in cap:
        parts.append("ADC")
    if Capability.DAC in cap:
        parts.append("DAC")
    if Capability.TOUCH in cap:
        parts.append("TCH")
    if Capability.PWM in cap:
        parts.append("PWM")
    if Capability.I2C in cap:
        parts.append("I2C")
    if Capability.SPI in cap:
        parts.append("SPI")
    if Capability.UART in cap:
        parts.append("UART")
    if Capability.RTC in cap:
        parts.append("RTC")
    return ",".join(parts) if parts else "NONE"


def generate_pinout() -> str:
    """Generate ASCII pinout diagram and return as string."""
    assignments = get_assignments()
    lines = []

    def fmt_label(gpio: int, max_len: int = 14) -> str:
        """Format a pin label with assignment info."""
        if gpio == -1:
            return ""
        if gpio in assignments:
            name = assignments[gpio]
            if len(name) > max_len:
                name = name[:max_len-2] + ".."
            return name
        elif gpio in FLASH_PINS:
            return "~~FLASH~~"
        else:
            return ""

    def pin_marker(gpio: int) -> str:
        """Get status marker for a pin."""
        if gpio == -1:
            return "="  # Power/ground
        if gpio in assignments:
            return "#"  # Assigned
        if gpio in FLASH_PINS:
            return "x"  # Unusable
        if gpio in BOOT_PINS:
            return "!"  # Boot pin (caution)
        if gpio in INPUT_ONLY_PINS:
            return ">"  # Input only
        return "o"  # Available

    # ESP32 DevKit V1 30-pin layout
    left_pins = [
        ("3V3", -1, "3.3V"),
        ("EN", -1, "RST"),
        ("VP", 36, ""),
        ("VN", 39, ""),
        ("34", 34, ""),
        ("35", 35, ""),
        ("32", 32, ""),
        ("33", 33, ""),
        ("25", 25, ""),
        ("26", 26, ""),
        ("27", 27, ""),
        ("14", 14, ""),
        ("12", 12, ""),
        ("GND", -1, "GND"),
        ("13", 13, ""),
    ]

    right_pins = [
        ("VIN", -1, "5V"),
        ("GND", -1, "GND"),
        ("23", 23, ""),
        ("22", 22, ""),
        ("TX", 1, ""),
        ("RX", 3, ""),
        ("21", 21, ""),
        ("19", 19, ""),
        ("18", 18, ""),
        ("5", 5, ""),
        ("17", 17, ""),
        ("16", 16, ""),
        ("4", 4, ""),
        ("0", 0, ""),
        ("2", 2, ""),
    ]

    W = 16  # Label width

    # Header
    lines.append("")
    lines.append("╔══════════════════════════════════════════════════════════════════════════════╗")
    lines.append("║                         ESP32 DevKit V1 - Pin Assignment                     ║")
    lines.append("╚══════════════════════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("                              ┌───────────────────┐")
    lines.append("                              │    ╔═════════╗    │")
    lines.append("                              │    ║  ESP32  ║    │")
    lines.append("                              │    ║ WROOM32 ║    │")
    lines.append("                              │    ╚═════════╝    │")
    lines.append("                              │                   │")
    lines.append("                              │    ┌───────┐      │")
    lines.append("                              │    │ micro │      │")
    lines.append("                              │    │  USB  │      │")
    lines.append("                        ┌─────┴────┴───────┴──────┴─────┐")

    # Pin rows
    for i in range(len(left_pins)):
        lbl_l, gpio_l, desc_l = left_pins[i]
        marker_l = pin_marker(gpio_l)
        assign_l = fmt_label(gpio_l, W)
        if not assign_l and desc_l:
            assign_l = desc_l

        if i < len(right_pins):
            lbl_r, gpio_r, desc_r = right_pins[i]
            marker_r = pin_marker(gpio_r)
            assign_r = fmt_label(gpio_r, W)
            if not assign_r and desc_r:
                assign_r = desc_r
        else:
            lbl_r, marker_r, assign_r = "", " ", ""

        left_info = f"{assign_l:>{W}}"
        right_info = f"{assign_r:<{W}}"

        lines.append(f"  {left_info} {marker_l}│ {lbl_l:>3} ○───────────○ {lbl_r:<3} │{marker_r} {right_info}")

    # Footer
    lines.append("                        └─────────────────────────────────┘")
    lines.append("")
    lines.append("  ┌─────────────────────────────────────────────────────────────────────────────┐")
    lines.append("  │  LEGEND                                                                    │")
    lines.append("  │    # = assigned        o = available       ! = boot strapping pin          │")
    lines.append("  │    > = input only      x = flash (unusable)    = = power/ground            │")
    lines.append("  └─────────────────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # Summary
    assigned = len(assignments)
    available_safe = len(SAFE_PINS - set(assignments.keys()))
    available_input = len(INPUT_ONLY_PINS - set(assignments.keys()))
    available_boot = len((BOOT_PINS - set(assignments.keys())) - FLASH_PINS)

    lines.append(f"  SUMMARY: {assigned} assigned │ {available_safe} safe available │ {available_input} input-only │ {available_boot} boot pins")
    lines.append("")

    # Pin assignment table
    if assignments:
        lines.append("  ┌─────────────────────────────────────────────────────────────────────────────┐")
        lines.append("  │  ACTIVE ASSIGNMENTS                                                        │")
        lines.append("  ├─────────────────────────────────────────────────────────────────────────────┤")

        # Sort by GPIO number
        sorted_assignments = sorted(assignments.items(), key=lambda x: x[0])
        row = "  │ "
        for gpio, name in sorted_assignments:
            entry = f" GPIO{gpio:>2}={name:<14}"
            if len(row) + len(entry) > 78:
                lines.append(row.ljust(79) + "│")
                row = "  │ "
            row += entry
        if row != "  │ ":
            lines.append(row.ljust(79) + "│")

        lines.append("  └─────────────────────────────────────────────────────────────────────────────┘")
        lines.append("")

    return "\n".join(lines)

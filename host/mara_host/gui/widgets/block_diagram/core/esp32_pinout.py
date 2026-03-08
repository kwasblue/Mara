# mara_host/gui/widgets/block_diagram/core/esp32_pinout.py
"""
ESP32 WROOM DevKit comprehensive pinout data.

Based on the official ESP32-WROOM-32 DevKit pinout reference.
This module provides detailed information for each GPIO pin including:
- Alternate functions (ADC, DAC, TOUCH, SPI, I2C, UART, etc.)
- Input/output capabilities
- Boot strapping restrictions
- Flash connection warnings
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class PinCapability(Enum):
    """Pin capability flags."""
    INPUT = auto()
    OUTPUT = auto()
    INPUT_ONLY = auto()
    PWM = auto()
    ADC = auto()
    DAC = auto()
    TOUCH = auto()
    I2C = auto()
    SPI = auto()
    UART = auto()
    RTC = auto()
    STRAPPING = auto()  # Boot strapping pin
    FLASH = auto()  # Connected to flash - DO NOT USE


@dataclass
class ESP32PinInfo:
    """Complete information about an ESP32 GPIO pin."""
    gpio: int
    name: str  # Primary name (e.g., "GPIO23")

    # Capabilities
    input: bool = True
    output: bool = True

    # Alternate functions
    adc1_channel: Optional[int] = None  # ADC1 channel number
    adc2_channel: Optional[int] = None  # ADC2 channel number
    dac_channel: Optional[int] = None   # DAC channel (1 or 2)
    touch_channel: Optional[int] = None # Touch sensor channel
    rtc_gpio: Optional[int] = None      # RTC GPIO number

    # Bus functions
    hspi: Optional[str] = None   # HSPI function (CLK, MISO, MOSI, CS)
    vspi: Optional[str] = None   # VSPI function
    i2c: Optional[str] = None    # I2C function (SDA, SCL)
    uart0: Optional[str] = None  # UART0 function (TX, RX)
    uart2: Optional[str] = None  # UART2 function (TX, RX)

    # SD card
    sd_card: Optional[str] = None  # SD card function

    # Restrictions
    strapping: bool = False     # Boot strapping pin
    flash_connected: bool = False  # Connected to internal flash
    input_only: bool = False    # Input only (no output)

    # Notes and warnings
    notes: str = ""
    warning: str = ""

    # Color coding for display (matches pinout image)
    color_category: str = "gpio"  # gpio, power, ground, flash, adc, touch, etc.

    def get_functions(self) -> list[str]:
        """Get list of all alternate functions."""
        funcs = []
        if self.adc1_channel is not None:
            funcs.append(f"ADC1_{self.adc1_channel}")
        if self.adc2_channel is not None:
            funcs.append(f"ADC2_{self.adc2_channel}")
        if self.dac_channel is not None:
            funcs.append(f"DAC_{self.dac_channel}")
        if self.touch_channel is not None:
            funcs.append(f"TOUCH_{self.touch_channel}")
        if self.rtc_gpio is not None:
            funcs.append(f"RTC_GPIO{self.rtc_gpio}")
        if self.hspi:
            funcs.append(f"HSPI_{self.hspi}")
        if self.vspi:
            funcs.append(f"VSPI_{self.vspi}")
        if self.i2c:
            funcs.append(f"I2C_{self.i2c}")
        if self.uart0:
            funcs.append(f"UART0_{self.uart0}")
        if self.uart2:
            funcs.append(f"UART2_{self.uart2}")
        if self.sd_card:
            funcs.append(f"SD_{self.sd_card}")
        return funcs

    def get_capability_string(self) -> str:
        """Get human-readable capability string."""
        caps = []
        if self.input and self.output:
            caps.append("I/O")
        elif self.input_only:
            caps.append("Input only")
        elif self.input:
            caps.append("Input")
        if self.output and not self.input_only:
            if "I/O" not in caps:
                caps.append("Output")
        if self.adc1_channel is not None or self.adc2_channel is not None:
            caps.append("ADC")
        if self.dac_channel is not None:
            caps.append("DAC")
        if self.touch_channel is not None:
            caps.append("Touch")
        return ", ".join(caps) if caps else "GPIO"

    def is_safe(self) -> bool:
        """Check if pin is safe to use without restrictions."""
        return not self.strapping and not self.flash_connected and not self.input_only


# Complete ESP32 WROOM DevKit pinout based on reference image
ESP32_PINOUT: dict[int, ESP32PinInfo] = {
    # GPIO0 - Boot strapping pin
    0: ESP32PinInfo(
        gpio=0,
        name="GPIO0",
        adc2_channel=1,
        touch_channel=1,
        rtc_gpio=11,
        strapping=True,
        warning="Boot strapping - must be HIGH during boot",
        notes="Used for boot mode selection. Connect to HIGH for normal boot.",
        color_category="strapping",
    ),

    # GPIO1 - UART0 TX (used for programming)
    1: ESP32PinInfo(
        gpio=1,
        name="GPIO1",
        uart0="TX",
        notes="UART0 TX - Used for serial programming/debug",
        warning="Connected to USB-UART, outputs debug data at boot",
        color_category="uart",
    ),

    # GPIO2 - Boot strapping pin, onboard LED on many boards
    2: ESP32PinInfo(
        gpio=2,
        name="GPIO2",
        adc2_channel=2,
        touch_channel=2,
        rtc_gpio=12,
        hspi="CS",  # Also HSPI WP
        strapping=True,
        warning="Boot strapping - must be LOW or floating during boot",
        notes="Often connected to onboard LED. Safe for output after boot.",
        color_category="strapping",
    ),

    # GPIO3 - UART0 RX (used for programming)
    3: ESP32PinInfo(
        gpio=3,
        name="GPIO3",
        uart0="RX",
        notes="UART0 RX - Used for serial programming/debug",
        warning="Connected to USB-UART, HIGH at boot",
        color_category="uart",
    ),

    # GPIO4 - Safe GPIO
    4: ESP32PinInfo(
        gpio=4,
        name="GPIO4",
        adc2_channel=0,
        touch_channel=0,
        rtc_gpio=10,
        notes="Safe to use. No boot restrictions.",
        color_category="gpio",
    ),

    # GPIO5 - Boot strapping (VSPI CS)
    5: ESP32PinInfo(
        gpio=5,
        name="GPIO5",
        vspi="CS",
        strapping=True,
        warning="Outputs PWM at boot",
        notes="VSPI CS0. Boot strapping pin.",
        color_category="spi",
    ),

    # GPIO6-11 - Connected to internal flash - DO NOT USE
    6: ESP32PinInfo(
        gpio=6,
        name="GPIO6",
        flash_connected=True,
        sd_card="CLK",
        warning="DO NOT USE - Connected to internal flash",
        notes="Flash SCK/CLK",
        color_category="flash",
    ),
    7: ESP32PinInfo(
        gpio=7,
        name="GPIO7",
        flash_connected=True,
        sd_card="SD0",
        warning="DO NOT USE - Connected to internal flash",
        notes="Flash SD0/D0",
        color_category="flash",
    ),
    8: ESP32PinInfo(
        gpio=8,
        name="GPIO8",
        flash_connected=True,
        sd_card="SD1",
        warning="DO NOT USE - Connected to internal flash",
        notes="Flash SD1/D1",
        color_category="flash",
    ),
    9: ESP32PinInfo(
        gpio=9,
        name="GPIO9",
        flash_connected=True,
        sd_card="SD2",
        warning="DO NOT USE - Connected to internal flash",
        notes="Flash SD2/D2 (SHD/SD2)",
        color_category="flash",
    ),
    10: ESP32PinInfo(
        gpio=10,
        name="GPIO10",
        flash_connected=True,
        sd_card="SD3",
        warning="DO NOT USE - Connected to internal flash",
        notes="Flash SD3/D3 (SWP/SD3)",
        color_category="flash",
    ),
    11: ESP32PinInfo(
        gpio=11,
        name="GPIO11",
        flash_connected=True,
        sd_card="CMD",
        warning="DO NOT USE - Connected to internal flash",
        notes="Flash CMD (CSC/CMD)",
        color_category="flash",
    ),

    # GPIO12 - Boot strapping (HSPI MISO)
    12: ESP32PinInfo(
        gpio=12,
        name="GPIO12",
        adc2_channel=5,
        touch_channel=5,
        rtc_gpio=15,
        hspi="MISO",
        strapping=True,
        warning="Boot strapping - must be LOW during boot for 3.3V flash",
        notes="MTDI. HSPI MISO. Boot fail if pulled HIGH.",
        color_category="strapping",
    ),

    # GPIO13 - HSPI MOSI
    13: ESP32PinInfo(
        gpio=13,
        name="GPIO13",
        adc2_channel=4,
        touch_channel=4,
        rtc_gpio=14,
        hspi="MOSI",
        notes="MTCK. HSPI MOSI. Safe to use.",
        color_category="spi",
    ),

    # GPIO14 - HSPI CLK
    14: ESP32PinInfo(
        gpio=14,
        name="GPIO14",
        adc2_channel=6,
        touch_channel=6,
        rtc_gpio=16,
        hspi="CLK",
        warning="Outputs PWM at boot",
        notes="MTMS. HSPI CLK.",
        color_category="spi",
    ),

    # GPIO15 - Boot strapping (HSPI CS)
    15: ESP32PinInfo(
        gpio=15,
        name="GPIO15",
        adc2_channel=3,
        touch_channel=3,
        rtc_gpio=13,
        hspi="CS",
        strapping=True,
        warning="Outputs PWM at boot",
        notes="MTDO. HSPI CS0. Silences boot messages if pulled LOW.",
        color_category="strapping",
    ),

    # GPIO16 - UART2 RX
    16: ESP32PinInfo(
        gpio=16,
        name="GPIO16",
        uart2="RX",
        notes="UART2 RX. Safe to use.",
        color_category="uart",
    ),

    # GPIO17 - UART2 TX
    17: ESP32PinInfo(
        gpio=17,
        name="GPIO17",
        uart2="TX",
        notes="UART2 TX. Safe to use.",
        color_category="uart",
    ),

    # GPIO18 - VSPI CLK
    18: ESP32PinInfo(
        gpio=18,
        name="GPIO18",
        vspi="CLK",
        notes="VSPI CLK. Safe to use.",
        color_category="spi",
    ),

    # GPIO19 - VSPI MISO
    19: ESP32PinInfo(
        gpio=19,
        name="GPIO19",
        vspi="MISO",
        notes="VSPI MISO. Safe to use.",
        color_category="spi",
    ),

    # GPIO21 - I2C SDA (default)
    21: ESP32PinInfo(
        gpio=21,
        name="GPIO21",
        i2c="SDA",
        notes="Default I2C SDA. Safe to use.",
        color_category="i2c",
    ),

    # GPIO22 - I2C SCL (default)
    22: ESP32PinInfo(
        gpio=22,
        name="GPIO22",
        i2c="SCL",
        notes="Default I2C SCL. Safe to use.",
        color_category="i2c",
    ),

    # GPIO23 - VSPI MOSI
    23: ESP32PinInfo(
        gpio=23,
        name="GPIO23",
        vspi="MOSI",
        notes="VSPI MOSI. Safe to use.",
        color_category="spi",
    ),

    # GPIO25 - DAC1
    25: ESP32PinInfo(
        gpio=25,
        name="GPIO25",
        adc2_channel=8,
        dac_channel=1,
        rtc_gpio=6,
        notes="DAC1 output. Safe to use.",
        color_category="dac",
    ),

    # GPIO26 - DAC2
    26: ESP32PinInfo(
        gpio=26,
        name="GPIO26",
        adc2_channel=9,
        dac_channel=2,
        rtc_gpio=7,
        notes="DAC2 output. Safe to use.",
        color_category="dac",
    ),

    # GPIO27 - Safe GPIO with ADC/Touch
    27: ESP32PinInfo(
        gpio=27,
        name="GPIO27",
        adc2_channel=7,
        touch_channel=7,
        rtc_gpio=17,
        notes="Safe to use. ADC2 and Touch available.",
        color_category="gpio",
    ),

    # GPIO32 - Safe GPIO with ADC
    32: ESP32PinInfo(
        gpio=32,
        name="GPIO32",
        adc1_channel=4,
        touch_channel=9,
        rtc_gpio=9,
        notes="Safe to use. ADC1 available (works with WiFi).",
        color_category="adc",
    ),

    # GPIO33 - Safe GPIO with ADC
    33: ESP32PinInfo(
        gpio=33,
        name="GPIO33",
        adc1_channel=5,
        touch_channel=8,
        rtc_gpio=8,
        notes="Safe to use. ADC1 available (works with WiFi).",
        color_category="adc",
    ),

    # GPIO34 - Input only
    34: ESP32PinInfo(
        gpio=34,
        name="GPIO34",
        adc1_channel=6,
        rtc_gpio=4,
        input_only=True,
        output=False,
        notes="INPUT ONLY - No internal pullup/pulldown.",
        color_category="input_only",
    ),

    # GPIO35 - Input only
    35: ESP32PinInfo(
        gpio=35,
        name="GPIO35",
        adc1_channel=7,
        rtc_gpio=5,
        input_only=True,
        output=False,
        notes="INPUT ONLY - No internal pullup/pulldown.",
        color_category="input_only",
    ),

    # GPIO36 (VP/SENSOR_VP) - Input only
    36: ESP32PinInfo(
        gpio=36,
        name="GPIO36",
        adc1_channel=0,
        rtc_gpio=0,
        input_only=True,
        output=False,
        notes="INPUT ONLY (SENSOR_VP). No internal pullup/pulldown.",
        color_category="input_only",
    ),

    # GPIO39 (VN/SENSOR_VN) - Input only
    39: ESP32PinInfo(
        gpio=39,
        name="GPIO39",
        adc1_channel=3,
        rtc_gpio=3,
        input_only=True,
        output=False,
        notes="INPUT ONLY (SENSOR_VN). No internal pullup/pulldown.",
        color_category="input_only",
    ),
}


# Color mapping for pin categories (matching pinout reference image)
PIN_CATEGORY_COLORS = {
    "gpio": "#10B981",       # Green - General GPIO
    "power": "#EF4444",      # Red - Power pins
    "ground": "#1F2937",     # Dark gray - Ground
    "flash": "#7C3AED",      # Purple - Flash connected (DO NOT USE)
    "strapping": "#F59E0B",  # Orange/Yellow - Boot strapping
    "adc": "#EC4899",        # Pink - ADC capable
    "dac": "#8B5CF6",        # Purple - DAC
    "touch": "#14B8A6",      # Teal - Touch sensor
    "spi": "#3B82F6",        # Blue - SPI
    "i2c": "#06B6D4",        # Cyan - I2C
    "uart": "#22C55E",       # Green - UART
    "input_only": "#A855F7", # Purple - Input only
}


def get_pin_info(gpio: int) -> Optional[ESP32PinInfo]:
    """Get complete pin information for a GPIO number."""
    return ESP32_PINOUT.get(gpio)


def get_safe_gpios() -> list[int]:
    """Get list of GPIO numbers that are safe to use."""
    return [gpio for gpio, info in ESP32_PINOUT.items() if info.is_safe()]


def get_adc1_gpios() -> list[int]:
    """Get GPIOs with ADC1 (works during WiFi)."""
    return [gpio for gpio, info in ESP32_PINOUT.items() if info.adc1_channel is not None]


def get_adc2_gpios() -> list[int]:
    """Get GPIOs with ADC2 (doesn't work during WiFi)."""
    return [gpio for gpio, info in ESP32_PINOUT.items() if info.adc2_channel is not None]


def get_touch_gpios() -> list[int]:
    """Get GPIOs with touch sensor capability."""
    return [gpio for gpio, info in ESP32_PINOUT.items() if info.touch_channel is not None]


def get_input_only_gpios() -> list[int]:
    """Get GPIOs that are input only."""
    return [gpio for gpio, info in ESP32_PINOUT.items() if info.input_only]


def get_flash_gpios() -> list[int]:
    """Get GPIOs connected to flash (DO NOT USE)."""
    return [gpio for gpio, info in ESP32_PINOUT.items() if info.flash_connected]


def get_strapping_gpios() -> list[int]:
    """Get boot strapping GPIOs."""
    return [gpio for gpio, info in ESP32_PINOUT.items() if info.strapping]

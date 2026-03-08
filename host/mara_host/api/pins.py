# mara_host/api/pins.py
"""
Pin Management API.

Provides programmatic access to GPIO pin configuration,
assignment validation, and pinout information.

Example:
    async with Robot("/dev/ttyUSB0") as robot:
        # List available pins
        pins = robot.pins.list_available()

        # Assign pin to function
        robot.pins.assign(13, "servo_0")

        # Check for conflicts
        conflicts = robot.pins.validate()

        # Get pin info
        info = robot.pins.info(13)
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Dict, Set
from enum import Enum

if TYPE_CHECKING:
    from mara_host.robot import Robot


class PinFunction(Enum):
    """Pin functions."""
    GPIO_INPUT = "gpio_input"
    GPIO_OUTPUT = "gpio_output"
    PWM = "pwm"
    ADC = "adc"
    DAC = "dac"
    I2C_SDA = "i2c_sda"
    I2C_SCL = "i2c_scl"
    SPI_MOSI = "spi_mosi"
    SPI_MISO = "spi_miso"
    SPI_CLK = "spi_clk"
    SPI_CS = "spi_cs"
    UART_TX = "uart_tx"
    UART_RX = "uart_rx"
    ENCODER_A = "encoder_a"
    ENCODER_B = "encoder_b"
    SERVO = "servo"
    MOTOR_PWM = "motor_pwm"
    MOTOR_DIR = "motor_dir"
    ULTRASONIC_TRIG = "ultrasonic_trig"
    ULTRASONIC_ECHO = "ultrasonic_echo"


@dataclass
class PinCapabilities:
    """Capabilities of a single pin."""
    gpio_input: bool = True
    gpio_output: bool = True
    pwm: bool = False
    adc: bool = False
    dac: bool = False
    touch: bool = False
    i2c: bool = False
    spi: bool = False
    uart: bool = False


@dataclass
class PinInfo:
    """Information about a GPIO pin."""
    number: int
    name: str = ""
    capabilities: PinCapabilities = field(default_factory=PinCapabilities)
    assigned_function: Optional[str] = None
    assigned_device: Optional[str] = None
    notes: str = ""


@dataclass
class PinConflict:
    """A pin assignment conflict."""
    pin: int
    devices: List[str]
    message: str


# ESP32 pin definitions
ESP32_PINS: Dict[int, PinInfo] = {
    0: PinInfo(0, "GPIO0", PinCapabilities(pwm=True, adc=True, touch=True),
               notes="Boot mode select, has pull-up"),
    1: PinInfo(1, "TX0", PinCapabilities(uart=True), notes="UART0 TX"),
    2: PinInfo(2, "GPIO2", PinCapabilities(pwm=True, adc=True, touch=True),
               notes="On-board LED on many boards"),
    3: PinInfo(3, "RX0", PinCapabilities(uart=True), notes="UART0 RX"),
    4: PinInfo(4, "GPIO4", PinCapabilities(pwm=True, adc=True, touch=True)),
    5: PinInfo(5, "GPIO5", PinCapabilities(pwm=True, spi=True),
               notes="VSPI CS0"),
    12: PinInfo(12, "GPIO12", PinCapabilities(pwm=True, adc=True, touch=True),
                notes="Boot fail if high"),
    13: PinInfo(13, "GPIO13", PinCapabilities(pwm=True, adc=True, touch=True)),
    14: PinInfo(14, "GPIO14", PinCapabilities(pwm=True, adc=True, touch=True)),
    15: PinInfo(15, "GPIO15", PinCapabilities(pwm=True, adc=True, touch=True)),
    16: PinInfo(16, "GPIO16", PinCapabilities(pwm=True)),
    17: PinInfo(17, "GPIO17", PinCapabilities(pwm=True)),
    18: PinInfo(18, "GPIO18", PinCapabilities(pwm=True, spi=True),
                notes="VSPI CLK"),
    19: PinInfo(19, "GPIO19", PinCapabilities(pwm=True, spi=True),
                notes="VSPI MISO"),
    21: PinInfo(21, "GPIO21", PinCapabilities(pwm=True, i2c=True),
                notes="I2C SDA"),
    22: PinInfo(22, "GPIO22", PinCapabilities(pwm=True, i2c=True),
                notes="I2C SCL"),
    23: PinInfo(23, "GPIO23", PinCapabilities(pwm=True, spi=True),
                notes="VSPI MOSI"),
    25: PinInfo(25, "GPIO25", PinCapabilities(pwm=True, adc=True, dac=True)),
    26: PinInfo(26, "GPIO26", PinCapabilities(pwm=True, adc=True, dac=True)),
    27: PinInfo(27, "GPIO27", PinCapabilities(pwm=True, adc=True, touch=True)),
    32: PinInfo(32, "GPIO32", PinCapabilities(adc=True, touch=True)),
    33: PinInfo(33, "GPIO33", PinCapabilities(adc=True, touch=True)),
    34: PinInfo(34, "GPIO34", PinCapabilities(gpio_output=False, adc=True),
                notes="Input only"),
    35: PinInfo(35, "GPIO35", PinCapabilities(gpio_output=False, adc=True),
                notes="Input only"),
    36: PinInfo(36, "VP", PinCapabilities(gpio_output=False, adc=True),
                notes="Input only, ADC1_CH0"),
    39: PinInfo(39, "VN", PinCapabilities(gpio_output=False, adc=True),
                notes="Input only, ADC1_CH3"),
}


class Pins:
    """
    Pin management interface.

    Provides:
    - Pin capability queries
    - Assignment tracking
    - Conflict detection
    - Pinout information

    Usage:
        pins = robot.pins
        pins.assign(13, "servo_0", PinFunction.SERVO)
        conflicts = pins.validate()
    """

    def __init__(self, robot: "Robot") -> None:
        self._robot = robot
        self._pins = {k: PinInfo(v.number, v.name, v.capabilities, notes=v.notes)
                      for k, v in ESP32_PINS.items()}
        self._assignments: Dict[int, tuple[str, PinFunction]] = {}

    def list_all(self) -> List[PinInfo]:
        """List all pins."""
        return list(self._pins.values())

    def list_available(self, function: Optional[PinFunction] = None) -> List[PinInfo]:
        """
        List available (unassigned) pins.

        Args:
            function: Filter by capability (e.g., PWM-capable pins)

        Returns:
            List of available PinInfo
        """
        available = []
        for pin_num, pin in self._pins.items():
            if pin.assigned_function is not None:
                continue

            if function is None:
                available.append(pin)
            elif function == PinFunction.PWM and pin.capabilities.pwm:
                available.append(pin)
            elif function == PinFunction.ADC and pin.capabilities.adc:
                available.append(pin)
            elif function in (PinFunction.GPIO_INPUT, PinFunction.GPIO_OUTPUT):
                available.append(pin)

        return available

    def info(self, pin_number: int) -> Optional[PinInfo]:
        """Get information about a pin."""
        return self._pins.get(pin_number)

    def assign(
        self,
        pin_number: int,
        device: str,
        function: PinFunction = PinFunction.GPIO_OUTPUT,
    ) -> bool:
        """
        Assign a pin to a device/function.

        Args:
            pin_number: GPIO pin number
            device: Device identifier (e.g., "servo_0", "motor_left")
            function: Pin function

        Returns:
            True if assignment succeeded
        """
        if pin_number not in self._pins:
            return False

        pin = self._pins[pin_number]
        pin.assigned_function = function.value
        pin.assigned_device = device
        self._assignments[pin_number] = (device, function)
        return True

    def unassign(self, pin_number: int) -> bool:
        """
        Remove pin assignment.

        Args:
            pin_number: GPIO pin number

        Returns:
            True if pin was assigned
        """
        if pin_number not in self._pins:
            return False

        pin = self._pins[pin_number]
        was_assigned = pin.assigned_function is not None

        pin.assigned_function = None
        pin.assigned_device = None
        self._assignments.pop(pin_number, None)

        return was_assigned

    def validate(self) -> List[PinConflict]:
        """
        Check for pin conflicts.

        Returns:
            List of conflicts found
        """
        conflicts = []

        # Check for duplicate assignments
        device_pins: Dict[str, List[int]] = {}
        for pin_num, (device, _) in self._assignments.items():
            if device not in device_pins:
                device_pins[device] = []
            device_pins[device].append(pin_num)

        # Check for boot-sensitive pins
        boot_pins = {0, 2, 12, 15}
        for pin_num in self._assignments:
            if pin_num in boot_pins:
                conflicts.append(PinConflict(
                    pin=pin_num,
                    devices=[self._assignments[pin_num][0]],
                    message=f"Pin {pin_num} affects boot mode",
                ))

        # Check for input-only pins used as output
        input_only = {34, 35, 36, 39}
        for pin_num, (device, function) in self._assignments.items():
            if pin_num in input_only and function in (
                PinFunction.GPIO_OUTPUT, PinFunction.PWM, PinFunction.SERVO
            ):
                conflicts.append(PinConflict(
                    pin=pin_num,
                    devices=[device],
                    message=f"Pin {pin_num} is input-only, cannot use for {function.value}",
                ))

        return conflicts

    def get_assignments(self) -> Dict[int, tuple[str, str]]:
        """
        Get all pin assignments.

        Returns:
            Dict of pin_number -> (device, function)
        """
        return {
            pin: (device, func.value)
            for pin, (device, func) in self._assignments.items()
        }

    def suggest(self, device_type: str, count: int = 1) -> List[int]:
        """
        Suggest pins for a device type.

        Args:
            device_type: Type of device ("servo", "motor", "encoder", etc.)
            count: Number of pins needed

        Returns:
            List of suggested pin numbers
        """
        suggestions = []

        if device_type == "servo":
            # PWM-capable pins, prefer 13, 14, 15
            preferred = [13, 14, 15, 16, 17, 18, 19]
        elif device_type == "motor":
            # PWM for speed, any for direction
            preferred = [25, 26, 27, 32, 33]
        elif device_type == "encoder":
            # Input-capable, interrupt-capable
            preferred = [34, 35, 36, 39, 32, 33]
        elif device_type == "ultrasonic":
            # Trig (output) + echo (input)
            preferred = [12, 14, 27, 26]
        else:
            preferred = list(self._pins.keys())

        for pin in preferred:
            if pin in self._pins and self._pins[pin].assigned_function is None:
                suggestions.append(pin)
                if len(suggestions) >= count:
                    break

        return suggestions

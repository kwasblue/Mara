# mara_host/services/pins/groups.py
"""Pin group templates for common configurations."""

from mara_host.tools.pins import Capability


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

# mara_host/services/pins/recommendations.py
"""Pin recommendation logic."""

from mara_host.tools.pins import (
    ESP32_PINS,
    SAFE_PINS,
    INPUT_ONLY_PINS,
    BOOT_PINS,
    Capability,
)
from .models import PinRecommendation, GroupRecommendation
from .groups import PIN_GROUPS


# Use case to capability mapping
USE_CASE_CAPS = {
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


def suggest_pins(
    use_case: str,
    assigned: set[int],
    count: int = 5
) -> list[PinRecommendation]:
    """
    Suggest best pins for a use case.

    Args:
        use_case: One of "pwm", "adc", "input", "output", "i2c", "spi", "uart", "touch"
        assigned: Set of already-assigned GPIO numbers
        count: Number of recommendations to return

    Returns:
        List of pin recommendations, best first.
    """
    recommendations = []
    required = USE_CASE_CAPS.get(use_case.lower(), Capability.INPUT | Capability.OUTPUT)

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


def recommend_group_pins(
    group_type: str,
    prefix: str,
    assigned: set[int],
) -> GroupRecommendation:
    """
    Recommend pins for a group configuration.

    Args:
        group_type: Key from PIN_GROUPS dict
        prefix: Prefix for pin names
        assigned: Set of already-assigned GPIO numbers

    Returns:
        GroupRecommendation with suggested_assignments.
    """
    group = PIN_GROUPS.get(group_type)
    if not group:
        return GroupRecommendation(
            suggested_assignments={},
            warnings=[f"Unknown group type: {group_type}"]
        )

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
        candidates = suggest_pins(
            use_case=_cap_to_use_case(required_cap),
            assigned=assigned | used_gpios,
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


def _cap_to_use_case(cap: Capability) -> str:
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


# Use case notes for informational purposes
USE_CASE_NOTES = {
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


def get_use_case_notes(use_case: str) -> list[str]:
    """
    Get informational notes for a use case.

    Args:
        use_case: One of "pwm", "adc", "input", "output", "i2c", etc.

    Returns:
        List of helpful notes/tips for the use case.
    """
    return USE_CASE_NOTES.get(use_case.lower(), [])

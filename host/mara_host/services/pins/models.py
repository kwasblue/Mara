# mara_host/services/pins/models.py
"""Pin service data models."""

from dataclasses import dataclass, field


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

# schema/control/core.py
"""
Core dataclasses for control block definitions.

Provides typed definitions for controllers, observers, filters, and signal blocks
that are used for GUI generation, firmware mapping, and state-space derivation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence


@dataclass(frozen=True)
class PortDef:
    """Definition of an input or output port on a control block."""

    id: str  # Internal ID (e.g., "ref", "meas", "out")
    label: str  # Display label (e.g., "REF", "MEAS", "OUT")
    description: str = ""  # Tooltip description


@dataclass(frozen=True)
class GuiConfig:
    """GUI appearance configuration for a control block."""

    label: str  # Display name
    color: str  # CSS color (e.g., "#3B82F6")
    description: str = ""  # Block description/tooltip
    inputs: tuple[PortDef, ...] = ()
    outputs: tuple[PortDef, ...] = ()
    width: int = 80
    height: int = 60
    shape: Literal["rectangle", "circle", "triangle"] = "rectangle"

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        return {
            "label": self.label,
            "color": self.color,
            "description": self.description,
            "inputs": [(p.id, p.label, p.description) for p in self.inputs],
            "outputs": [(p.id, p.label, p.description) for p in self.outputs],
            "width": self.width,
            "height": self.height,
            "shape": self.shape,
        }


@dataclass(frozen=True)
class ParameterDef:
    """Definition of a configurable parameter on a control block."""

    name: str
    type: Literal["int", "float", "string", "matrix", "list"]
    default: Any = None
    range: tuple[float, float] | None = None  # (min, max)
    unit: str = ""
    description: str = ""
    options: tuple[str, ...] | None = None  # For string enum types

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        d: dict[str, Any] = {
            "type": self.type,
            "default": self.default if self.default is not None else ([] if self.type in ("matrix", "list") else 0),
        }
        if self.range:
            d["range"] = list(self.range)
        if self.unit:
            d["unit"] = self.unit
        if self.description:
            d["description"] = self.description
        if self.options:
            d["options"] = list(self.options)
        return d


@dataclass(frozen=True)
class FirmwareConfig:
    """Firmware mapping configuration for a control block."""

    slot_type: str | None  # "CONTROLLER", "OBSERVER", "SIGNAL_BUS", None
    maps_to: str | Sequence[str] | None  # Firmware implementation type
    max_slots: int | None = None
    feature_flag: str | None = None  # Optional feature flag requirement
    uses_slots: int = 1  # Number of slots used
    uses_controller_slot: bool = False
    uses_observer_slot: bool = False
    note: str | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        d: dict[str, Any] = {
            "slot_type": self.slot_type,
            "maps_to": list(self.maps_to) if isinstance(self.maps_to, (list, tuple)) else self.maps_to,
        }
        if self.max_slots:
            d["max_slots"] = self.max_slots
        if self.feature_flag:
            d["feature_flag"] = self.feature_flag
        if self.uses_slots != 1:
            d["uses_slots"] = self.uses_slots
        if self.uses_controller_slot:
            d["uses_controller_slot"] = True
        if self.uses_observer_slot:
            d["uses_observer_slot"] = True
        if self.note:
            d["note"] = self.note
        if self.warning:
            d["warning"] = self.warning
        return d


@dataclass(frozen=True)
class StateSpaceConfig:
    """State-space derivation configuration for a control block."""

    description: str = ""
    derive_fn: str | None = None  # Function name for deriving state-space matrices
    # Optional pre-defined matrices (for simple blocks)
    A: tuple[float, ...] | None = None
    B: tuple[float, ...] | None = None
    A_expr: str | None = None  # Expression referencing parameters
    B_expr: str | None = None
    C_expr: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        d: dict[str, Any] = {"description": self.description}
        if self.derive_fn:
            d["derive_fn"] = self.derive_fn
        if self.A:
            d["A"] = list(self.A)
        if self.B:
            d["B"] = list(self.B)
        if self.A_expr:
            d["A_expr"] = self.A_expr
        if self.B_expr:
            d["B_expr"] = self.B_expr
        if self.C_expr:
            d["C_expr"] = self.C_expr
        return d


@dataclass(frozen=True)
class ControlBlockDef:
    """
    Definition of a control block (controller, observer, filter, or signal).

    Attributes:
        name: Unique block type identifier (e.g., "pid", "kalman", "filter")
        category: Block category ("controller", "observer", "filter", "signal")
        gui: GUI appearance configuration
        parameters: Dict of parameter definitions
        firmware: Firmware mapping configuration
        state_space: Optional state-space derivation config
    """

    name: str
    category: Literal["controller", "observer", "filter", "signal"]
    gui: GuiConfig
    parameters: Mapping[str, ParameterDef] = field(default_factory=dict)
    firmware: FirmwareConfig | None = None
    state_space: StateSpaceConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format for backward compatibility."""
        d: dict[str, Any] = {
            "category": self.category,
            "gui": self.gui.to_dict(),
            "parameters": {name: param.to_dict() for name, param in self.parameters.items()},
        }
        if self.firmware:
            d["firmware"] = self.firmware.to_dict()
        if self.state_space:
            d["state_space"] = self.state_space.to_dict()
        else:
            d["state_space"] = None
        return d


# Helper functions for creating PortDefs from legacy tuples
def port(id: str, label: str, description: str = "") -> PortDef:
    """Create a PortDef from components."""
    return PortDef(id=id, label=label, description=description)


def ports_from_legacy(legacy: list[tuple[str, str, str]] | list) -> tuple[PortDef, ...]:
    """Convert legacy port tuples to PortDefs."""
    return tuple(PortDef(id=p[0], label=p[1], description=p[2] if len(p) > 2 else "") for p in legacy)


__all__ = [
    "PortDef",
    "GuiConfig",
    "ParameterDef",
    "FirmwareConfig",
    "StateSpaceConfig",
    "ControlBlockDef",
    "port",
    "ports_from_legacy",
]

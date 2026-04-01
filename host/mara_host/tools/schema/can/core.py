# schema/can/core.py
"""
Core typed dataclass definitions for CAN bus messages.

CAN messages are 8-byte frames for hybrid real-time/protocol transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


# Type mappings (same as binary)
TYPE_INFO = {
    "u8": {"cpp": "uint8_t", "py_struct": "B", "size": 1},
    "u16": {"cpp": "uint16_t", "py_struct": "H", "size": 2},
    "u32": {"cpp": "uint32_t", "py_struct": "I", "size": 4},
    "i8": {"cpp": "int8_t", "py_struct": "b", "size": 1},
    "i16": {"cpp": "int16_t", "py_struct": "h", "size": 2},
    "i32": {"cpp": "int32_t", "py_struct": "i", "size": 4},
    "f32": {"cpp": "float", "py_struct": "f", "size": 4},
}


@dataclass(frozen=True)
class CanFieldDef:
    """
    Definition of a field in a CAN message struct.

    Attributes:
        name: Field name
        type: Field type (u8, u16, u32, i8, i16, i32, f32)
        scale: Scale factor for physical value
        unit: Physical unit (e.g., "m/s", "mg", "ms")
    """
    name: str
    type: str
    scale: float = 1.0
    unit: str = ""

    def __post_init__(self) -> None:
        if self.type not in TYPE_INFO:
            raise ValueError(f"Unknown type: {self.type}")

    @property
    def cpp_type(self) -> str:
        return TYPE_INFO[self.type]["cpp"]

    @property
    def py_struct(self) -> str:
        return TYPE_INFO[self.type]["py_struct"]

    @property
    def size(self) -> int:
        return TYPE_INFO[self.type]["size"]

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name, "type": self.type}
        if self.scale != 1.0:
            result["scale"] = self.scale
        if self.unit:
            result["unit"] = self.unit
        return result

    @classmethod
    def u8(cls, name: str, unit: str = "") -> "CanFieldDef":
        return cls(name, "u8", 1.0, unit)

    @classmethod
    def u16(cls, name: str, scale: float = 1.0, unit: str = "") -> "CanFieldDef":
        return cls(name, "u16", scale, unit)

    @classmethod
    def u32(cls, name: str, scale: float = 1.0, unit: str = "") -> "CanFieldDef":
        return cls(name, "u32", scale, unit)

    @classmethod
    def i8(cls, name: str, unit: str = "") -> "CanFieldDef":
        return cls(name, "i8", 1.0, unit)

    @classmethod
    def i16(cls, name: str, scale: float = 1.0, unit: str = "") -> "CanFieldDef":
        return cls(name, "i16", scale, unit)

    @classmethod
    def i32(cls, name: str, scale: float = 1.0, unit: str = "") -> "CanFieldDef":
        return cls(name, "i32", scale, unit)

    @classmethod
    def f32(cls, name: str, unit: str = "") -> "CanFieldDef":
        return cls(name, "f32", 1.0, unit)


@dataclass(frozen=True)
class CanMessageDef:
    """
    Definition of a CAN message.

    Attributes:
        name: Message name (e.g., "SET_VEL", "ENCODER")
        base_id: Base message ID name (e.g., "SET_VEL_BASE")
        direction: Message direction ("host->mcu", "mcu->host", "both")
        description: Human-readable description
        struct: Tuple of field definitions (max 8 bytes total)
    """
    name: str
    base_id: str
    direction: str  # host->mcu | mcu->host | both
    description: str
    struct: Tuple[CanFieldDef, ...]

    def __post_init__(self) -> None:
        if self.direction not in ("host->mcu", "mcu->host", "both"):
            raise ValueError(f"Invalid direction: {self.direction}")
        total_size = sum(f.size for f in self.struct)
        if total_size > 8:
            raise ValueError(f"CAN message struct exceeds 8 bytes: {total_size}")

    @property
    def struct_size(self) -> int:
        """Total size of struct in bytes."""
        return sum(f.size for f in self.struct)

    @property
    def struct_format(self) -> str:
        """Python struct format string."""
        return "<" + "".join(f.py_struct for f in self.struct)

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to legacy CAN_MESSAGES dict format."""
        return {
            "base_id": self.base_id,
            "direction": self.direction,
            "description": self.description,
            "struct": [f.to_dict() for f in self.struct],
        }


__all__ = ["CanFieldDef", "CanMessageDef", "TYPE_INFO"]

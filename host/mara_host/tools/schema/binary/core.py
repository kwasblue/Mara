# schema/binary/core.py
"""
Core typed dataclass definitions for binary commands.

Binary commands are compact fixed-format messages for high-rate control loops.
Use JSON commands for setup/config, binary for real-time streaming (50+ Hz).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Tuple


# Type mappings
TYPE_INFO = {
    "u8": {"cpp": "uint8_t", "py_struct": "B", "size": 1, "py_type": "int"},
    "u16": {"cpp": "uint16_t", "py_struct": "H", "size": 2, "py_type": "int"},
    "u32": {"cpp": "uint32_t", "py_struct": "I", "size": 4, "py_type": "int"},
    "i8": {"cpp": "int8_t", "py_struct": "b", "size": 1, "py_type": "int"},
    "i16": {"cpp": "int16_t", "py_struct": "h", "size": 2, "py_type": "int"},
    "i32": {"cpp": "int32_t", "py_struct": "i", "size": 4, "py_type": "int"},
    "f32": {"cpp": "float", "py_struct": "f", "size": 4, "py_type": "float"},
}


@dataclass(frozen=True)
class BinaryFieldDef:
    """
    Definition of a field in a binary command payload.

    Attributes:
        name: Field name
        type: Field type (u8, u16, u32, i8, i16, i32, f32)
        description: Human-readable description
    """
    name: str
    type: str  # u8 | u16 | u32 | i8 | i16 | i32 | f32
    description: str = ""

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

    @property
    def py_type(self) -> str:
        return TYPE_INFO[self.type]["py_type"]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type}

    @classmethod
    def u8(cls, name: str, description: str = "") -> "BinaryFieldDef":
        return cls(name, "u8", description)

    @classmethod
    def u16(cls, name: str, description: str = "") -> "BinaryFieldDef":
        return cls(name, "u16", description)

    @classmethod
    def u32(cls, name: str, description: str = "") -> "BinaryFieldDef":
        return cls(name, "u32", description)

    @classmethod
    def i8(cls, name: str, description: str = "") -> "BinaryFieldDef":
        return cls(name, "i8", description)

    @classmethod
    def i16(cls, name: str, description: str = "") -> "BinaryFieldDef":
        return cls(name, "i16", description)

    @classmethod
    def i32(cls, name: str, description: str = "") -> "BinaryFieldDef":
        return cls(name, "i32", description)

    @classmethod
    def f32(cls, name: str, description: str = "") -> "BinaryFieldDef":
        return cls(name, "f32", description)


@dataclass(frozen=True)
class BinaryCommandDef:
    """
    Definition of a binary command.

    Attributes:
        name: Command name (e.g., "SET_VEL")
        opcode: Binary opcode (0x00-0xFF)
        description: Human-readable description
        payload: Tuple of payload field definitions
        json_cmd: Corresponding JSON command name (if any)
        variable_length: Whether command has variable-length payload
        variable_item: Fields for each variable-length item
    """
    name: str
    opcode: int
    description: str
    payload: Tuple[BinaryFieldDef, ...] = ()
    json_cmd: str | None = None
    variable_length: bool = False
    variable_item: Tuple[BinaryFieldDef, ...] = ()

    def __post_init__(self) -> None:
        if not 0x00 <= self.opcode <= 0xFF:
            raise ValueError(f"opcode must be 0x00-0xFF, got 0x{self.opcode:02X}")

    @property
    def payload_size(self) -> int:
        """Fixed payload size in bytes (excluding opcode)."""
        return sum(f.size for f in self.payload)

    @property
    def struct_format(self) -> str:
        """Python struct format string (including opcode)."""
        fmt = "<B"  # Little-endian, opcode byte
        for f in self.payload:
            fmt += f.py_struct
        return fmt

    @property
    def pascal_case_name(self) -> str:
        """Convert name to PascalCase: SET_VEL -> SetVel"""
        return "".join(word.capitalize() for word in self.name.split("_"))

    @property
    def snake_case_name(self) -> str:
        """Convert name to snake_case: SET_VEL -> set_vel"""
        return self.name.lower()

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to legacy BINARY_COMMANDS dict format."""
        result: dict[str, Any] = {
            "opcode": self.opcode,
            "description": self.description,
            "payload": [f.to_dict() for f in self.payload],
        }
        if self.json_cmd:
            result["json_cmd"] = self.json_cmd
        else:
            result["json_cmd"] = None
        if self.variable_length:
            result["variable_length"] = True
            result["variable_item"] = [f.to_dict() for f in self.variable_item]
        return result


__all__ = ["BinaryFieldDef", "BinaryCommandDef", "TYPE_INFO"]

# schema/telemetry/core.py
"""
Core types for telemetry section definitions.

TelemetrySectionDef defines a telemetry section with its ID, fields, and
parsing logic. FieldDef defines individual fields within a section.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple, Union


@dataclass(frozen=True)
class FieldDef:
    """Definition of a single field in a telemetry section."""

    name: str
    fmt: str  # struct format char (e.g., 'B', 'H', 'i', 'f')
    size: int
    scale: float = 1.0  # Multiply raw value by this
    offset: float = 0.0  # Add this after scaling
    description: str = ""

    @classmethod
    def uint8(cls, name: str, scale: float = 1.0, description: str = "") -> "FieldDef":
        return cls(name, "B", 1, scale, 0.0, description)

    @classmethod
    def int8(cls, name: str, scale: float = 1.0, description: str = "") -> "FieldDef":
        return cls(name, "b", 1, scale, 0.0, description)

    @classmethod
    def uint16(cls, name: str, scale: float = 1.0, description: str = "") -> "FieldDef":
        return cls(name, "H", 2, scale, 0.0, description)

    @classmethod
    def int16(cls, name: str, scale: float = 1.0, description: str = "") -> "FieldDef":
        return cls(name, "h", 2, scale, 0.0, description)

    @classmethod
    def uint32(cls, name: str, scale: float = 1.0, description: str = "") -> "FieldDef":
        return cls(name, "I", 4, scale, 0.0, description)

    @classmethod
    def int32(cls, name: str, scale: float = 1.0, description: str = "") -> "FieldDef":
        return cls(name, "i", 4, scale, 0.0, description)

    @classmethod
    def float32(cls, name: str, scale: float = 1.0, description: str = "") -> "FieldDef":
        return cls(name, "f", 4, scale, 0.0, description)

    @classmethod
    def bool_field(cls, name: str, description: str = "") -> "FieldDef":
        """Boolean encoded as uint8 (0 or 1)."""
        return cls(name, "B", 1, 1.0, 0.0, description)


@dataclass
class TelemetrySectionDef:
    """
    Definition of a telemetry section.

    Attributes:
        name: Section name (e.g., "TELEM_IMU")
        section_id: Unique section ID (0x01-0xFF)
        description: Human-readable description
        fields: Tuple of FieldDef objects defining the binary format
        variable_length: If True, section has variable length (requires custom parser)
        custom_parser: Optional custom parser function for complex sections
        model_class: Optional dataclass to use for parsed data
    """

    name: str
    section_id: int
    description: str
    fields: Tuple[FieldDef, ...] = field(default_factory=tuple)
    variable_length: bool = False
    custom_parser: Optional[Callable[[bytes, int], dict]] = None
    model_class: Optional[type] = None

    def __post_init__(self):
        # Build struct format from fields
        if self.fields and not self.variable_length:
            fmt = "<" + "".join(f.fmt for f in self.fields)
            self._struct = struct.Struct(fmt)
            self._size = self._struct.size
        else:
            self._struct = None
            self._size = None

    @property
    def size(self) -> Optional[int]:
        """Fixed size in bytes, or None for variable-length sections."""
        return self._size

    @property
    def struct_format(self) -> Optional[struct.Struct]:
        """Pre-compiled struct for parsing, or None for variable-length."""
        return self._struct

    def parse(self, body: bytes, ts_ms: int) -> Optional[dict]:
        """
        Parse binary data into a dictionary.

        Args:
            body: Raw section body bytes
            ts_ms: Timestamp from packet header

        Returns:
            Dictionary with parsed fields, or None on error
        """
        # Use custom parser if provided
        if self.custom_parser is not None:
            return self.custom_parser(body, ts_ms)

        # Variable-length sections require custom parser
        if self.variable_length:
            return None

        # Check size
        if self._struct is None or len(body) < self._struct.size:
            return None

        # Unpack and apply scaling
        values = self._struct.unpack_from(body, 0)
        result = {"ts_ms": ts_ms}

        for i, field_def in enumerate(self.fields):
            raw_value = values[i]
            # Apply scale and offset
            if field_def.scale != 1.0 or field_def.offset != 0.0:
                scaled = raw_value * field_def.scale + field_def.offset
            else:
                scaled = raw_value
            # Handle bool fields
            if field_def.fmt == "B" and field_def.scale == 1.0 and field_def.name.startswith(("is_", "has_", "ok", "online", "attached", "enabled", "moving")):
                scaled = bool(raw_value)
            result[field_def.name] = scaled

        return result

    def to_legacy_dict(self) -> dict:
        """Convert to legacy TELEMETRY_SECTIONS dict format."""
        fmt_parts = []
        for f in self.fields:
            type_map = {
                "B": "u8", "b": "i8",
                "H": "u16", "h": "i16",
                "I": "u32", "i": "i32",
                "f": "f32",
            }
            fmt_parts.append(f"{f.name}({type_map.get(f.fmt, f.fmt)})")

        return {
            "id": self.section_id,
            "description": self.description,
            "format": " ".join(fmt_parts),
            "size": self._size,
        }


__all__ = ["TelemetrySectionDef", "FieldDef"]

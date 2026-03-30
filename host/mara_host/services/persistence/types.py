"""
Typed persistence record classes.

These dataclasses replace nested dicts for persistence records, providing
type safety, IDE autocomplete, and clearer code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CalibrationRecord:
    """A calibration record for a subsystem."""

    name: str
    calibration_type: str
    saved_at: float
    values: dict[str, Any]

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> CalibrationRecord:
        """Parse from stored dict format."""
        return cls(
            name=name,
            calibration_type=data.get("type", "generic"),
            saved_at=data.get("saved_at", 0.0),
            values=data.get("values", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to storable dict format."""
        return {
            "type": self.calibration_type,
            "saved_at": self.saved_at,
            "values": self.values,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticRecord:
    """A diagnostic snapshot record."""

    name: str
    captured_at: float
    details: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiagnosticRecord:
        """Parse from stored dict format."""
        return cls(
            name=data.get("name", ""),
            captured_at=data.get("captured_at", 0.0),
            details=data.get("details", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to storable dict format."""
        return {
            "name": self.name,
            "captured_at": self.captured_at,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class ControlGraphPayload:
    """A stored control graph configuration."""

    version: int
    saved_at: float
    source: str
    graph: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ControlGraphPayload:
        """Parse from stored dict format."""
        return cls(
            version=data.get("version", 1),
            saved_at=data.get("saved_at", 0.0),
            source=data.get("source", "unknown"),
            graph=data.get("graph", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to storable dict format."""
        return {
            "kind": "control_graph",
            "version": self.version,
            "saved_at": self.saved_at,
            "source": self.source,
            "graph": self.graph,
        }


@dataclass(slots=True)
class CalibrationData:
    """In-memory representation of all calibration data."""

    version: int = 1
    records: dict[str, CalibrationRecord] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationData:
        """Parse from stored dict format."""
        records = {}
        for name, record_data in data.get("records", {}).items():
            records[name] = CalibrationRecord.from_dict(name, record_data)
        return cls(
            version=data.get("version", 1),
            records=records,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to storable dict format."""
        return {
            "kind": "calibrations",
            "version": self.version,
            "records": {name: record.to_dict() for name, record in self.records.items()},
        }

    def get(self, name: str) -> CalibrationRecord | None:
        """Get a calibration record by name."""
        return self.records.get(name)

    def set(self, record: CalibrationRecord) -> None:
        """Set a calibration record."""
        self.records[record.name] = record


@dataclass(slots=True)
class DiagnosticData:
    """In-memory representation of all diagnostic data."""

    version: int = 1
    records: list[DiagnosticRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiagnosticData:
        """Parse from stored dict format."""
        records = [
            DiagnosticRecord.from_dict(r)
            for r in data.get("records", [])
        ]
        return cls(
            version=data.get("version", 1),
            records=records,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to storable dict format."""
        return {
            "kind": "diagnostics",
            "version": self.version,
            "records": [r.to_dict() for r in self.records],
        }

    def append(self, record: DiagnosticRecord) -> None:
        """Append a diagnostic record."""
        self.records.append(record)


__all__ = [
    "CalibrationRecord",
    "DiagnosticRecord",
    "ControlGraphPayload",
    "CalibrationData",
    "DiagnosticData",
]

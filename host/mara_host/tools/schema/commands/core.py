"""Typed command-schema objects with legacy dict export helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, TypeAlias


class _UnsetType:
    pass


UNSET = _UnsetType()


SchemaLike: TypeAlias = "FieldDef | Mapping[str, Any]"
SchemaFieldMap: TypeAlias = Mapping[str, SchemaLike]


def _serialize_schema_like(spec: SchemaLike) -> dict[str, Any]:
    if isinstance(spec, FieldDef):
        return spec.to_dict()

    if "type" not in spec:
        return {name: _serialize_schema_like(item) for name, item in spec.items()}

    data = dict(spec)

    if "items" in data and data["items"] is not None:
        items = data["items"]
        if isinstance(items, Mapping):
            data["items"] = _serialize_schema_like(items)

    if "properties" in data and data["properties"] is not None:
        properties = data["properties"]
        if isinstance(properties, Mapping):
            data["properties"] = {
                name: _serialize_schema_like(item)
                for name, item in properties.items()
            }

    return data


@dataclass(frozen=True)
class FieldDef:
    type: str
    required: bool = False
    description: str | None = None
    default: Any = UNSET
    enum: tuple[Any, ...] = ()
    minimum: int | float | None = None
    maximum: int | float | None = None
    items: SchemaLike | None = None
    properties: SchemaFieldMap | None = None
    units: str | None = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type}
        if self.required:
            data["required"] = True
        if self.description:
            data["description"] = self.description
        if self.default is not UNSET:
            data["default"] = self.default
        if self.enum:
            data["enum"] = list(self.enum)
        if self.minimum is not None:
            data["min"] = self.minimum
        if self.maximum is not None:
            data["max"] = self.maximum
        if self.items is not None:
            data["items"] = _serialize_schema_like(self.items)
        if self.properties:
            data["properties"] = {
                name: _serialize_schema_like(field)
                for name, field in self.properties.items()
            }
        if self.units:
            data["units"] = self.units
        data.update(self.extras)
        return data


@dataclass(frozen=True)
class CommandDef:
    kind: str
    direction: str
    description: str
    payload: SchemaFieldMap = field(default_factory=dict)
    timeout_s: float | None = None
    response: SchemaFieldMap | None = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "kind": self.kind,
            "direction": self.direction,
            "description": self.description,
            "payload": {name: _serialize_schema_like(field) for name, field in self.payload.items()},
        }
        if self.timeout_s is not None:
            data["timeout_s"] = self.timeout_s
        if self.response:
            data["response"] = {
                name: _serialize_schema_like(field)
                for name, field in self.response.items()
            }
        data.update(self.extras)
        return data


CommandDefMap = dict[str, CommandDef]
LegacyCommandMap = dict[str, dict[str, Any]]


def export_command_dicts(commands: Mapping[str, CommandDef]) -> LegacyCommandMap:
    return {name: spec.to_dict() for name, spec in commands.items()}

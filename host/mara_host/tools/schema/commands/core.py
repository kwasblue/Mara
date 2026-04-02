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
    # Code generation fields
    category: str | None = None  # Service category (e.g., "motor", "servo"). Auto-derived from CMD_ prefix if None.
    requires_arm: bool = True  # Whether tool requires armed state
    method_name: str | None = None  # Override for generated service method name
    # MCP Tool generation fields
    tool_name: str | None = None  # Override tool name (default: category_method)
    tool_description: str | None = None  # Override tool description (default: command description)
    response_format: str | None = None  # Response format template (e.g., "Servo {servo_id} -> {angle}deg")
    service_name: str | None = None  # Override service name (default: {category}_service)
    skip_tool: bool = False  # Don't generate a tool for this command
    param_overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)  # Per-param overrides

    def get_category(self, cmd_name: str) -> str:
        """Get category, deriving from command name if not explicit."""
        if self.category:
            return self.category
        # Derive from CMD_CATEGORY_ACTION pattern
        # e.g., CMD_DC_SET_SPEED -> "dc", CMD_SERVO_ATTACH -> "servo"
        parts = cmd_name.removeprefix("CMD_").lower().split("_")
        if len(parts) >= 2:
            return parts[0]
        return "misc"

    def get_method_name(self, cmd_name: str) -> str:
        """Get method name, deriving from command name if not explicit."""
        if self.method_name:
            return self.method_name
        # Derive from CMD_CATEGORY_ACTION pattern
        # e.g., CMD_DC_SET_SPEED -> "set_speed", CMD_SERVO_ATTACH -> "attach"
        parts = cmd_name.removeprefix("CMD_").lower().split("_")
        if len(parts) >= 2:
            return "_".join(parts[1:])
        return parts[0]

    def get_tool_name(self, cmd_name: str) -> str:
        """Get tool name, deriving from category + method if not explicit."""
        if self.tool_name:
            return self.tool_name
        category = self.get_category(cmd_name)
        method = self.get_method_name(cmd_name)
        return f"{category}_{method}"

    def get_service_name(self, cmd_name: str) -> str:
        """Get service name, deriving from category if not explicit."""
        if self.service_name:
            return self.service_name
        category = self.get_category(cmd_name)
        return f"{category}_service"

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

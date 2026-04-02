"""Graph-instance schema helpers for runtime control-graph configs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from . import SINK_DEFS, SOURCE_DEFS, TRANSFORM_DEFS
from .core import GraphTypeDef, ParamDef

GRAPH_SCHEMA_VERSION = 1


class ControlGraphValidationError(ValueError):
    """Raised when a control-graph config is structurally invalid."""


GraphConfig = dict[str, Any]
GraphConfigInput = Mapping[str, Any] | "ControlGraphConfig" | GraphConfig


@dataclass(frozen=True)
class GraphNodeConfig:
    """Typed runtime instance of a source/transform/sink node."""

    type: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "params": deepcopy(self.params)}


@dataclass(frozen=True)
class GraphSlotConfig:
    """Typed runtime instance of a control-graph slot."""

    id: str
    source: GraphNodeConfig
    enabled: bool = True
    rate_hz: float | int | None = None
    transforms: tuple[GraphNodeConfig, ...] = field(default_factory=tuple)
    sink: GraphNodeConfig | None = None
    sinks: tuple[GraphNodeConfig, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "enabled": self.enabled,
            "rate_hz": self.rate_hz,
            "source": self.source.to_dict(),
            "transforms": [node.to_dict() for node in self.transforms],
        }
        if self.sink is not None:
            data["sink"] = self.sink.to_dict()
        elif self.sinks:
            data["sinks"] = [node.to_dict() for node in self.sinks]
        else:
            raise ControlGraphValidationError(f"slot {self.id!r} must have at least one sink")
        return data

    def with_enabled(self, enabled: bool) -> "GraphSlotConfig":
        return GraphSlotConfig(
            id=self.id,
            source=self.source,
            enabled=enabled,
            rate_hz=self.rate_hz,
            transforms=self.transforms,
            sink=self.sink,
            sinks=self.sinks,
        )


@dataclass(frozen=True)
class ControlGraphConfig:
    """Typed runtime control-graph config used as the schema/source-of-truth boundary."""

    schema_version: int = GRAPH_SCHEMA_VERSION
    slots: tuple[GraphSlotConfig, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "slots": [slot.to_dict() for slot in self.slots],
        }

    def with_enabled(self, enabled: bool) -> "ControlGraphConfig":
        return ControlGraphConfig(
            schema_version=self.schema_version,
            slots=tuple(slot.with_enabled(enabled) for slot in self.slots),
        )


# Mapping from internal param types to valid JSON Schema types
_JSON_SCHEMA_TYPE_MAP = {
    "int": "integer",
    "float": "number",
    "string": "string",
    "bool": "boolean",
    "enum": "string",  # enum type uses "string" with an enum array
    "string_list": "array",  # array of strings
}


def _param_schema(param: ParamDef) -> dict[str, Any]:
    json_type = _JSON_SCHEMA_TYPE_MAP.get(param.type, param.type)

    # Handle string_list as array of strings
    if param.type == "string_list":
        schema: dict[str, Any] = {
            "type": "array",
            "items": {"type": "string"},
        }
    else:
        schema = {"type": json_type}

    if param.description:
        schema["description"] = param.description
    if param.default is not None:
        schema["default"] = param.default
    if param.minimum is not None:
        schema["minimum"] = param.minimum
    if param.maximum is not None:
        schema["maximum"] = param.maximum
    if param.enum is not None:
        schema["enum"] = list(param.enum)
    return schema


def _kind_schema(defs: dict[str, GraphTypeDef], title: str) -> dict[str, Any]:
    one_of: list[dict[str, Any]] = []

    for kind, spec in sorted(defs.items()):
        properties = {
            "type": {"const": kind},
            "params": {
                "type": "object",
                "properties": {param.name: _param_schema(param) for param in spec.params},
                "additionalProperties": False,
            },
        }
        required = ["type"]
        required_params = [param.name for param in spec.params if param.required and param.default is None]
        if required_params:
            properties["params"]["required"] = required_params
        one_of.append(
            {
                "title": kind,
                "description": spec.description,
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            }
        )

    return {
        "title": title,
        "oneOf": one_of,
    }


def graph_json_schema() -> dict[str, Any]:
    """Return a JSON-schema-ish description for control-graph configs."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "MARA Control Graph",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": GRAPH_SCHEMA_VERSION},
            "slots": {
                "type": "array",
                "items": {"$ref": "#/definitions/slot"},
            },
        },
        "required": ["schema_version", "slots"],
        "definitions": {
            "slot": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "enabled": {"type": "boolean", "default": True},
                    "rate_hz": {"type": "number", "exclusiveMinimum": 0},
                    "source": _kind_schema(SOURCE_DEFS, "source"),
                    "transforms": {
                        "type": "array",
                        "items": _kind_schema(TRANSFORM_DEFS, "transform"),
                        "default": [],
                    },
                    "sink": _kind_schema(SINK_DEFS, "sink"),
                    "sinks": {
                        "type": "array",
                        "items": _kind_schema(SINK_DEFS, "sink"),
                        "minItems": 1,
                        "maxItems": 4,
                    },
                },
                "required": ["id", "source"],
                "oneOf": [
                    {"required": ["sink"]},
                    {"required": ["sinks"]},
                ],
            },
            "source": {kind: {"type": "object"} for kind in SOURCE_DEFS},
            "transform": {kind: {"type": "object"} for kind in TRANSFORM_DEFS},
            "sink": {kind: {"type": "object"} for kind in SINK_DEFS},
        },
    }


def _validate_param_value(param: ParamDef, value: Any, path: str) -> None:
    if param.type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ControlGraphValidationError(f"{path} must be an int")
    elif param.type == "float":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ControlGraphValidationError(f"{path} must be a number")
    elif param.type == "string":
        if not isinstance(value, str):
            raise ControlGraphValidationError(f"{path} must be a string")
    elif param.type == "bool":
        if not isinstance(value, bool):
            raise ControlGraphValidationError(f"{path} must be a bool")
    elif param.type == "enum":
        if value not in (param.enum or []):
            raise ControlGraphValidationError(f"{path} must be one of {param.enum}")
    elif param.type == "string_list":
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ControlGraphValidationError(f"{path} must be a list of strings")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if param.minimum is not None and value < param.minimum:
            raise ControlGraphValidationError(f"{path} must be >= {param.minimum}")
        if param.maximum is not None and value > param.maximum:
            raise ControlGraphValidationError(f"{path} must be <= {param.maximum}")


def _normalize_node(node: Any, defs: dict[str, GraphTypeDef], path: str) -> GraphNodeConfig:
    if isinstance(node, GraphNodeConfig):
        node = node.to_dict()
    if not isinstance(node, Mapping):
        raise ControlGraphValidationError(f"{path} must be an object")

    kind = node.get("type")
    if not isinstance(kind, str):
        raise ControlGraphValidationError(f"{path}.type must be a string")
    spec = defs.get(kind)
    if spec is None:
        raise ControlGraphValidationError(f"{path}.type unknown: {kind}")

    allowed = {"type", "params"}
    extra = set(node) - allowed
    if extra:
        raise ControlGraphValidationError(f"{path} has unexpected fields: {sorted(extra)}")

    params_in = node.get("params", {})
    if params_in is None:
        params_in = {}
    if not isinstance(params_in, Mapping):
        raise ControlGraphValidationError(f"{path}.params must be an object")

    params_out: dict[str, Any] = {}
    known_names = {param.name for param in spec.params}
    extra_params = set(params_in) - known_names
    if extra_params:
        raise ControlGraphValidationError(f"{path}.params has unexpected keys: {sorted(extra_params)}")

    for param in spec.params:
        if param.name in params_in:
            value = params_in[param.name]
        elif param.default is not None:
            value = deepcopy(param.default)
        elif param.required:
            raise ControlGraphValidationError(f"{path}.params.{param.name} is required")
        else:
            continue

        _validate_param_value(param, value, f"{path}.params.{param.name}")
        params_out[param.name] = deepcopy(value)

    return GraphNodeConfig(type=kind, params=params_out)


def normalize_graph_model(config: GraphConfigInput) -> ControlGraphConfig:
    if isinstance(config, ControlGraphConfig):
        config = config.to_dict()
    if not isinstance(config, Mapping):
        raise ControlGraphValidationError("graph config must be an object")

    extra_top = set(config) - {"schema_version", "slots"}
    if extra_top:
        raise ControlGraphValidationError(f"graph config has unexpected fields: {sorted(extra_top)}")

    schema_version = config.get("schema_version", GRAPH_SCHEMA_VERSION)
    if schema_version != GRAPH_SCHEMA_VERSION:
        raise ControlGraphValidationError(
            f"schema_version must be {GRAPH_SCHEMA_VERSION}, got {schema_version}"
        )

    slots_in = config.get("slots")
    if not isinstance(slots_in, list):
        raise ControlGraphValidationError("slots must be an array")

    seen_ids: set[str] = set()
    slots_out: list[GraphSlotConfig] = []
    for idx, slot in enumerate(slots_in):
        path = f"slots[{idx}]"
        if isinstance(slot, GraphSlotConfig):
            slot = slot.to_dict()
        if not isinstance(slot, Mapping):
            raise ControlGraphValidationError(f"{path} must be an object")

        extra = set(slot) - {"id", "enabled", "rate_hz", "source", "transforms", "sink", "sinks"}
        if extra:
            raise ControlGraphValidationError(f"{path} has unexpected fields: {sorted(extra)}")

        slot_id = slot.get("id")
        if not isinstance(slot_id, str) or not slot_id:
            raise ControlGraphValidationError(f"{path}.id must be a non-empty string")
        if slot_id in seen_ids:
            raise ControlGraphValidationError(f"duplicate slot id: {slot_id}")
        seen_ids.add(slot_id)

        enabled = slot.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ControlGraphValidationError(f"{path}.enabled must be a bool")

        rate_hz = slot.get("rate_hz")
        if rate_hz is not None:
            if not isinstance(rate_hz, (int, float)) or isinstance(rate_hz, bool) or rate_hz <= 0:
                raise ControlGraphValidationError(f"{path}.rate_hz must be > 0")

        source = _normalize_node(slot.get("source"), SOURCE_DEFS, f"{path}.source")

        has_sink = "sink" in slot
        has_sinks = "sinks" in slot
        if has_sink and has_sinks:
            raise ControlGraphValidationError(f"{path} cannot have both 'sink' and 'sinks'")
        if not has_sink and not has_sinks:
            raise ControlGraphValidationError(f"{path} must have either 'sink' or 'sinks'")

        sink: GraphNodeConfig | None = None
        sinks: tuple[GraphNodeConfig, ...] = tuple()
        if has_sink:
            sink = _normalize_node(slot.get("sink"), SINK_DEFS, f"{path}.sink")
        else:
            sinks_in = slot.get("sinks")
            if not isinstance(sinks_in, list) or len(sinks_in) == 0:
                raise ControlGraphValidationError(f"{path}.sinks must be a non-empty array")
            if len(sinks_in) > 4:
                raise ControlGraphValidationError(f"{path}.sinks cannot have more than 4 items")
            sinks = tuple(
                _normalize_node(s, SINK_DEFS, f"{path}.sinks[{s_idx}]")
                for s_idx, s in enumerate(sinks_in)
            )

        transforms_in = slot.get("transforms", [])
        if not isinstance(transforms_in, list):
            raise ControlGraphValidationError(f"{path}.transforms must be an array")
        transforms = tuple(
            _normalize_node(node, TRANSFORM_DEFS, f"{path}.transforms[{t_idx}]")
            for t_idx, node in enumerate(transforms_in)
        )

        slots_out.append(
            GraphSlotConfig(
                id=slot_id,
                source=source,
                enabled=enabled,
                rate_hz=rate_hz,
                transforms=transforms,
                sink=sink,
                sinks=sinks,
            )
        )

    return ControlGraphConfig(schema_version=GRAPH_SCHEMA_VERSION, slots=tuple(slots_out))


def normalize_graph_config(config: GraphConfigInput) -> GraphConfig:
    """Compatibility shim: validate into typed objects, then emit canonical dicts."""
    return normalize_graph_model(config).to_dict()


def validate_graph_config(config: GraphConfigInput) -> None:
    """Validate a graph config, raising ControlGraphValidationError on failure."""
    normalize_graph_model(config)

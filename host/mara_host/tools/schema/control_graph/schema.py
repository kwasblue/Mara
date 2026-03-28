"""Graph-instance schema helpers for runtime control-graph configs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import SOURCE_DEFS, TRANSFORM_DEFS, SINK_DEFS
from .core import GraphTypeDef, ParamDef

GRAPH_SCHEMA_VERSION = 1


class ControlGraphValidationError(ValueError):
    """Raised when a control-graph config is structurally invalid."""


GraphConfig = dict[str, Any]


def _param_schema(param: ParamDef) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": param.type}
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
    if param.unit is not None:
        schema["unit"] = param.unit
    return schema


def _kind_schema(defs: dict[str, GraphTypeDef], title: str) -> dict[str, Any]:
    discriminator = sorted(defs)
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
        "discriminator": {
            "propertyName": "type",
            "mapping": {kind: f"#/definitions/{title}/{kind}" for kind in discriminator},
        },
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

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if param.minimum is not None and value < param.minimum:
            raise ControlGraphValidationError(f"{path} must be >= {param.minimum}")
        if param.maximum is not None and value > param.maximum:
            raise ControlGraphValidationError(f"{path} must be <= {param.maximum}")


def _normalize_node(node: Any, defs: dict[str, GraphTypeDef], path: str) -> dict[str, Any]:
    if not isinstance(node, dict):
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
    if not isinstance(params_in, dict):
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
        params_out[param.name] = value

    return {"type": kind, "params": params_out}


def normalize_graph_config(config: GraphConfig) -> GraphConfig:
    if not isinstance(config, dict):
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
    slots_out: list[dict[str, Any]] = []
    for idx, slot in enumerate(slots_in):
        path = f"slots[{idx}]"
        if not isinstance(slot, dict):
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

        # Support both single sink and array of sinks (SIMO)
        has_sink = "sink" in slot
        has_sinks = "sinks" in slot
        if has_sink and has_sinks:
            raise ControlGraphValidationError(f"{path} cannot have both 'sink' and 'sinks'")
        if not has_sink and not has_sinks:
            raise ControlGraphValidationError(f"{path} must have either 'sink' or 'sinks'")

        sinks: list[dict[str, Any]] = []
        if has_sink:
            sinks = [_normalize_node(slot.get("sink"), SINK_DEFS, f"{path}.sink")]
        else:
            sinks_in = slot.get("sinks")
            if not isinstance(sinks_in, list) or len(sinks_in) == 0:
                raise ControlGraphValidationError(f"{path}.sinks must be a non-empty array")
            if len(sinks_in) > 4:
                raise ControlGraphValidationError(f"{path}.sinks cannot have more than 4 items")
            sinks = [
                _normalize_node(s, SINK_DEFS, f"{path}.sinks[{s_idx}]")
                for s_idx, s in enumerate(sinks_in)
            ]

        transforms_in = slot.get("transforms", [])
        if not isinstance(transforms_in, list):
            raise ControlGraphValidationError(f"{path}.transforms must be an array")
        transforms = [
            _normalize_node(node, TRANSFORM_DEFS, f"{path}.transforms[{t_idx}]")
            for t_idx, node in enumerate(transforms_in)
        ]

        # Use "sink" for single, "sinks" for multiple (backwards compatible)
        slot_out: dict[str, Any] = {
            "id": slot_id,
            "enabled": enabled,
            "rate_hz": rate_hz,
            "source": source,
            "transforms": transforms,
        }
        if len(sinks) == 1:
            slot_out["sink"] = sinks[0]
        else:
            slot_out["sinks"] = sinks
        slots_out.append(slot_out)

    return {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "slots": slots_out,
    }


def validate_graph_config(config: GraphConfig) -> None:
    """Validate a graph config, raising ControlGraphValidationError on failure."""
    normalize_graph_config(config)

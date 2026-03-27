from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from mara_host.core.result import ServiceResult
from mara_host.tools.schema import COMMANDS


class CompositeService:
    """Generic composite/batch actuator service using {cmd, args} actions."""

    BATCHABLE_COMMANDS: dict[str, dict[str, Any]] = {
        "CMD_GPIO_WRITE": {
            "conflict_group": None,
            "max_actions_error": "too_many_gpio_actions",
        },
        "CMD_SERVO_SET_ANGLE": {
            "conflict_group": None,
            "max_actions_error": "too_many_servo_actions",
        },
        "CMD_PWM_SET": {
            "conflict_group": None,
            "max_actions_error": "too_many_pwm_actions",
        },
        "CMD_DC_SET_SPEED": {
            "conflict_group": "dc_motor",
            "id_field": "motor_id",
            "conflict_error": "conflicting_motor_action",
            "max_actions_error": "too_many_motor_set_actions",
        },
        "CMD_DC_STOP": {
            "conflict_group": "dc_motor",
            "id_field": "motor_id",
            "conflict_error": "conflicting_motor_action",
            "max_actions_error": "too_many_motor_stop_actions",
        },
        "CMD_STEPPER_MOVE_REL": {
            "conflict_group": "stepper",
            "id_field": "motor_id",
            "conflict_error": "conflicting_stepper_action",
            "max_actions_error": "too_many_stepper_move_actions",
        },
        "CMD_STEPPER_STOP": {
            "conflict_group": "stepper",
            "id_field": "motor_id",
            "conflict_error": "conflicting_stepper_action",
            "max_actions_error": "too_many_stepper_stop_actions",
        },
    }

    TYPE_MAP = {
        "int": int,
        "float": (int, float),
        "string": str,
        "bool": bool,
        "array": list,
        "object": dict,
    }

    def __init__(self, client):
        self.client = client

    @staticmethod
    def _is_finite_number(value) -> bool:
        return isinstance(value, (int, float)) and math.isfinite(value)

    def _normalize_field(self, spec: dict[str, Any], value: Any) -> Any:
        field_type = spec.get("type")
        if field_type == "float":
            return float(value)
        if field_type == "int":
            return int(value)
        return value

    def _validate_arg(self, name: str, spec: dict[str, Any], value: Any) -> str | None:
        field_type = spec.get("type")
        expected = self.TYPE_MAP.get(field_type)
        if expected and not isinstance(value, expected):
            return f"invalid_{name}"

        if field_type == "float" and not self._is_finite_number(value):
            return f"invalid_{name}"

        if "enum" in spec and value not in spec["enum"]:
            return f"invalid_{name}"

        if field_type in {"int", "float"}:
            numeric = float(value)
            if "min" in spec and numeric < float(spec["min"]):
                return f"invalid_{name}"
            if "max" in spec and numeric > float(spec["max"]):
                return f"invalid_{name}"

        return None

    def _validate_actions(self, actions: list[dict]) -> tuple[list[dict], str | None]:
        if not isinstance(actions, list) or not actions:
            return [], "actions_required"

        normalized: list[dict] = []
        seen_conflicts: dict[str, set[int]] = {"dc_motor": set(), "stepper": set()}

        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                return [], f"action_{index}_must_be_object"

            cmd = action.get("cmd")
            if not isinstance(cmd, str) or not cmd:
                return [], f"missing_cmd:{index}"
            if cmd not in self.BATCHABLE_COMMANDS:
                return [], f"unsupported_batch_command:{cmd}"

            args = action.get("args", {})
            if args is None:
                args = {}
            if not isinstance(args, dict):
                return [], f"invalid_args:{index}"

            payload_spec = COMMANDS.get(cmd, {}).get("payload", {}) or {}
            normalized_args = deepcopy(args)

            for field_name, field_spec in payload_spec.items():
                if field_name not in normalized_args:
                    if field_spec.get("required"):
                        return [], f"missing_{field_name}:{index}"
                    if "default" in field_spec:
                        normalized_args[field_name] = deepcopy(field_spec["default"])
                    continue

                error = self._validate_arg(field_name, field_spec, normalized_args[field_name])
                if error:
                    return [], f"{error}:{index}"
                normalized_args[field_name] = self._normalize_field(field_spec, normalized_args[field_name])

            unknown_fields = sorted(set(normalized_args) - set(payload_spec))
            if unknown_fields:
                return [], f"unexpected_args:{index}:{','.join(unknown_fields)}"

            policy = self.BATCHABLE_COMMANDS[cmd]
            conflict_group = policy.get("conflict_group")
            id_field = policy.get("id_field")
            if conflict_group and id_field:
                actuator_id = normalized_args.get(id_field)
                if not isinstance(actuator_id, int) or actuator_id < 0:
                    return [], f"invalid_{id_field}:{index}"
                if actuator_id in seen_conflicts[conflict_group]:
                    return [], f"{policy['conflict_error']}:{index}"
                seen_conflicts[conflict_group].add(actuator_id)

            normalized.append({"cmd": cmd, "args": normalized_args})

        return normalized, None

    async def apply(self, actions: list[dict]) -> ServiceResult:
        normalized, error = self._validate_actions(actions)
        if error:
            return ServiceResult.failure(error=error)

        ok, error = await self.client.send_reliable(
            "CMD_BATCH_APPLY",
            {"actions": normalized},
        )
        if not ok:
            return ServiceResult.failure(error=error or "Failed to apply batch")
        return ServiceResult.success(data={"actions": normalized, "count": len(normalized)})

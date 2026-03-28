"""Core definition helpers for the control-graph schema registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParamDef:
    """Declarative parameter definition for a graph type."""

    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    minimum: float | int | None = None
    maximum: float | int | None = None
    enum: list[Any] | None = None
    unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "required": self.required,
        }
        if self.description:
            data["description"] = self.description
        if self.default is not None:
            data["default"] = self.default
        if self.minimum is not None:
            data["minimum"] = self.minimum
        if self.maximum is not None:
            data["maximum"] = self.maximum
        if self.enum is not None:
            data["enum"] = list(self.enum)
        if self.unit is not None:
            data["unit"] = self.unit
        return data

    @classmethod
    def int(cls, name: str, **kwargs: Any) -> "ParamDef":
        return cls(name=name, type="int", **kwargs)

    @classmethod
    def float(cls, name: str, **kwargs: Any) -> "ParamDef":
        return cls(name=name, type="float", **kwargs)

    @classmethod
    def string(cls, name: str, **kwargs: Any) -> "ParamDef":
        return cls(name=name, type="string", **kwargs)

    @classmethod
    def boolean(cls, name: str, **kwargs: Any) -> "ParamDef":
        return cls(name=name, type="bool", **kwargs)

    @classmethod
    def enum_param(cls, name: str, *, values: list[Any], **kwargs: Any) -> "ParamDef":
        return cls(name=name, type="enum", enum=values, **kwargs)

    @classmethod
    def string_list(cls, name: str, **kwargs: Any) -> "ParamDef":
        return cls(name=name, type="string_list", **kwargs)


@dataclass(frozen=True)
class GraphTypeDef:
    """Base definition for a graph source/transform/sink kind."""

    kind: str
    category: str
    description: str
    params: tuple[ParamDef, ...] = field(default_factory=tuple)
    inputs: int = 0
    outputs: int = 0
    stateful: bool = False
    mcu_supported: bool = True
    host_supported: bool = True
    requires: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    impl_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "category": self.category,
            "description": self.description,
            "params": [param.to_dict() for param in self.params],
            "inputs": self.inputs,
            "outputs": self.outputs,
            "stateful": self.stateful,
            "mcu_supported": self.mcu_supported,
            "host_supported": self.host_supported,
            "requires": list(self.requires),
            "tags": list(self.tags),
        }
        if self.impl_key is not None:
            data["impl_key"] = self.impl_key
        return data


@dataclass(frozen=True)
class SourceDef(GraphTypeDef):
    def __init__(self, *, kind: str, description: str, params: tuple[ParamDef, ...] = tuple(), outputs: int = 1,
                 stateful: bool = False, mcu_supported: bool = True, host_supported: bool = True,
                 requires: tuple[str, ...] = tuple(), tags: tuple[str, ...] = tuple(), impl_key: str | None = None):
        super().__init__(
            kind=kind,
            category="source",
            description=description,
            params=params,
            inputs=0,
            outputs=outputs,
            stateful=stateful,
            mcu_supported=mcu_supported,
            host_supported=host_supported,
            requires=requires,
            tags=tags,
            impl_key=impl_key,
        )


@dataclass(frozen=True)
class TransformDef(GraphTypeDef):
    def __init__(self, *, kind: str, description: str, params: tuple[ParamDef, ...] = tuple(), inputs: int = 1,
                 outputs: int = 1, stateful: bool = False, mcu_supported: bool = True,
                 host_supported: bool = True, requires: tuple[str, ...] = tuple(), tags: tuple[str, ...] = tuple(),
                 impl_key: str | None = None):
        super().__init__(
            kind=kind,
            category="transform",
            description=description,
            params=params,
            inputs=inputs,
            outputs=outputs,
            stateful=stateful,
            mcu_supported=mcu_supported,
            host_supported=host_supported,
            requires=requires,
            tags=tags,
            impl_key=impl_key,
        )


@dataclass(frozen=True)
class SinkDef(GraphTypeDef):
    def __init__(self, *, kind: str, description: str, params: tuple[ParamDef, ...] = tuple(), inputs: int = 1,
                 stateful: bool = False, mcu_supported: bool = True, host_supported: bool = True,
                 requires: tuple[str, ...] = tuple(), tags: tuple[str, ...] = tuple(), impl_key: str | None = None):
        super().__init__(
            kind=kind,
            category="sink",
            description=description,
            params=params,
            inputs=inputs,
            outputs=0,
            stateful=stateful,
            mcu_supported=mcu_supported,
            host_supported=host_supported,
            requires=requires,
            tags=tags,
            impl_key=impl_key,
        )

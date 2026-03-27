"""Discovery helpers for control-graph type definition modules."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .core import GraphTypeDef


def discover_defs(package_file: str, package_name: str, export_name: str) -> dict[str, GraphTypeDef]:
    registry: dict[str, GraphTypeDef] = {}
    package_dir = Path(package_file).parent

    for module_file in sorted(package_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue
        module_name = module_file.stem
        module = importlib.import_module(f"{package_name}.{module_name}")
        exported: Any = getattr(module, export_name, None)
        if exported is None:
            continue
        if not isinstance(exported, GraphTypeDef):
            raise TypeError(f"{package_name}.{module_name}.{export_name} must be a GraphTypeDef")
        if exported.kind in registry:
            raise ValueError(f"Duplicate control-graph kind: {exported.kind}")
        registry[exported.kind] = exported

    return registry

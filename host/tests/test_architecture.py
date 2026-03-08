# tests/test_architecture.py
"""
Architecture boundary tests.

These tests verify that module boundaries are respected and that internal
modules don't leak into public API or violate layering rules.

Layer hierarchy (higher layers may import from lower, not vice versa):
    1. api/         - Public user-facing API (top)
    2. runtime/     - Runtime orchestration
    3. command/     - Client and command handling
    4. motor/, sensor/, hw/ - Host modules
    5. core/        - Core infrastructure
    6. transport/   - Transport layer (bottom)

Rules:
    - transport/ should not import from command/ or api/
    - core/ should not import from motor/, sensor/, hw/, api/
    - api/ is the public surface, all others are internal
"""

import ast
import importlib
from pathlib import Path
from typing import Set

import pytest


# Get the mara_host source directory
MARA_HOST_ROOT = Path(__file__).parent.parent / "mara_host"


def get_imports_from_file(filepath: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Handle relative imports
                if node.level > 0:
                    # Relative import like "from . import x" or "from ..core import y"
                    # We'll track the full module path
                    imports.add(f"relative:{node.level}:{node.module or ''}")
                else:
                    imports.add(node.module.split(".")[0])
    return imports


def get_mara_imports_from_file(filepath: Path) -> Set[str]:
    """Extract mara_host submodule imports from a Python file."""
    imports = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(filepath))
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("mara_host."):
                # Extract the submodule (e.g., "mara_host.command" -> "command")
                parts = node.module.split(".")
                if len(parts) >= 2:
                    imports.add(parts[1])
            elif node.level > 0 and node.module:
                # Relative import - extract target module
                imports.add(node.module.split(".")[0])
    return imports


class TestPublicAPIBoundary:
    """Verify that the public API is clearly defined."""

    def test_mara_host_has_all_defined(self):
        """Top-level mara_host must define __all__."""
        import mara_host
        assert hasattr(mara_host, "__all__"), "mara_host must define __all__"
        assert len(mara_host.__all__) > 0, "__all__ must not be empty"

    def test_public_api_does_not_expose_internals(self):
        """Public __all__ should not include internal modules."""
        import mara_host

        internal_prefixes = ("_", "core", "hw", "motor", "sensor", "telemetry")
        for name in mara_host.__all__:
            for prefix in internal_prefixes:
                if name.lower().startswith(prefix) and not name.startswith("__"):
                    # Allow things like "EncoderReading" but not "core" or "_internal"
                    if name in ("core", "hw", "motor", "sensor", "telemetry"):
                        pytest.fail(f"Internal module '{name}' exposed in public __all__")


class TestTransportLayerBoundary:
    """Transport layer should be low-level and not depend on higher layers."""

    def test_transport_does_not_import_command(self):
        """Transport modules should not import from command layer."""
        transport_dir = MARA_HOST_ROOT / "transport"
        if not transport_dir.exists():
            pytest.skip("transport directory not found")

        violations = []
        for py_file in transport_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            imports = get_mara_imports_from_file(py_file)
            if "command" in imports:
                violations.append(f"{py_file.name} imports from command/")

        assert not violations, f"Transport layer violations: {violations}"

    def test_transport_does_not_import_api(self):
        """Transport modules should not import from api layer."""
        transport_dir = MARA_HOST_ROOT / "transport"
        if not transport_dir.exists():
            pytest.skip("transport directory not found")

        violations = []
        for py_file in transport_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            imports = get_mara_imports_from_file(py_file)
            if "api" in imports:
                violations.append(f"{py_file.name} imports from api/")

        assert not violations, f"Transport layer violations: {violations}"


class TestCoreLayerBoundary:
    """Core layer should not depend on domain modules."""

    def test_core_does_not_import_motor(self):
        """Core modules should not import from motor layer."""
        core_dir = MARA_HOST_ROOT / "core"
        if not core_dir.exists():
            pytest.skip("core directory not found")

        violations = []
        for py_file in core_dir.glob("*.py"):
            imports = get_mara_imports_from_file(py_file)
            if "motor" in imports:
                violations.append(f"{py_file.name} imports from motor/")

        assert not violations, f"Core layer violations: {violations}"

    def test_core_does_not_import_sensor(self):
        """Core modules should not import from sensor layer."""
        core_dir = MARA_HOST_ROOT / "core"
        if not core_dir.exists():
            pytest.skip("core directory not found")

        violations = []
        for py_file in core_dir.glob("*.py"):
            imports = get_mara_imports_from_file(py_file)
            if "sensor" in imports:
                violations.append(f"{py_file.name} imports from sensor/")

        assert not violations, f"Core layer violations: {violations}"

    def test_core_does_not_import_api(self):
        """Core modules should not import from api layer."""
        core_dir = MARA_HOST_ROOT / "core"
        if not core_dir.exists():
            pytest.skip("core directory not found")

        violations = []
        for py_file in core_dir.glob("*.py"):
            imports = get_mara_imports_from_file(py_file)
            if "api" in imports:
                violations.append(f"{py_file.name} imports from api/")

        assert not violations, f"Core layer violations: {violations}"


class TestInternalModulesHaveAll:
    """Internal modules should define __all__ for explicit exports."""

    @pytest.mark.parametrize("module_name", [
        "core",
        "hw",
        "motor",
        "sensor",
        "telemetry",
        "command",
    ])
    def test_internal_module_has_all(self, module_name: str):
        """Each internal module should define __all__."""
        try:
            module = importlib.import_module(f"mara_host.{module_name}")
            assert hasattr(module, "__all__"), f"mara_host.{module_name} must define __all__"
        except ImportError as e:
            pytest.skip(f"Could not import mara_host.{module_name}: {e}")


class TestNoCircularImports:
    """Verify no circular import issues exist."""

    def test_can_import_all_public_symbols(self):
        """All public symbols should be importable without circular import errors."""
        import mara_host

        for name in mara_host.__all__:
            obj = getattr(mara_host, name, None)
            assert obj is not None, f"Public symbol '{name}' is None (possible circular import)"

    def test_can_import_internal_modules_independently(self):
        """Internal modules should be importable on their own."""
        modules = [
            "mara_host.core",
            "mara_host.hw",
            "mara_host.motor",
            "mara_host.sensor",
            "mara_host.telemetry",
            "mara_host.command",
            "mara_host.transport",
        ]

        for module_name in modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

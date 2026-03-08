# mara_host/workflows/__init__.py
"""
Workflow layer for MARA operations.

AUTO-DISCOVERY: Workflows are lazily imported from subpackages.
To add a new workflow:
1. Create in the appropriate subpackage (calibration/, testing/, recording/)
2. Add to _EXPORTS below

Provides reusable, testable workflows for calibration, testing,
recording, and other multi-step operations. Workflows can be used
from CLI, GUI, or programmatically.

Example:
    from mara_host.workflows import MotorCalibrationWorkflow

    workflow = MotorCalibrationWorkflow(client)
    workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

    result = await workflow.run(motor_id=0)
    if result.ok:
        print(f"Dead zone: {result.data['dead_zone']}")
"""

import importlib
from typing import Any

_EXPORTS = {
    # Base classes (always needed, import eagerly)
    "BaseWorkflow": "base",
    "WorkflowResult": "base",
    "WorkflowState": "base",
    # Calibration workflows
    "MotorCalibrationWorkflow": "calibration",
    "ServoCalibrationWorkflow": "calibration",
    "EncoderCalibrationWorkflow": "calibration",
    "IMUCalibrationWorkflow": "calibration",
    "PIDTuningWorkflow": "calibration",
    # Testing workflows
    "SmokeTestWorkflow": "testing",
    "HardwareTestWorkflow": "testing",
    "LatencyProfiler": "testing",
    # Recording workflows
    "RecordingWorkflow": "recording",
    "ReplayWorkflow": "recording",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        module_name = _EXPORTS[name]
        if module_name not in _cache:
            _cache[module_name] = importlib.import_module(
                f".{module_name}", package=__name__
            )
        return getattr(_cache[module_name], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(_EXPORTS.keys())


__all__ = list(_EXPORTS.keys())

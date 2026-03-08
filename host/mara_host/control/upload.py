"""
Upload helpers for transferring control configurations to the MCU.

Provides high-level functions to configure and upload state-space controllers
and Luenberger observers to the ESP32 control kernel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
from numpy.typing import ArrayLike

from .state_space import StateSpaceModel
from .design import check_stability

if TYPE_CHECKING:
    # Avoid circular import - client type is only needed for type hints
    pass


@dataclass
class SignalDefinition:
    """Signal definition for the MCU signal bus."""

    id: int
    name: str
    kind: str  # "reference", "measurement", "control", "state", "estimate"
    initial: float = 0.0


@dataclass
class ControllerConfig:
    """
    Configuration for uploading a state-space controller to MCU.

    Attributes:
        slot: Control slot index (0-7)
        K: State feedback gain matrix (m x n)
        Kr: Optional reference gain matrix (m x p)
        Ki: Optional integral gain matrix (m x p)
        state_ids: Signal IDs for state inputs
        ref_ids: Signal IDs for reference inputs
        output_ids: Signal IDs for control outputs
        rate_hz: Controller update rate
    """

    slot: int
    K: np.ndarray
    state_ids: List[int]
    output_ids: List[int]
    Kr: Optional[np.ndarray] = None
    Ki: Optional[np.ndarray] = None
    ref_ids: Optional[List[int]] = None
    rate_hz: int = 100
    require_armed: bool = True
    require_active: bool = True


@dataclass
class ObserverConfig:
    """
    Configuration for uploading a Luenberger observer to MCU.

    Attributes:
        slot: Observer slot index (0-3)
        A: State matrix (n x n)
        B: Input matrix (n x m)
        C: Output matrix (p x n)
        L: Observer gain matrix (n x p)
        input_ids: Signal IDs for control inputs (u)
        output_ids: Signal IDs for measurements (y)
        estimate_ids: Signal IDs for state estimates (x_hat)
        rate_hz: Observer update rate
    """

    slot: int
    A: np.ndarray
    B: np.ndarray
    C: np.ndarray
    L: np.ndarray
    input_ids: List[int]
    output_ids: List[int]
    estimate_ids: List[int]
    rate_hz: int = 200


def _matrix_to_row_major(matrix: np.ndarray) -> List[float]:
    """Convert numpy matrix to row-major list for MCU upload."""
    return matrix.flatten(order="C").tolist()


async def upload_controller(
    client: Any,
    config: ControllerConfig,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    Upload a state-space controller configuration to the MCU.

    Args:
        client: Robot client with send_json_cmd method
        config: Controller configuration
        validate: If True, check stability before uploading

    Returns:
        Dict with upload status and any warnings

    Example:
        from mara_host.control import lqr, upload_controller, ControllerConfig

        # Design controller
        K, S, E = lqr(A, B, Q, R)

        # Configure upload
        config = ControllerConfig(
            slot=0,
            K=K,
            state_ids=[10, 11],  # x1, x2 signals
            output_ids=[20],     # control output signal
            rate_hz=100,
        )

        # Upload to MCU
        result = await upload_controller(client, config)
    """
    result: Dict[str, Any] = {"success": False, "warnings": []}

    n_states = config.K.shape[1]
    n_inputs = config.K.shape[0]

    # Validate signal ID counts
    if len(config.state_ids) != n_states:
        raise ValueError(f"Expected {n_states} state_ids, got {len(config.state_ids)}")
    if len(config.output_ids) != n_inputs:
        raise ValueError(f"Expected {n_inputs} output_ids, got {len(config.output_ids)}")

    # Configure the control slot
    await client.send_json_cmd(
        "CMD_CTRL_SLOT_CONFIG",
        {
            "slot": config.slot,
            "controller_type": "STATE_SPACE",
            "rate_hz": config.rate_hz,
            "num_states": n_states,
            "num_inputs": n_inputs,
            "state_ids": config.state_ids,
            "ref_ids": config.ref_ids or config.state_ids,  # Default to state_ids if not specified
            "output_ids": config.output_ids,
            "require_armed": config.require_armed,
            "require_active": config.require_active,
        },
    )

    # Upload K matrix
    await client.send_json_cmd(
        "CMD_CTRL_SLOT_SET_PARAM_ARRAY",
        {
            "slot": config.slot,
            "key": "K",
            "values": _matrix_to_row_major(config.K),
        },
    )

    # Upload Kr matrix if provided
    if config.Kr is not None:
        await client.send_json_cmd(
            "CMD_CTRL_SLOT_SET_PARAM_ARRAY",
            {
                "slot": config.slot,
                "key": "Kr",
                "values": _matrix_to_row_major(config.Kr),
            },
        )

    # Upload Ki matrix if provided
    if config.Ki is not None:
        await client.send_json_cmd(
            "CMD_CTRL_SLOT_SET_PARAM_ARRAY",
            {
                "slot": config.slot,
                "key": "Ki",
                "values": _matrix_to_row_major(config.Ki),
            },
        )

    result["success"] = True
    result["slot"] = config.slot
    result["n_states"] = n_states
    result["n_inputs"] = n_inputs

    return result


async def upload_observer(
    client: Any,
    config: ObserverConfig,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    Upload a Luenberger observer configuration to the MCU.

    Args:
        client: Robot client with send_json_cmd method
        config: Observer configuration
        validate: If True, check observer stability before uploading

    Returns:
        Dict with upload status and any warnings

    Example:
        from mara_host.control import observer_gains, upload_observer, ObserverConfig

        # Design observer
        L = observer_gains(A, C, observer_poles)

        # Configure upload
        config = ObserverConfig(
            slot=0,
            A=A, B=B, C=C, L=L,
            input_ids=[20],       # Control input signal
            output_ids=[30],      # Measurement signal
            estimate_ids=[10, 11], # State estimate signals
            rate_hz=200,
        )

        # Upload to MCU
        result = await upload_observer(client, config)
    """
    result: Dict[str, Any] = {"success": False, "warnings": []}

    n_states = config.A.shape[0]
    n_inputs = config.B.shape[1]
    n_outputs = config.C.shape[0]

    # Validate matrix dimensions
    if config.A.shape != (n_states, n_states):
        raise ValueError(f"A must be {n_states}x{n_states}")
    if config.B.shape != (n_states, n_inputs):
        raise ValueError(f"B must be {n_states}x{n_inputs}")
    if config.C.shape != (n_outputs, n_states):
        raise ValueError(f"C must be {n_outputs}x{n_states}")
    if config.L.shape != (n_states, n_outputs):
        raise ValueError(f"L must be {n_states}x{n_outputs}")

    # Validate signal ID counts
    if len(config.input_ids) != n_inputs:
        raise ValueError(f"Expected {n_inputs} input_ids, got {len(config.input_ids)}")
    if len(config.output_ids) != n_outputs:
        raise ValueError(f"Expected {n_outputs} output_ids, got {len(config.output_ids)}")
    if len(config.estimate_ids) != n_states:
        raise ValueError(f"Expected {n_states} estimate_ids, got {len(config.estimate_ids)}")

    # Check observer stability if requested
    if validate:
        obs_poles = np.linalg.eigvals(config.A - config.L @ config.C)
        if not np.all(np.real(obs_poles) < 0):
            result["warnings"].append(
                f"Observer may be unstable! Poles: {obs_poles.tolist()}"
            )

    # Configure the observer slot
    await client.send_json_cmd(
        "CMD_OBSERVER_CONFIG",
        {
            "slot": config.slot,
            "num_states": n_states,
            "num_inputs": n_inputs,
            "num_outputs": n_outputs,
            "rate_hz": config.rate_hz,
            "input_ids": config.input_ids,
            "output_ids": config.output_ids,
            "estimate_ids": config.estimate_ids,
        },
    )

    # Upload matrices
    await client.send_json_cmd(
        "CMD_OBSERVER_SET_PARAM_ARRAY",
        {"slot": config.slot, "key": "A", "values": _matrix_to_row_major(config.A)},
    )
    await client.send_json_cmd(
        "CMD_OBSERVER_SET_PARAM_ARRAY",
        {"slot": config.slot, "key": "B", "values": _matrix_to_row_major(config.B)},
    )
    await client.send_json_cmd(
        "CMD_OBSERVER_SET_PARAM_ARRAY",
        {"slot": config.slot, "key": "C", "values": _matrix_to_row_major(config.C)},
    )
    await client.send_json_cmd(
        "CMD_OBSERVER_SET_PARAM_ARRAY",
        {"slot": config.slot, "key": "L", "values": _matrix_to_row_major(config.L)},
    )

    result["success"] = True
    result["slot"] = config.slot
    result["n_states"] = n_states
    result["n_inputs"] = n_inputs
    result["n_outputs"] = n_outputs

    return result


async def configure_state_feedback(
    client: Any,
    model: StateSpaceModel,
    K: ArrayLike,
    controller_slot: int = 0,
    observer_slot: int = 0,
    L: Optional[ArrayLike] = None,
    Kr: Optional[ArrayLike] = None,
    Ki: Optional[ArrayLike] = None,
    signals: Optional[Dict[str, List[int]]] = None,
    controller_rate_hz: int = 100,
    observer_rate_hz: int = 200,
    use_observer: bool = False,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    High-level helper to configure a complete state feedback system.

    This function sets up:
    1. Required signals on the signal bus
    2. State-space controller (K, Kr, Ki)
    3. Optionally, a Luenberger observer (A, B, C, L)

    Args:
        client: Robot client
        model: StateSpaceModel with A, B, C matrices
        K: State feedback gain matrix
        controller_slot: Control slot index (0-7)
        observer_slot: Observer slot index (0-3), if using observer
        L: Observer gain matrix (required if use_observer=True)
        Kr: Reference gain matrix (optional)
        Ki: Integral gain matrix (optional)
        signals: Dict mapping signal names to IDs:
            - "state": State/estimate signal IDs
            - "ref": Reference signal IDs
            - "control": Control output signal IDs
            - "measurement": Measurement signal IDs (for observer)
            - "input": Control input signal IDs (for observer)
        controller_rate_hz: Controller update rate
        observer_rate_hz: Observer update rate
        use_observer: If True, also configure an observer
        validate: If True, check stability before enabling

    Returns:
        Dict with configuration results

    Example:
        from mara_host.control import (
            StateSpaceModel, lqr, observer_gains, configure_state_feedback
        )

        # Define system
        model = StateSpaceModel(A, B, C)

        # Design controller and observer
        K, _, _ = lqr(A, B, Q, R)
        L = observer_gains(A, C, obs_poles)

        # Configure complete system
        result = await configure_state_feedback(
            client, model, K,
            L=L,
            use_observer=True,
            signals={
                "state": [10, 11],
                "ref": [12, 13],
                "control": [20],
                "measurement": [30],
                "input": [20],
            },
        )
    """
    K = np.atleast_2d(np.asarray(K, dtype=np.float64))
    result: Dict[str, Any] = {"success": False, "controller": None, "observer": None}

    n_states = model.num_states
    n_inputs = model.num_inputs
    n_outputs = model.num_outputs

    # Validate K dimensions
    if K.shape != (n_inputs, n_states):
        raise ValueError(f"K must be {n_inputs}x{n_states}, got {K.shape}")

    # Stability check
    if validate:
        is_stable, cl_poles = check_stability(model.A, model.B, K, continuous=True)
        if not is_stable:
            raise ValueError(
                f"Closed-loop system is unstable! Poles: {cl_poles.tolist()}"
            )
        result["closed_loop_poles"] = cl_poles.tolist()

    # Default signal mapping if not provided
    if signals is None:
        # Auto-generate signal IDs
        base_id = controller_slot * 100
        signals = {
            "state": list(range(base_id, base_id + n_states)),
            "ref": list(range(base_id + 10, base_id + 10 + n_states)),
            "control": list(range(base_id + 20, base_id + 20 + n_inputs)),
            "measurement": list(range(base_id + 30, base_id + 30 + n_outputs)),
            "input": list(range(base_id + 20, base_id + 20 + n_inputs)),
        }

    # Process optional matrices
    if Kr is not None:
        Kr = np.atleast_2d(np.asarray(Kr, dtype=np.float64))
    if Ki is not None:
        Ki = np.atleast_2d(np.asarray(Ki, dtype=np.float64))

    # Upload controller
    ctrl_config = ControllerConfig(
        slot=controller_slot,
        K=K,
        Kr=Kr,
        Ki=Ki,
        state_ids=signals.get("state", [])[:n_states],
        ref_ids=signals.get("ref", signals.get("state", []))[:n_states],
        output_ids=signals.get("control", [])[:n_inputs],
        rate_hz=controller_rate_hz,
    )
    result["controller"] = await upload_controller(client, ctrl_config, validate=False)

    # Upload observer if requested
    if use_observer:
        if L is None:
            raise ValueError("L (observer gain) required when use_observer=True")

        L = np.atleast_2d(np.asarray(L, dtype=np.float64))

        obs_config = ObserverConfig(
            slot=observer_slot,
            A=model.A,
            B=model.B,
            C=model.C,
            L=L,
            input_ids=signals.get("input", signals.get("control", []))[:n_inputs],
            output_ids=signals.get("measurement", [])[:n_outputs],
            estimate_ids=signals.get("state", [])[:n_states],
            rate_hz=observer_rate_hz,
        )
        result["observer"] = await upload_observer(client, obs_config, validate=validate)

    result["success"] = True
    return result


async def enable_controller(client: Any, slot: int, enable: bool = True) -> None:
    """Enable or disable a control slot."""
    await client.send_json_cmd("CMD_CTRL_SLOT_ENABLE", {"slot": slot, "enable": enable})


async def enable_observer(client: Any, slot: int, enable: bool = True) -> None:
    """Enable or disable an observer slot."""
    await client.send_json_cmd("CMD_OBSERVER_ENABLE", {"slot": slot, "enable": enable})


async def reset_controller(client: Any, slot: int) -> None:
    """Reset a controller's internal state (integrators, etc)."""
    await client.send_json_cmd("CMD_CTRL_SLOT_RESET", {"slot": slot})


async def reset_observer(client: Any, slot: int) -> None:
    """Reset an observer's state estimate to zero."""
    await client.send_json_cmd("CMD_OBSERVER_RESET", {"slot": slot})

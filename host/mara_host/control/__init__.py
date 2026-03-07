"""
Control system design tools for robot platform.

Provides scipy-based design tools for state-space controllers and observers,
with helpers to upload configurations to the MCU.

Example usage:
    from mara_host.control import StateSpaceModel, lqr, configure_state_feedback

    # Define system
    A = np.array([[0, 1], [-10, -0.5]])
    B = np.array([[0], [1]])
    C = np.array([[1, 0]])
    model = StateSpaceModel(A, B, C)

    # Design LQR controller
    Q = np.diag([100, 1])
    R = np.array([[1]])
    K, S, E = lqr(A, B, Q, R)

    # Upload to MCU
    result = await configure_state_feedback(client, model, K, ...)

See mara_host.control.examples for more detailed examples.
"""

from .state_space import StateSpaceModel, discretize
from .design import (
    lqr,
    lqr_discrete,
    pole_placement,
    observer_gains,
    acker,
    lqe,
    check_stability,
    reference_gain,
    integral_gain,
)
from .upload import (
    ControllerConfig,
    ObserverConfig,
    SignalDefinition,
    upload_controller,
    upload_observer,
    configure_state_feedback,
    enable_controller,
    enable_observer,
    reset_controller,
    reset_observer,
)

__all__ = [
    # Models
    "StateSpaceModel",
    "discretize",
    # Design - LQR
    "lqr",
    "lqr_discrete",
    "lqe",
    # Design - Pole placement
    "pole_placement",
    "observer_gains",
    "acker",
    # Design - Utilities
    "check_stability",
    "reference_gain",
    "integral_gain",
    # Upload - Config
    "ControllerConfig",
    "ObserverConfig",
    "SignalDefinition",
    # Upload - Functions
    "upload_controller",
    "upload_observer",
    "configure_state_feedback",
    "enable_controller",
    "enable_observer",
    "reset_controller",
    "reset_observer",
]

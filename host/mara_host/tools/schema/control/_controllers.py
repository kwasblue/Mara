# schema/control/_controllers.py
"""
Controller block definitions - SINGLE SOURCE OF TRUTH.

Adding a new controller (3 steps):
    1. Add entry to CONTROLLER_BLOCKS below
    2. Run: mara generate all
    3. Implement firmware if needed (most map to state-space)

That's it! GUI block + palette entry + firmware mapping auto-generated.

Each controller entry defines:
    - category: "controller" (required)
    - gui: {label, color, inputs, outputs, description} - Block diagram appearance
    - parameters: {param_name: {type, default, range, unit}} - Configurable params
    - firmware: {slot_type, maps_to, feature_flag} - Firmware mapping
    - state_space: {derive_fn} - How to derive state-space matrices

See docs/ADDING_CONTROL.md for full guide.
"""

from typing import Any

CONTROLLER_BLOCKS: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # PID Controller
    # -------------------------------------------------------------------------
    "pid": {
        "category": "controller",
        "gui": {
            "label": "PID",
            "color": "#3B82F6",
            "description": "PID controller with anti-windup",
            "inputs": [("ref", "REF", "reference"), ("meas", "MEAS", "measurement")],
            "outputs": [("out", "OUT", "control output")],
            "width": 80,
            "height": 60,
        },
        "parameters": {
            "kp": {"type": "float", "default": 1.0, "range": [0, 1000], "unit": ""},
            "ki": {"type": "float", "default": 0.0, "range": [0, 1000], "unit": "1/s"},
            "kd": {"type": "float", "default": 0.0, "range": [0, 100], "unit": "s"},
            "output_min": {"type": "float", "default": -1.0, "range": [-1e6, 1e6], "unit": ""},
            "output_max": {"type": "float", "default": 1.0, "range": [-1e6, 1e6], "unit": ""},
            "d_filter_coeff": {"type": "float", "default": 100.0, "range": [1, 1000], "unit": "Hz"},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "PID",  # Direct firmware support
            "max_slots": 8,
            "feature_flag": None,  # Always available
        },
        "state_space": None,  # Direct PID, no state-space conversion
    },

    # -------------------------------------------------------------------------
    # LQR Controller (Linear Quadratic Regulator)
    # -------------------------------------------------------------------------
    "lqr": {
        "category": "controller",
        "gui": {
            "label": "LQR",
            "color": "#8B5CF6",
            "description": "Linear Quadratic Regulator",
            "inputs": [("ref", "REF", "state reference"), ("state", "STATE", "state estimate")],
            "outputs": [("out", "OUT", "control output")],
            "width": 80,
            "height": 60,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 2, "range": [1, 8], "unit": ""},
            "num_inputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "K": {"type": "matrix", "default": [], "description": "State feedback gain (row-major)"},
            "Q": {"type": "matrix", "default": [], "description": "State cost (for design, not runtime)"},
            "R": {"type": "matrix", "default": [], "description": "Input cost (for design, not runtime)"},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "max_slots": 8,
            "feature_flag": None,
        },
        "state_space": {
            "description": "u = -K(x - x_ref)",
            "derive_fn": "derive_lqr_state_space",
        },
    },

    # -------------------------------------------------------------------------
    # Kalman Filter + LQG Controller
    # -------------------------------------------------------------------------
    "kalman_lqg": {
        "category": "controller",
        "gui": {
            "label": "Kalman/LQG",
            "color": "#22C55E",
            "description": "Kalman filter with LQR control (LQG)",
            "inputs": [
                ("ref", "REF", "state reference"),
                ("u", "U", "control input (for prediction)"),
                ("y", "Y", "measurement"),
            ],
            "outputs": [
                ("x_hat", "X̂", "state estimate"),
                ("out", "OUT", "control output"),
            ],
            "width": 100,
            "height": 80,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 2, "range": [1, 8], "unit": ""},
            "num_inputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "num_outputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "A": {"type": "matrix", "default": [], "description": "State transition matrix"},
            "B": {"type": "matrix", "default": [], "description": "Input matrix"},
            "C": {"type": "matrix", "default": [], "description": "Output matrix"},
            "K": {"type": "matrix", "default": [], "description": "LQR gain"},
            "L": {"type": "matrix", "default": [], "description": "Kalman gain"},
            "Q_process": {"type": "matrix", "default": [], "description": "Process noise covariance"},
            "R_meas": {"type": "matrix", "default": [], "description": "Measurement noise covariance"},
            "controller_slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
            "observer_slot": {"type": "int", "default": 0, "range": [0, 3], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER+OBSERVER",
            "maps_to": ["STATE_SPACE", "OBSERVER"],
            "uses_controller_slot": True,
            "uses_observer_slot": True,
            "feature_flag": None,
        },
        "state_space": {
            "description": "Combined Kalman observer + LQR controller",
            "derive_fn": "derive_kalman_lqg",
        },
    },

    # -------------------------------------------------------------------------
    # State-Space Controller (Generic)
    # -------------------------------------------------------------------------
    "state_space": {
        "category": "controller",
        "gui": {
            "label": "State-Space",
            "color": "#EC4899",
            "description": "Generic state-space controller",
            "inputs": [("x", "X", "state input")],
            "outputs": [("out", "OUT", "control output")],
            "width": 90,
            "height": 60,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 2, "range": [1, 8], "unit": ""},
            "num_inputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "A": {"type": "matrix", "default": [], "description": "State matrix (n×n)"},
            "B": {"type": "matrix", "default": [], "description": "Input matrix (n×m)"},
            "C": {"type": "matrix", "default": [], "description": "Output matrix (p×n)"},
            "D": {"type": "matrix", "default": [], "description": "Feedthrough matrix (p×m)"},
            "K": {"type": "matrix", "default": [], "description": "Feedback gain (m×n)"},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "max_slots": 8,
            "feature_flag": None,
        },
        "state_space": {
            "description": "Direct state-space: dx = Ax + Bu, y = Cx + Du",
            "derive_fn": None,  # Direct use, no derivation
        },
    },

    # -------------------------------------------------------------------------
    # Cascade PID Controller
    # -------------------------------------------------------------------------
    "cascade_pid": {
        "category": "controller",
        "gui": {
            "label": "Cascade PID",
            "color": "#F59E0B",
            "description": "Cascaded inner/outer PID loops",
            "inputs": [
                ("ref", "REF", "outer reference"),
                ("outer_meas", "OUTER", "outer measurement"),
                ("inner_meas", "INNER", "inner measurement"),
            ],
            "outputs": [("out", "OUT", "control output")],
            "width": 120,
            "height": 70,
        },
        "parameters": {
            "outer_kp": {"type": "float", "default": 1.0, "range": [0, 1000], "unit": ""},
            "outer_ki": {"type": "float", "default": 0.1, "range": [0, 1000], "unit": "1/s"},
            "outer_kd": {"type": "float", "default": 0.0, "range": [0, 100], "unit": "s"},
            "inner_kp": {"type": "float", "default": 5.0, "range": [0, 1000], "unit": ""},
            "inner_ki": {"type": "float", "default": 0.5, "range": [0, 1000], "unit": "1/s"},
            "inner_kd": {"type": "float", "default": 0.0, "range": [0, 100], "unit": "s"},
            "inner_output_min": {"type": "float", "default": -1.0, "unit": ""},
            "inner_output_max": {"type": "float", "default": 1.0, "unit": ""},
            "outer_slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
            "inner_slot": {"type": "int", "default": 1, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "PID",  # Uses 2 PID slots
            "uses_slots": 2,
            "feature_flag": None,
        },
        "state_space": None,  # Uses native PID slots
    },

    # -------------------------------------------------------------------------
    # Model Predictive Controller (MPC) - Simplified
    # -------------------------------------------------------------------------
    "mpc": {
        "category": "controller",
        "gui": {
            "label": "MPC",
            "color": "#06B6D4",
            "description": "Model Predictive Controller (simplified)",
            "inputs": [("ref", "REF", "reference trajectory"), ("state", "STATE", "current state")],
            "outputs": [("out", "OUT", "optimal control")],
            "width": 80,
            "height": 60,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 2, "range": [1, 4], "unit": ""},
            "num_inputs": {"type": "int", "default": 1, "range": [1, 2], "unit": ""},
            "horizon": {"type": "int", "default": 10, "range": [1, 50], "unit": "steps"},
            "A": {"type": "matrix", "default": [], "description": "State transition"},
            "B": {"type": "matrix", "default": [], "description": "Input matrix"},
            "Q": {"type": "matrix", "default": [], "description": "State cost"},
            "R": {"type": "matrix", "default": [], "description": "Input cost"},
            "u_min": {"type": "float", "default": -1.0, "unit": ""},
            "u_max": {"type": "float", "default": 1.0, "unit": ""},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",  # Approximated as state-space
            "feature_flag": "HAS_MPC",  # Optional firmware feature
            "warning": "MPC runs as state-space approximation on MCU (limited horizon)",
        },
        "state_space": {
            "description": "Precomputed MPC as state-feedback gain",
            "derive_fn": "derive_mpc_gain",
        },
    },

    # -------------------------------------------------------------------------
    # Feedforward Controller
    # -------------------------------------------------------------------------
    "feedforward": {
        "category": "controller",
        "gui": {
            "label": "Feedforward",
            "color": "#A855F7",
            "description": "Feedforward control (model inverse)",
            "inputs": [("ref", "REF", "reference")],
            "outputs": [("out", "OUT", "feedforward output")],
            "width": 90,
            "height": 50,
        },
        "parameters": {
            "gain": {"type": "float", "default": 1.0, "range": [0, 1000], "unit": ""},
            "velocity_gain": {"type": "float", "default": 0.0, "range": [0, 100], "unit": "s"},
            "accel_gain": {"type": "float", "default": 0.0, "range": [0, 10], "unit": "s²"},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "feature_flag": None,
        },
        "state_space": {
            "description": "FF as state-space with derivative filter",
            "derive_fn": "derive_feedforward_state_space",
        },
    },
}

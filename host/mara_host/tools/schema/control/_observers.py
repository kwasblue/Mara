# schema/control/_observers.py
"""
Observer block definitions - SINGLE SOURCE OF TRUTH.

Adding a new observer (3 steps):
    1. Add entry to OBSERVER_BLOCKS below
    2. Run: mara generate all
    3. Implement firmware if needed (most map to Luenberger)

Each observer entry defines:
    - category: "observer" (required)
    - gui: {label, color, inputs, outputs, description} - Block diagram appearance
    - parameters: {param_name: {type, default, range, unit}} - Configurable params
    - firmware: {slot_type, maps_to} - Firmware mapping
    - state_space: {derive_fn} - How to derive observer matrices

See docs/ADDING_CONTROL.md for full guide.
"""

from typing import Any

OBSERVER_BLOCKS: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Luenberger Observer (State Observer)
    # -------------------------------------------------------------------------
    "observer": {
        "category": "observer",
        "gui": {
            "label": "Observer",
            "color": "#22C55E",
            "description": "Luenberger state observer",
            "inputs": [("u", "U", "control input"), ("y", "Y", "measurement")],
            "outputs": [("x_hat", "X̂", "state estimate")],
            "width": 80,
            "height": 60,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 2, "range": [1, 8], "unit": ""},
            "num_inputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "num_outputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "A": {"type": "matrix", "default": [], "description": "State matrix"},
            "B": {"type": "matrix", "default": [], "description": "Input matrix"},
            "C": {"type": "matrix", "default": [], "description": "Output matrix"},
            "L": {"type": "matrix", "default": [], "description": "Observer gain"},
            "rate_hz": {"type": "int", "default": 200, "range": [10, 1000], "unit": "Hz"},
            "slot": {"type": "int", "default": 0, "range": [0, 3], "unit": ""},
        },
        "firmware": {
            "slot_type": "OBSERVER",
            "maps_to": "LUENBERGER",
            "max_slots": 4,
            "feature_flag": None,
        },
        "state_space": {
            "description": "x̂_dot = Ax̂ + Bu + L(y - Cx̂)",
            "derive_fn": None,  # Direct observer
        },
    },

    # -------------------------------------------------------------------------
    # Kalman Filter
    # -------------------------------------------------------------------------
    "kalman": {
        "category": "observer",
        "gui": {
            "label": "Kalman",
            "color": "#14B8A6",
            "description": "Kalman filter (optimal observer)",
            "inputs": [("u", "U", "control input"), ("y", "Y", "measurement")],
            "outputs": [("x_hat", "X̂", "state estimate"), ("P", "P", "covariance")],
            "width": 80,
            "height": 70,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 2, "range": [1, 8], "unit": ""},
            "num_inputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "num_outputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "A": {"type": "matrix", "default": [], "description": "State matrix"},
            "B": {"type": "matrix", "default": [], "description": "Input matrix"},
            "C": {"type": "matrix", "default": [], "description": "Output matrix"},
            "Q": {"type": "matrix", "default": [], "description": "Process noise covariance"},
            "R": {"type": "matrix", "default": [], "description": "Measurement noise covariance"},
            "rate_hz": {"type": "int", "default": 200, "range": [10, 1000], "unit": "Hz"},
            "slot": {"type": "int", "default": 0, "range": [0, 3], "unit": ""},
        },
        "firmware": {
            "slot_type": "OBSERVER",
            "maps_to": "LUENBERGER",  # Computed L gain at init
            "feature_flag": None,
            "note": "Steady-state Kalman gain precomputed, runs as Luenberger",
        },
        "state_space": {
            "description": "Kalman with precomputed steady-state gain L",
            "derive_fn": "derive_kalman_gain",
        },
    },

    # -------------------------------------------------------------------------
    # Extended Kalman Filter (EKF)
    # -------------------------------------------------------------------------
    "ekf": {
        "category": "observer",
        "gui": {
            "label": "EKF",
            "color": "#F59E0B",
            "description": "Extended Kalman Filter (nonlinear)",
            "inputs": [("u", "U", "control input"), ("y", "Y", "measurement")],
            "outputs": [("x_hat", "X̂", "state estimate")],
            "width": 80,
            "height": 60,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 3, "range": [1, 8], "unit": ""},
            "num_inputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "num_outputs": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "f_model": {"type": "string", "default": "linear", "description": "State transition model ID"},
            "h_model": {"type": "string", "default": "linear", "description": "Measurement model ID"},
            "Q": {"type": "matrix", "default": [], "description": "Process noise covariance"},
            "R": {"type": "matrix", "default": [], "description": "Measurement noise covariance"},
            "rate_hz": {"type": "int", "default": 200, "range": [10, 1000], "unit": "Hz"},
            "slot": {"type": "int", "default": 0, "range": [0, 3], "unit": ""},
        },
        "firmware": {
            "slot_type": "OBSERVER",
            "maps_to": "LUENBERGER",  # Linearized around operating point
            "feature_flag": "HAS_EKF",
            "warning": "EKF linearized at operating point for MCU",
        },
        "state_space": {
            "description": "EKF linearized to Luenberger at operating point",
            "derive_fn": "derive_ekf_linearized",
        },
    },

    # -------------------------------------------------------------------------
    # Complementary Filter
    # -------------------------------------------------------------------------
    "complementary": {
        "category": "observer",
        "gui": {
            "label": "Comp. Filter",
            "color": "#EC4899",
            "description": "Complementary filter (sensor fusion)",
            "inputs": [
                ("gyro", "GYRO", "gyroscope (high freq)"),
                ("accel", "ACCEL", "accelerometer (low freq)"),
            ],
            "outputs": [("angle", "θ", "fused angle")],
            "width": 100,
            "height": 60,
        },
        "parameters": {
            "alpha": {"type": "float", "default": 0.98, "range": [0, 1], "description": "Gyro weight"},
            "dt": {"type": "float", "default": 0.01, "range": [0.001, 0.1], "unit": "s"},
            "slot": {"type": "int", "default": 0, "range": [0, 3], "unit": ""},
        },
        "firmware": {
            "slot_type": "OBSERVER",
            "maps_to": "LUENBERGER",
            "feature_flag": None,
        },
        "state_space": {
            "description": "angle = alpha * (angle + gyro*dt) + (1-alpha) * accel_angle",
            "derive_fn": "derive_complementary_state_space",
        },
    },

    # -------------------------------------------------------------------------
    # Velocity Observer (from Position)
    # -------------------------------------------------------------------------
    "velocity_observer": {
        "category": "observer",
        "gui": {
            "label": "Velocity Est.",
            "color": "#8B5CF6",
            "description": "Velocity estimator from position",
            "inputs": [("pos", "POS", "position measurement")],
            "outputs": [("vel", "VEL", "velocity estimate")],
            "width": 90,
            "height": 50,
        },
        "parameters": {
            "filter_hz": {"type": "float", "default": 20.0, "range": [1, 100], "unit": "Hz"},
            "rate_hz": {"type": "int", "default": 200, "range": [10, 1000], "unit": "Hz"},
            "slot": {"type": "int", "default": 0, "range": [0, 3], "unit": ""},
        },
        "firmware": {
            "slot_type": "OBSERVER",
            "maps_to": "LUENBERGER",
            "feature_flag": None,
        },
        "state_space": {
            "description": "2-state observer: [pos, vel], measure pos, estimate vel",
            "derive_fn": "derive_velocity_observer",
        },
    },

    # -------------------------------------------------------------------------
    # Disturbance Observer
    # -------------------------------------------------------------------------
    "disturbance_observer": {
        "category": "observer",
        "gui": {
            "label": "DOB",
            "color": "#EF4444",
            "description": "Disturbance observer",
            "inputs": [("u", "U", "control input"), ("y", "Y", "output measurement")],
            "outputs": [("d_hat", "D̂", "disturbance estimate")],
            "width": 80,
            "height": 60,
        },
        "parameters": {
            "num_states": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "bandwidth_hz": {"type": "float", "default": 10.0, "range": [1, 100], "unit": "Hz"},
            "plant_gain": {"type": "float", "default": 1.0, "description": "Nominal plant DC gain"},
            "slot": {"type": "int", "default": 0, "range": [0, 3], "unit": ""},
        },
        "firmware": {
            "slot_type": "OBSERVER",
            "maps_to": "LUENBERGER",
            "feature_flag": None,
        },
        "state_space": {
            "description": "Augmented state observer with disturbance state",
            "derive_fn": "derive_disturbance_observer",
        },
    },
}

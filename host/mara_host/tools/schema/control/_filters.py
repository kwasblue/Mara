# schema/control/_filters.py
"""
Filter and signal processing block definitions - SINGLE SOURCE OF TRUTH.

Adding a new filter (3 steps):
    1. Add entry to FILTER_BLOCKS below
    2. Run: mara generate all
    3. Firmware auto-generates (all filters map to state-space)

Each filter entry defines:
    - category: "filter" | "signal" (required)
    - gui: {label, color, inputs, outputs, description} - Block diagram appearance
    - parameters: {param_name: {type, default, range, unit}} - Configurable params
    - firmware: {slot_type, maps_to} - Firmware mapping
    - state_space: {derive_fn} - How to derive state-space matrices

See docs/ADDING_CONTROL.md for full guide.
"""

from typing import Any

FILTER_BLOCKS: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # SIGNAL BLOCKS
    # -------------------------------------------------------------------------
    "signal_source": {
        "category": "signal",
        "gui": {
            "label": "Signal",
            "color": "#3B82F6",
            "description": "Signal source (reference input)",
            "inputs": [],
            "outputs": [("out", "OUT", "signal output")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "signal_id": {"type": "int", "default": 0, "range": [0, 31], "unit": ""},
            "initial_value": {"type": "float", "default": 0.0, "unit": ""},
        },
        "firmware": {
            "slot_type": "SIGNAL_BUS",
            "maps_to": "SIGNAL",
            "feature_flag": None,
        },
        "state_space": None,  # Signal routing only
    },

    "signal_sink": {
        "category": "signal",
        "gui": {
            "label": "Output",
            "color": "#F59E0B",
            "description": "Signal sink (output)",
            "inputs": [("in", "IN", "signal input")],
            "outputs": [],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "signal_id": {"type": "int", "default": 0, "range": [0, 31], "unit": ""},
        },
        "firmware": {
            "slot_type": "SIGNAL_BUS",
            "maps_to": "SIGNAL",
            "feature_flag": None,
        },
        "state_space": None,  # Signal routing only
    },

    "sum": {
        "category": "signal",
        "gui": {
            "label": "Sum",
            "color": "#71717A",
            "description": "Summing junction",
            "inputs": [("in0", "+", "input 0"), ("in1", "-", "input 1")],
            "outputs": [("out", "OUT", "sum output")],
            "width": 40,
            "height": 40,
            "shape": "circle",
        },
        "parameters": {
            "signs": {"type": "list", "default": ["+", "-"], "description": "Input signs"},
        },
        "firmware": {
            "slot_type": "SIGNAL_BUS",
            "maps_to": "SUM",
            "feature_flag": None,
            "note": "Handled via signal bus routing",
        },
        "state_space": None,  # Signal routing only
    },

    "gain": {
        "category": "signal",
        "gui": {
            "label": "Gain",
            "color": "#8B5CF6",
            "description": "Scalar gain",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "output")],
            "width": 50,
            "height": 40,
            "shape": "triangle",
        },
        "parameters": {
            "gain": {"type": "float", "default": 1.0, "range": [-1e6, 1e6], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",  # Uses slot if gain != 1
            "maps_to": "STATE_SPACE",
            "feature_flag": None,
            "note": "Unity gain uses no slot; other gains use state-space with C=K",
        },
        "state_space": {
            "description": "y = K * u (pass-through with gain)",
            "derive_fn": "derive_gain_state_space",
        },
    },

    # -------------------------------------------------------------------------
    # DYNAMIC BLOCKS
    # -------------------------------------------------------------------------
    "integrator": {
        "category": "filter",
        "gui": {
            "label": "Integrator",
            "color": "#14B8A6",
            "description": "Integration (1/s)",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "integral")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "gain": {"type": "float", "default": 1.0, "range": [0, 1000], "unit": ""},
            "limit_min": {"type": "float", "default": -1000.0, "unit": ""},
            "limit_max": {"type": "float", "default": 1000.0, "unit": ""},
            "initial_state": {"type": "float", "default": 0.0, "unit": ""},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "feature_flag": None,
        },
        "state_space": {
            "description": "dx/dt = u, y = K*x (pure integrator)",
            "A": [0.0],
            "B": [1.0],
            "C_expr": "gain",
            "derive_fn": "derive_integrator_state_space",
        },
    },

    "derivative": {
        "category": "filter",
        "gui": {
            "label": "Derivative",
            "color": "#EC4899",
            "description": "Filtered derivative (s with filter)",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "derivative")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "gain": {"type": "float", "default": 1.0, "range": [0, 1000], "unit": ""},
            "filter_coeff": {"type": "float", "default": 100.0, "range": [1, 1000], "unit": "rad/s"},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "feature_flag": None,
        },
        "state_space": {
            "description": "Filtered derivative: H(s) = K*s/(1 + s/N)",
            "A_expr": "-N",
            "B_expr": "N",
            "C_expr": "gain",
            "derive_fn": "derive_derivative_state_space",
        },
    },

    # -------------------------------------------------------------------------
    # FILTERS
    # -------------------------------------------------------------------------
    "filter": {
        "category": "filter",
        "gui": {
            "label": "Filter",
            "color": "#A855F7",
            "description": "Low-pass filter",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "filtered")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "cutoff_freq": {"type": "float", "default": 10.0, "range": [0.1, 1000], "unit": "Hz"},
            "order": {"type": "int", "default": 1, "range": [1, 4], "unit": ""},
            "filter_type": {"type": "string", "default": "lowpass", "options": ["lowpass", "highpass"]},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "feature_flag": None,
        },
        "state_space": {
            "description": "1st order LP: H(s) = wc/(s + wc)",
            "derive_fn": "derive_filter_state_space",
        },
    },

    "notch_filter": {
        "category": "filter",
        "gui": {
            "label": "Notch",
            "color": "#06B6D4",
            "description": "Notch filter (band-reject)",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "filtered")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "center_freq": {"type": "float", "default": 50.0, "range": [1, 500], "unit": "Hz"},
            "bandwidth": {"type": "float", "default": 5.0, "range": [0.1, 100], "unit": "Hz"},
            "depth_db": {"type": "float", "default": -40.0, "range": [-60, 0], "unit": "dB"},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "feature_flag": None,
            "note": "2nd order state-space",
        },
        "state_space": {
            "description": "2nd order notch filter",
            "derive_fn": "derive_notch_state_space",
        },
    },

    "moving_average": {
        "category": "filter",
        "gui": {
            "label": "Moving Avg",
            "color": "#22C55E",
            "description": "Moving average filter",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "averaged")],
            "width": 70,
            "height": 40,
        },
        "parameters": {
            "window_size": {"type": "int", "default": 5, "range": [2, 50], "unit": "samples"},
            "slot": {"type": "int", "default": 0, "range": [0, 7], "unit": ""},
        },
        "firmware": {
            "slot_type": "CONTROLLER",
            "maps_to": "STATE_SPACE",
            "feature_flag": None,
            "warning": "Approximated as 1st order LP with matched bandwidth",
        },
        "state_space": {
            "description": "MA approximated as LP with fc = fs/(2*pi*N)",
            "derive_fn": "derive_moving_avg_state_space",
        },
    },

    # -------------------------------------------------------------------------
    # NONLINEAR BLOCKS
    # -------------------------------------------------------------------------
    "saturation": {
        "category": "filter",
        "gui": {
            "label": "Saturation",
            "color": "#EF4444",
            "description": "Output limiter",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "limited")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "lower": {"type": "float", "default": -1.0, "unit": ""},
            "upper": {"type": "float", "default": 1.0, "unit": ""},
        },
        "firmware": {
            "slot_type": None,  # No dedicated slot
            "maps_to": "OUTPUT_LIMITS",
            "feature_flag": None,
            "warning": "Apply via controller output_min/output_max instead",
        },
        "state_space": None,  # Not a linear system
    },

    "deadzone": {
        "category": "filter",
        "gui": {
            "label": "Deadzone",
            "color": "#F97316",
            "description": "Deadzone nonlinearity",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "output")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "lower": {"type": "float", "default": -0.1, "unit": ""},
            "upper": {"type": "float", "default": 0.1, "unit": ""},
        },
        "firmware": {
            "slot_type": None,
            "maps_to": None,
            "feature_flag": "HAS_DEADZONE",
            "warning": "Not directly supported on MCU; handle in host post-processing",
        },
        "state_space": None,  # Not a linear system
    },

    "rate_limiter": {
        "category": "filter",
        "gui": {
            "label": "Rate Limit",
            "color": "#EAB308",
            "description": "Rate of change limiter",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "rate-limited")],
            "width": 70,
            "height": 40,
        },
        "parameters": {
            "rising_rate": {"type": "float", "default": 10.0, "range": [0.1, 1000], "unit": "1/s"},
            "falling_rate": {"type": "float", "default": 10.0, "range": [0.1, 1000], "unit": "1/s"},
        },
        "firmware": {
            "slot_type": None,
            "maps_to": None,
            "feature_flag": None,
            "warning": "Handle via signal bus rate limiting or host-side",
        },
        "state_space": None,  # Not a linear system
    },

    # -------------------------------------------------------------------------
    # DELAY BLOCKS
    # -------------------------------------------------------------------------
    "delay": {
        "category": "filter",
        "gui": {
            "label": "Delay",
            "color": "#F97316",
            "description": "Time delay",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "delayed")],
            "width": 60,
            "height": 40,
        },
        "parameters": {
            "delay_time": {"type": "float", "default": 0.1, "range": [0.001, 10], "unit": "s"},
        },
        "firmware": {
            "slot_type": None,
            "maps_to": None,
            "feature_flag": None,
            "warning": "Pure delays require buffer memory; not directly supported",
        },
        "state_space": {
            "description": "Padé approximation for small delays",
            "derive_fn": "derive_delay_pade",
        },
    },

    "transport_delay": {
        "category": "filter",
        "gui": {
            "label": "Transport",
            "color": "#D946EF",
            "description": "Transport delay (discrete samples)",
            "inputs": [("in", "IN", "input")],
            "outputs": [("out", "OUT", "delayed")],
            "width": 70,
            "height": 40,
        },
        "parameters": {
            "samples": {"type": "int", "default": 10, "range": [1, 100], "unit": "samples"},
        },
        "firmware": {
            "slot_type": None,
            "maps_to": None,
            "feature_flag": "HAS_TRANSPORT_DELAY",
            "warning": "Requires circular buffer; limited MCU support",
        },
        "state_space": None,  # Discrete buffer, not continuous state-space
    },
}

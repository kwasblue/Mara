# Adding Control Blocks to MARA

This guide explains how to add new control blocks (controllers, observers, filters) to MARA using the single-file registry pattern.

## Quick Start: Adding a New Controller

**Example: Adding a Lead-Lag Compensator**

1. Edit `host/mara_host/tools/schema/control/_controllers.py`:

```python
"lead_lag": {
    "category": "controller",
    "gui": {
        "label": "Lead-Lag",
        "color": "#10B981",
        "description": "Lead-lag compensator",
        "inputs": [("in", "IN", "input")],
        "outputs": [("out", "OUT", "output")],
        "width": 70,
        "height": 50,
    },
    "parameters": {
        "lead_zero": {"type": "float", "default": 1.0, "unit": "rad/s"},
        "lead_pole": {"type": "float", "default": 10.0, "unit": "rad/s"},
        "lag_zero": {"type": "float", "default": 0.1, "unit": "rad/s"},
        "lag_pole": {"type": "float", "default": 0.01, "unit": "rad/s"},
        "gain": {"type": "float", "default": 1.0},
        "slot": {"type": "int", "default": 0, "range": [0, 7]},
    },
    "firmware": {
        "slot_type": "CONTROLLER",
        "maps_to": "STATE_SPACE",
    },
    "state_space": {
        "description": "Lead-lag as 2nd order state-space",
        "derive_fn": "derive_lead_lag_state_space",
    },
},
```

2. Add the derivation function to `_derive.py`:

```python
def derive_lead_lag_state_space(params: dict) -> dict[str, list[float]]:
    """Lead-lag compensator: H(s) = K * (s + z1)/(s + p1) * (s + z2)/(s + p2)"""
    z1 = params.get("lead_zero", 1.0)
    p1 = params.get("lead_pole", 10.0)
    z2 = params.get("lag_zero", 0.1)
    p2 = params.get("lag_pole", 0.01)
    K = params.get("gain", 1.0)

    # 2nd order state-space in controllable canonical form
    A = [0.0, 1.0, -p1*p2, -(p1+p2)]
    B = [0.0, 1.0]
    C = [K*(z1*z2 - p1*p2), K*(z1+z2 - p1-p2)]

    return {"A": A, "B": B, "C": C, "K": [0.0, 0.0]}
```

3. Run the generator:

```bash
cd host/mara_host/tools && python3 gen_control_blocks.py
```

4. Your block now appears in the GUI palette and is auto-mapped to firmware!

## Registry Structure

### Control Registry Files

```
host/mara_host/tools/schema/control/
├── __init__.py           # Main registry, merges all categories
├── _controllers.py       # Controllers: PID, LQR, MPC, etc.
├── _observers.py         # Observers: Kalman, EKF, DOB, etc.
├── _filters.py           # Filters: LP, HP, Notch, etc.
└── _derive.py            # State-space derivation functions
```

### Block Configuration Schema

```python
"block_name": {
    "category": "controller" | "observer" | "filter" | "signal",

    "gui": {
        "label": "Display Name",
        "color": "#HEXCOLOR",
        "description": "Tooltip text",
        "inputs": [("port_id", "LABEL", "description"), ...],
        "outputs": [("port_id", "LABEL", "description"), ...],
        "width": 80,   # pixels
        "height": 60,  # pixels
    },

    "parameters": {
        "param_name": {
            "type": "float" | "int" | "string" | "matrix" | "list",
            "default": value,
            "range": [min, max],  # optional
            "unit": "unit_string",  # optional
            "description": "...",  # optional
        },
    },

    "firmware": {
        "slot_type": "CONTROLLER" | "OBSERVER" | "SIGNAL_BUS" | None,
        "maps_to": "PID" | "STATE_SPACE" | "LUENBERGER" | None,
        "max_slots": 8,  # optional
        "feature_flag": "HAS_FEATURE",  # optional
        "warning": "...",  # optional, shown in UI
    },

    "state_space": {
        "description": "Mathematical description",
        "derive_fn": "derive_block_name",  # Function name in _derive.py
    },
}
```

## Categories

### Controllers (`_controllers.py`)
- Use `slot_type: "CONTROLLER"`
- Map to either `"PID"` (native) or `"STATE_SPACE"`
- 8 slots available (0-7)

**Built-in controllers:**
- `pid` - PID with anti-windup
- `lqr` - Linear Quadratic Regulator
- `kalman_lqg` - Combined Kalman + LQR
- `state_space` - Generic state-space
- `cascade_pid` - Nested PID loops (uses 2 slots)
- `mpc` - Model Predictive Control (approximated)
- `feedforward` - Feedforward compensation

### Observers (`_observers.py`)
- Use `slot_type: "OBSERVER"`
- Map to `"LUENBERGER"` (all observers run as Luenberger on MCU)
- 4 slots available (0-3)

**Built-in observers:**
- `observer` - Luenberger state observer
- `kalman` - Kalman filter (precomputed gain)
- `ekf` - Extended Kalman (linearized)
- `complementary` - Complementary filter (sensor fusion)
- `velocity_observer` - Velocity from position
- `disturbance_observer` - Disturbance estimation

### Filters (`_filters.py`)
- Most use `slot_type: "CONTROLLER"` with `STATE_SPACE`
- Nonlinear blocks (saturation, deadzone) have `slot_type: None`

**Built-in filters:**
- `integrator` - Integration (1/s)
- `derivative` - Filtered derivative
- `filter` - Low-pass/high-pass
- `notch_filter` - Band-reject
- `moving_average` - MA (approximated)
- `saturation` - Output limiter (use controller limits)
- `deadzone` - Dead-band
- `rate_limiter` - Slew rate limiting
- `delay` - Time delay (Padé approximation)

## State-Space Mapping

GUI blocks are mapped to firmware via state-space representation:

```
dx/dt = Ax + Bu    (state equation)
y = Cx + Du        (output equation)
```

For controllers: `u = -Kx` (state feedback)
For observers: `x̂_dot = Ax̂ + Bu + L(y - Cx̂)` (observer with gain L)

### Derivation Functions

Add to `_derive.py`:

```python
def derive_my_block_state_space(params: dict) -> dict[str, list[float]]:
    """
    Derive state-space matrices from block parameters.

    Returns dict with keys: A, B, C, D, K (for controllers)
                        or: A, B, C, L (for observers)
    Matrices are flat lists in row-major order.
    """
    # Your math here
    return {
        "A": [...],  # n×n flattened
        "B": [...],  # n×m flattened
        "C": [...],  # p×n flattened
        "K": [...],  # m×n flattened (controllers)
        # or "L": [...] for observers
    }
```

Register in `DERIVE_FUNCTIONS`:

```python
DERIVE_FUNCTIONS = {
    # ...existing...
    "derive_my_block_state_space": derive_my_block_state_space,
}
```

## Firmware Integration

### Slot Limits
- Controllers: 8 slots (0-7)
- Observers: 4 slots (0-3)

### Blocks Without Direct Firmware Support

Some blocks can't run on the MCU:

1. **Saturation/Deadzone** - Use controller `output_min`/`output_max`
2. **Pure delays** - Require buffer memory; use Padé approximation or host-side
3. **Nonlinear blocks** - Handle in host post-processing

Add warnings in `firmware.warning` to inform users.

## Generated Files

Running `mara generate control` creates:

```
host/mara_host/gui/widgets/block_diagram/
├── blocks/_generated.py           # Block classes
└── diagrams/_generated_palette.py  # Palette entries
```

## Testing

After adding a block:

```bash
# Verify syntax
python3 -m py_compile mara_host/tools/schema/control/_controllers.py

# Generate blocks
cd host/mara_host/tools && python3 gen_control_blocks.py

# Run GUI to verify
mara gui
```

## Example: Adding a Notch Filter

Full example of adding a second-order notch filter:

```python
# In _filters.py
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
        "slot": {"type": "int", "default": 0, "range": [0, 7]},
    },
    "firmware": {
        "slot_type": "CONTROLLER",
        "maps_to": "STATE_SPACE",
        "note": "2nd order state-space",
    },
    "state_space": {
        "description": "2nd order notch filter",
        "derive_fn": "derive_notch_state_space",
    },
},
```

```python
# In _derive.py
def derive_notch_state_space(params: dict) -> dict[str, list[float]]:
    """
    Notch filter: H(s) = (s² + wn²) / (s² + (wn/Q)*s + wn²)
    """
    f_center = params.get("center_freq", 50.0)
    bandwidth = params.get("bandwidth", 5.0)

    wn = 2 * math.pi * f_center
    Q = f_center / bandwidth

    # 2nd order state-space
    A = [0.0, 1.0, -wn*wn, -wn/Q]
    B = [0.0, 1.0]
    C = [wn*wn, -wn/Q]
    D = [1.0]

    return {"A": A, "B": B, "C": C, "D": D, "K": [0.0, 0.0]}
```

That's it! The notch filter is now available in the GUI and automatically maps to firmware.

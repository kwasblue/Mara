# mara_host/gui/widgets/block_diagram/core/block_mapping.py
"""
Block-to-Firmware Mapping

Maps GUI block configurations to firmware primitives.
The firmware supports:
  - 8 Controller slots (PID or State-Space)
  - 4 Observer slots (Luenberger)
  - Signal bus for routing

GUI blocks that don't have direct firmware equivalents are mapped to
state-space representations or composed from primitives.

Block definitions are loaded from the control registry:
  - tools/schema/control/_controllers.py
  - tools/schema/control/_observers.py
  - tools/schema/control/_filters.py

To add a new control block:
  1. Add entry to the appropriate registry file
  2. Run: mara generate control
  3. The block will be available in GUI and auto-mapped to firmware
"""

from dataclasses import dataclass, field
from typing import Optional
import math

# Import control registry and derivation functions
try:
    from mara_host.tools.schema.control import CONTROL_BLOCKS, get_block_config
    from mara_host.tools.schema.control._derive import derive_state_space, DERIVE_FUNCTIONS
    HAS_CONTROL_REGISTRY = True
except ImportError:
    HAS_CONTROL_REGISTRY = False
    CONTROL_BLOCKS = {}
    get_block_config = lambda x: None
    derive_state_space = lambda x, y: None


@dataclass
class SignalConfig:
    """Signal bus signal configuration."""
    signal_id: int
    name: str
    kind: str = "SIGNAL"  # REF, MEAS, OUT, EST, SIGNAL
    initial: float = 0.0


@dataclass
class ControllerSlotConfig:
    """Firmware controller slot configuration."""
    slot: int
    controller_type: str  # "PID" or "STATE_SPACE"
    rate_hz: int = 100

    # Signal routing
    ref_ids: list[int] = field(default_factory=list)
    meas_ids: list[int] = field(default_factory=list)
    state_ids: list[int] = field(default_factory=list)
    output_ids: list[int] = field(default_factory=list)

    # PID params
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    out_min: float = -1.0
    out_max: float = 1.0

    # State-space params (matrices as flat lists, row-major)
    num_states: int = 1
    num_inputs: int = 1
    A: list[float] = field(default_factory=list)
    B: list[float] = field(default_factory=list)
    C: list[float] = field(default_factory=list)
    K: list[float] = field(default_factory=list)

    require_armed: bool = True
    require_active: bool = True


@dataclass
class ObserverSlotConfig:
    """Firmware observer slot configuration."""
    slot: int
    num_states: int
    num_inputs: int
    num_outputs: int
    rate_hz: int = 200

    # Signal routing
    input_ids: list[int] = field(default_factory=list)
    output_ids: list[int] = field(default_factory=list)
    estimate_ids: list[int] = field(default_factory=list)

    # Matrices (flat, row-major)
    A: list[float] = field(default_factory=list)
    B: list[float] = field(default_factory=list)
    C: list[float] = field(default_factory=list)
    L: list[float] = field(default_factory=list)


class BlockMapper:
    """
    Maps GUI diagram blocks to firmware configurations.

    Block Type Mapping:
    - pid: Direct → Firmware PID slot
    - observer: Direct → Firmware Observer slot
    - integrator: Mapped → State-space [A=0, B=K, C=1]
    - derivative: Mapped → State-space with filter
    - saturation: Note → Use controller output limits
    - filter: Mapped → State-space 1st order LP
    - delay: Note → Not directly supported, use signal timing
    - gain: Note → Typically inline or state-space C matrix
    - sum: Note → Signal bus summing (handled in routing)
    """

    def __init__(self):
        self._next_signal_id = 100  # Start signal IDs at 100
        self._next_controller_slot = 0
        self._next_observer_slot = 0
        self._signals: dict[str, SignalConfig] = {}
        self._controller_configs: list[ControllerSlotConfig] = []
        self._observer_configs: list[ObserverSlotConfig] = []
        self._warnings: list[str] = []

    def allocate_signal(self, name: str, kind: str = "SIGNAL", initial: float = 0.0) -> int:
        """Allocate a signal ID for the signal bus."""
        if name in self._signals:
            return self._signals[name].signal_id

        signal_id = self._next_signal_id
        self._next_signal_id += 1
        self._signals[name] = SignalConfig(signal_id, name, kind, initial)
        return signal_id

    def allocate_controller_slot(self) -> int:
        """Allocate next available controller slot."""
        if self._next_controller_slot >= 8:
            raise ValueError("Maximum 8 controller slots available")
        slot = self._next_controller_slot
        self._next_controller_slot += 1
        return slot

    def allocate_observer_slot(self) -> int:
        """Allocate next available observer slot."""
        if self._next_observer_slot >= 4:
            raise ValueError("Maximum 4 observer slots available")
        slot = self._next_observer_slot
        self._next_observer_slot += 1
        return slot

    def map_pid_block(self, block_props: dict) -> ControllerSlotConfig:
        """Map PID block to firmware config."""
        slot = block_props.get("slot", self.allocate_controller_slot())

        config = ControllerSlotConfig(
            slot=slot,
            controller_type="PID",
            rate_hz=100,
            kp=block_props.get("kp", 1.0),
            ki=block_props.get("ki", 0.0),
            kd=block_props.get("kd", 0.0),
            out_min=block_props.get("output_min", -1.0),
            out_max=block_props.get("output_max", 1.0),
        )
        self._controller_configs.append(config)
        return config

    def map_observer_block(self, block_props: dict) -> ObserverSlotConfig:
        """Map Observer block to firmware config."""
        slot = block_props.get("slot", self.allocate_observer_slot())
        n_states = block_props.get("n_states", 2)

        config = ObserverSlotConfig(
            slot=slot,
            num_states=n_states,
            num_inputs=block_props.get("n_inputs", 1),
            num_outputs=block_props.get("n_outputs", 1),
            rate_hz=200,
            A=block_props.get("A", [0.0] * (n_states * n_states)),
            B=block_props.get("B", [0.0] * n_states),
            C=block_props.get("C", [1.0] + [0.0] * (n_states - 1)),
            L=block_props.get("L", [0.5] * n_states),
        )
        self._observer_configs.append(config)
        return config

    def map_integrator_block(self, block_props: dict) -> ControllerSlotConfig:
        """
        Map Integrator block to state-space controller.

        Integrator: x_dot = u, y = K*x
        State-space: A=0, B=1, C=K, D=0

        With limits, this becomes a controller slot.
        """
        slot = self.allocate_controller_slot()
        gain = block_props.get("gain", 1.0)

        config = ControllerSlotConfig(
            slot=slot,
            controller_type="STATE_SPACE",
            rate_hz=100,
            num_states=1,
            num_inputs=1,
            A=[0.0],  # dx/dt = 0*x + B*u (pure integrator)
            B=[1.0],  # Input gain
            C=[gain],  # Output = gain * state
            K=[0.0],  # No state feedback (open loop)
            out_min=block_props.get("limit_min", -1000.0),
            out_max=block_props.get("limit_max", 1000.0),
        )
        self._controller_configs.append(config)
        return config

    def map_derivative_block(self, block_props: dict) -> ControllerSlotConfig:
        """
        Map Derivative block to state-space controller.

        Filtered derivative: H(s) = K*s / (1 + s/N)

        This is equivalent to:
        x_dot = -N*x + N*u
        y = K*(-N*x + N*u) = K*N*(u - x)

        Simplified as 1st order HP filter.
        """
        slot = self.allocate_controller_slot()
        gain = block_props.get("gain", 1.0)
        N = block_props.get("filter_coeff", 100.0)

        config = ControllerSlotConfig(
            slot=slot,
            controller_type="STATE_SPACE",
            rate_hz=100,
            num_states=1,
            num_inputs=1,
            A=[-N],      # x_dot = -N*x + N*u
            B=[N],
            C=[gain],    # y = K*x (state tracks filtered derivative)
            K=[0.0],
        )
        self._controller_configs.append(config)
        self._warnings.append(
            f"Derivative block mapped to 1st-order HP filter with N={N}"
        )
        return config

    def map_filter_block(self, block_props: dict) -> ControllerSlotConfig:
        """
        Map Filter block to state-space controller.

        1st order low-pass: H(s) = wc / (s + wc)

        State-space: x_dot = -wc*x + wc*u, y = x
        """
        slot = self.allocate_controller_slot()
        cutoff = block_props.get("cutoff_freq", 10.0)
        wc = 2 * math.pi * cutoff  # Convert Hz to rad/s

        config = ControllerSlotConfig(
            slot=slot,
            controller_type="STATE_SPACE",
            rate_hz=100,
            num_states=1,
            num_inputs=1,
            A=[-wc],
            B=[wc],
            C=[1.0],
            K=[0.0],
        )
        self._controller_configs.append(config)
        return config

    def map_saturation_block(self, block_props: dict) -> Optional[ControllerSlotConfig]:
        """
        Saturation blocks don't map to dedicated slots.

        Instead, saturation is implemented via:
        1. Controller output limits (out_min, out_max)
        2. Signal bus rate limiting

        Returns None and adds a warning.
        """
        lower = block_props.get("lower", -1.0)
        upper = block_props.get("upper", 1.0)

        self._warnings.append(
            f"Saturation block [{lower}, {upper}] should be applied via "
            f"controller output limits or post-processing."
        )
        return None

    def map_delay_block(self, block_props: dict) -> Optional[ControllerSlotConfig]:
        """
        Delay blocks cannot be directly mapped to firmware.

        Time delays require buffer memory which isn't available
        in the current controller architecture.

        Returns None and adds a warning.
        """
        delay = block_props.get("delay_time", 0.1)

        self._warnings.append(
            f"Delay block (T={delay}s) not directly supported in firmware. "
            f"Consider using signal timing or external delay buffer."
        )
        return None

    def map_gain_block(self, block_props: dict) -> Optional[ControllerSlotConfig]:
        """
        Gain blocks are typically absorbed into other blocks.

        They can be implemented as:
        1. Part of signal routing (multiply on read)
        2. State-space with C=K (pass-through with gain)
        """
        gain = block_props.get("gain", 1.0)

        if gain == 1.0:
            return None  # Unity gain needs no slot

        # Map to trivial state-space
        slot = self.allocate_controller_slot()
        config = ControllerSlotConfig(
            slot=slot,
            controller_type="STATE_SPACE",
            rate_hz=100,
            num_states=1,
            num_inputs=1,
            A=[0.0],
            B=[0.0],
            C=[gain],
            K=[0.0],
        )
        self._controller_configs.append(config)
        self._warnings.append(
            f"Gain block (K={gain}) uses a controller slot. "
            f"Consider merging with adjacent blocks."
        )
        return config

    def map_sum_block(self, block_props: dict) -> None:
        """
        Sum blocks are handled by signal routing, not slots.

        The signal bus can sum multiple signals when reading.
        """
        self._warnings.append(
            "Sum block handled via signal routing, no slot needed."
        )

    def map_from_registry(self, block_type: str, block_props: dict) -> Optional[ControllerSlotConfig]:
        """
        Map a block using the control registry.

        This is the extensible mapping path - new blocks added to the registry
        are automatically supported without code changes here.

        Args:
            block_type: Block type key from registry
            block_props: Block properties from GUI

        Returns:
            ControllerSlotConfig or ObserverSlotConfig if mapped, None otherwise
        """
        if not HAS_CONTROL_REGISTRY:
            return None

        block_config = get_block_config(block_type)
        if not block_config:
            return None

        category = block_config.get("category", "")
        firmware = block_config.get("firmware", {})
        slot_type = firmware.get("slot_type")
        maps_to = firmware.get("maps_to")
        warning = firmware.get("warning")

        # Add any firmware warnings
        if warning:
            self._warnings.append(f"{block_type}: {warning}")

        # Signal blocks don't use slots
        if slot_type == "SIGNAL_BUS" or slot_type is None:
            if maps_to is None:
                self._warnings.append(
                    f"{block_type}: No direct firmware mapping"
                )
            return None

        # Try to derive state-space matrices from registry
        ss_matrices = derive_state_space(block_config, block_props)

        if slot_type == "CONTROLLER":
            slot = block_props.get("slot", self.allocate_controller_slot())

            if maps_to == "PID":
                # Direct PID mapping
                config = ControllerSlotConfig(
                    slot=slot,
                    controller_type="PID",
                    rate_hz=block_props.get("rate_hz", 100),
                    kp=block_props.get("kp", 1.0),
                    ki=block_props.get("ki", 0.0),
                    kd=block_props.get("kd", 0.0),
                    out_min=block_props.get("output_min", -1.0),
                    out_max=block_props.get("output_max", 1.0),
                )
            else:
                # State-space mapping (derived or direct)
                n = block_props.get("num_states", 1)
                config = ControllerSlotConfig(
                    slot=slot,
                    controller_type="STATE_SPACE",
                    rate_hz=block_props.get("rate_hz", 100),
                    num_states=n,
                    num_inputs=block_props.get("num_inputs", 1),
                    A=ss_matrices.get("A", [0.0] * (n * n)) if ss_matrices else block_props.get("A", []),
                    B=ss_matrices.get("B", [0.0] * n) if ss_matrices else block_props.get("B", []),
                    C=ss_matrices.get("C", [1.0] + [0.0] * (n - 1)) if ss_matrices else block_props.get("C", []),
                    K=ss_matrices.get("K", [0.0] * n) if ss_matrices else block_props.get("K", []),
                    out_min=block_props.get("output_min", -1.0),
                    out_max=block_props.get("output_max", 1.0),
                )

            self._controller_configs.append(config)
            return config

        elif slot_type == "OBSERVER":
            slot = block_props.get("slot", self.allocate_observer_slot())
            n = block_props.get("num_states", 2)

            config = ObserverSlotConfig(
                slot=slot,
                num_states=n,
                num_inputs=block_props.get("num_inputs", 1),
                num_outputs=block_props.get("num_outputs", 1),
                rate_hz=block_props.get("rate_hz", 200),
                A=ss_matrices.get("A", [0.0] * (n * n)) if ss_matrices else block_props.get("A", []),
                B=ss_matrices.get("B", [0.0] * n) if ss_matrices else block_props.get("B", []),
                C=ss_matrices.get("C", [1.0] + [0.0] * (n - 1)) if ss_matrices else block_props.get("C", []),
                L=ss_matrices.get("L", [0.5] * n) if ss_matrices else block_props.get("L", []),
            )
            self._observer_configs.append(config)
            return config

        elif slot_type == "CONTROLLER+OBSERVER":
            # Combined blocks use both slots (e.g., Kalman+LQG)
            controller_slot = block_props.get("controller_slot", self.allocate_controller_slot())
            observer_slot = block_props.get("observer_slot", self.allocate_observer_slot())
            n = block_props.get("num_states", 2)

            # Controller part
            ctrl_config = ControllerSlotConfig(
                slot=controller_slot,
                controller_type="STATE_SPACE",
                rate_hz=block_props.get("rate_hz", 100),
                num_states=n,
                num_inputs=block_props.get("num_inputs", 1),
                A=block_props.get("A", []),
                B=block_props.get("B", []),
                C=block_props.get("C", []),
                K=block_props.get("K", []),
            )
            self._controller_configs.append(ctrl_config)

            # Observer part
            obs_config = ObserverSlotConfig(
                slot=observer_slot,
                num_states=n,
                num_inputs=block_props.get("num_inputs", 1),
                num_outputs=block_props.get("num_outputs", 1),
                rate_hz=block_props.get("rate_hz", 200),
                A=block_props.get("A", []),
                B=block_props.get("B", []),
                C=block_props.get("C", []),
                L=block_props.get("L", []),
            )
            self._observer_configs.append(obs_config)

            return ctrl_config

        return None

    def get_signals(self) -> list[SignalConfig]:
        """Get all allocated signals."""
        return list(self._signals.values())

    def get_controller_configs(self) -> list[ControllerSlotConfig]:
        """Get all controller slot configurations."""
        return self._controller_configs

    def get_observer_configs(self) -> list[ObserverSlotConfig]:
        """Get all observer slot configurations."""
        return self._observer_configs

    def get_warnings(self) -> list[str]:
        """Get mapping warnings."""
        return self._warnings

    def get_slot_usage(self) -> dict:
        """Get slot usage summary."""
        return {
            "controller_slots_used": self._next_controller_slot,
            "controller_slots_free": 8 - self._next_controller_slot,
            "observer_slots_used": self._next_observer_slot,
            "observer_slots_free": 4 - self._next_observer_slot,
            "signals_defined": len(self._signals),
        }


def map_diagram_to_firmware(diagram_state: dict) -> tuple[list[dict], list[dict], list[str]]:
    """
    Map a complete diagram to firmware configurations.

    Args:
        diagram_state: Diagram state from DiagramCanvas.get_state()

    Returns:
        Tuple of (controller_configs, observer_configs, warnings)
    """
    mapper = BlockMapper()

    for block in diagram_state.get("blocks", []):
        block_type = block.get("block_type", "")
        props = block.get("properties", {})

        # Try registry-based mapping first
        if HAS_CONTROL_REGISTRY and block_type in CONTROL_BLOCKS:
            mapper.map_from_registry(block_type, props)
        # Fallback to hardcoded mapping for backwards compatibility
        elif block_type == "pid":
            mapper.map_pid_block(props)
        elif block_type == "observer":
            mapper.map_observer_block(props)
        elif block_type == "integrator":
            mapper.map_integrator_block(props)
        elif block_type == "derivative":
            mapper.map_derivative_block(props)
        elif block_type == "filter":
            mapper.map_filter_block(props)
        elif block_type == "saturation":
            mapper.map_saturation_block(props)
        elif block_type == "delay":
            mapper.map_delay_block(props)
        elif block_type == "gain":
            mapper.map_gain_block(props)
        elif block_type == "sum":
            mapper.map_sum_block(props)
        # Service blocks (motor_service, etc.) don't need mapping

    # Convert to dicts for JSON serialization
    controller_configs = [
        {
            "slot": c.slot,
            "controller_type": c.controller_type,
            "rate_hz": c.rate_hz,
            "kp": c.kp, "ki": c.ki, "kd": c.kd,
            "out_min": c.out_min, "out_max": c.out_max,
            "num_states": c.num_states, "num_inputs": c.num_inputs,
            "A": c.A, "B": c.B, "C": c.C, "K": c.K,
        }
        for c in mapper.get_controller_configs()
    ]

    observer_configs = [
        {
            "slot": o.slot,
            "num_states": o.num_states,
            "num_inputs": o.num_inputs,
            "num_outputs": o.num_outputs,
            "rate_hz": o.rate_hz,
            "A": o.A, "B": o.B, "C": o.C, "L": o.L,
        }
        for o in mapper.get_observer_configs()
    ]

    return controller_configs, observer_configs, mapper.get_warnings()

# mara_host/services/control/controller_service.py
"""
Controller system service.

Provides high-level control for signal bus and controller/observer slots.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class SignalKind(str, Enum):
    """Signal types in the signal bus."""

    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    EVENT = "event"


class ControllerType(str, Enum):
    """Controller types."""

    PID = "PID"
    STATE_SPACE = "STATE_SPACE"


class ObserverType(str, Enum):
    """Observer types."""

    KALMAN = "KALMAN"
    LUENBERGER = "LUENBERGER"
    EKF = "EKF"


@dataclass
class Signal:
    """Signal definition."""

    signal_id: int
    name: str
    kind: SignalKind = SignalKind.CONTINUOUS
    value: float = 0.0


@dataclass
class ControllerSlot:
    """Controller slot configuration."""

    slot: int
    controller_type: ControllerType = ControllerType.PID
    ref_id: Optional[int] = None  # Reference signal ID
    meas_id: Optional[int] = None  # Measurement signal ID
    out_id: Optional[int] = None  # Output signal ID
    rate_hz: int = 100
    enabled: bool = False
    params: dict = field(default_factory=dict)


@dataclass
class ObserverSlot:
    """Observer slot configuration."""

    slot: int
    observer_type: ObserverType = ObserverType.KALMAN
    rate_hz: int = 100
    enabled: bool = False


class ControllerService:
    """
    Service for control system management.

    Manages the signal bus and controller/observer slots on the MCU.
    This is a plain class (not ConfigurableService) as it manages
    multiple related entities.

    Example:
        ctrl_svc = ControllerService(client)

        # Define signals
        await ctrl_svc.signal_define(0, "velocity_ref", kind="continuous")
        await ctrl_svc.signal_define(1, "velocity_meas", kind="continuous")
        await ctrl_svc.signal_define(2, "motor_cmd", kind="continuous")

        # Configure controller
        await ctrl_svc.controller_config(
            slot=0,
            controller_type="PID",
            ref_id=0,
            meas_id=1,
            out_id=2,
        )

        # Set PID gains
        await ctrl_svc.controller_set_param(0, "kp", 1.0)
        await ctrl_svc.controller_set_param(0, "ki", 0.1)
        await ctrl_svc.controller_set_param(0, "kd", 0.01)

        # Enable controller
        await ctrl_svc.controller_enable(0)
    """

    def __init__(self, client: "MaraClient"):
        """
        Initialize controller service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._signals: dict[int, Signal] = {}
        self._controllers: dict[int, ControllerSlot] = {}
        self._observers: dict[int, ObserverSlot] = {}

    # ==================== Signal Operations ====================

    async def signal_define(
        self,
        signal_id: int,
        name: str,
        kind: str = "continuous",
        initial_value: float = 0.0,
    ) -> ServiceResult:
        """
        Define a new signal in the signal bus.

        Args:
            signal_id: Signal ID (0-255)
            name: Signal name
            kind: Signal kind (continuous, discrete, event)
            initial_value: Initial value

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SIGNAL_DEFINE",
            {
                "signal_id": signal_id,
                "name": name,
                "signal_kind": kind,
                "initial_value": initial_value,
            },
        )

        if ok:
            self._signals[signal_id] = Signal(
                signal_id=signal_id,
                name=name,
                kind=SignalKind(kind),
                value=initial_value,
            )
            return ServiceResult.success(
                data={"signal_id": signal_id, "name": name}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to define signal {signal_id}"
            )

    async def signal_set(self, signal_id: int, value: float) -> ServiceResult:
        """
        Set a signal value.

        Args:
            signal_id: Signal ID
            value: Value to set

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SIGNAL_SET",
            {
                "signal_id": signal_id,
                "value": value,
            },
        )

        if ok:
            if signal_id in self._signals:
                self._signals[signal_id].value = value
            return ServiceResult.success(
                data={"signal_id": signal_id, "value": value}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set signal {signal_id}"
            )

    async def signals_list(self) -> ServiceResult:
        """
        Request list of all signals.

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SIGNALS_LIST",
            {},
        )

        if ok:
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to list signals")

    async def signals_clear(self) -> ServiceResult:
        """
        Clear all signals.

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SIGNALS_CLEAR",
            {},
        )

        if ok:
            self._signals.clear()
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to clear signals")

    # ==================== Controller Operations ====================

    async def controller_config(
        self,
        slot: int,
        controller_type: str = "PID",
        ref_id: Optional[int] = None,
        meas_id: Optional[int] = None,
        out_id: Optional[int] = None,
        rate_hz: int = 100,
        # STATE_SPACE specific parameters
        num_states: Optional[int] = None,
        num_inputs: Optional[int] = None,
        state_ids: Optional[list[int]] = None,
        ref_ids: Optional[list[int]] = None,
        output_ids: Optional[list[int]] = None,
        require_armed: bool = True,
        require_active: bool = True,
    ) -> ServiceResult:
        """
        Configure a controller slot.

        Args:
            slot: Slot number (0-7)
            controller_type: Controller type (PID, STATE_SPACE)
            ref_id: Reference signal ID (PID mode)
            meas_id: Measurement signal ID (PID mode)
            out_id: Output signal ID (PID mode)
            rate_hz: Control rate in Hz
            num_states: Number of state variables (STATE_SPACE mode, 1-6)
            num_inputs: Number of control inputs (STATE_SPACE mode, 1-2)
            state_ids: Signal IDs for state measurements (STATE_SPACE mode)
            ref_ids: Signal IDs for state references (STATE_SPACE mode)
            output_ids: Signal IDs for control outputs (STATE_SPACE mode)
            require_armed: Only run when robot is armed
            require_active: Only run when robot is active

        Returns:
            ServiceResult
        """
        payload = {
            "slot": slot,
            "controller_type": controller_type,
            "rate_hz": rate_hz,
        }

        # PID mode parameters
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if meas_id is not None:
            payload["meas_id"] = meas_id
        if out_id is not None:
            payload["out_id"] = out_id

        # STATE_SPACE mode parameters
        if num_states is not None:
            payload["num_states"] = num_states
        if num_inputs is not None:
            payload["num_inputs"] = num_inputs
        if state_ids is not None:
            payload["state_ids"] = state_ids
        if ref_ids is not None:
            payload["ref_ids"] = ref_ids
        if output_ids is not None:
            payload["output_ids"] = output_ids

        # Safety requirements
        payload["require_armed"] = require_armed
        payload["require_active"] = require_active

        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SLOT_CONFIG",
            payload,
        )

        if ok:
            self._controllers[slot] = ControllerSlot(
                slot=slot,
                controller_type=ControllerType(controller_type),
                ref_id=ref_id,
                meas_id=meas_id,
                out_id=out_id,
                rate_hz=rate_hz,
            )
            return ServiceResult.success(data=payload)
        else:
            return ServiceResult.failure(
                error=error or f"Failed to configure controller slot {slot}"
            )

    async def controller_enable(self, slot: int, enable: bool = True) -> ServiceResult:
        """
        Enable or disable a controller slot.

        Args:
            slot: Slot number (0-7)
            enable: True to enable, False to disable

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SLOT_ENABLE",
            {
                "slot": slot,
                "enable": enable,
            },
        )

        if ok:
            if slot in self._controllers:
                self._controllers[slot].enabled = enable
            return ServiceResult.success(
                data={"slot": slot, "enabled": enable}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to {'enable' if enable else 'disable'} controller slot {slot}"
            )

    async def controller_disable(self, slot: int) -> ServiceResult:
        """
        Disable a controller slot.

        Args:
            slot: Slot number (0-7)

        Returns:
            ServiceResult
        """
        return await self.controller_enable(slot, enable=False)

    async def controller_set_param(
        self,
        slot: int,
        key: str,
        value: float,
    ) -> ServiceResult:
        """
        Set a controller parameter.

        Args:
            slot: Slot number (0-7)
            key: Parameter key (e.g., kp, ki, kd)
            value: Parameter value

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SLOT_SET_PARAM",
            {
                "slot": slot,
                "key": key,
                "value": value,
            },
        )

        if ok:
            if slot in self._controllers:
                self._controllers[slot].params[key] = value
            return ServiceResult.success(
                data={"slot": slot, "key": key, "value": value}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set parameter {key} on slot {slot}"
            )

    async def controller_reset(self, slot: int) -> ServiceResult:
        """
        Reset a controller slot.

        Resets internal state (e.g., integrator, previous error).

        Args:
            slot: Slot number (0-7)

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SLOT_RESET",
            {"slot": slot},
        )

        if ok:
            return ServiceResult.success(data={"slot": slot})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to reset controller slot {slot}"
            )

    async def controller_set_param_array(
        self,
        slot: int,
        key: str,
        values: list,
    ) -> ServiceResult:
        """
        Set controller matrix parameters (for state-space controllers).

        Args:
            slot: Slot number (0-7)
            key: Parameter key (e.g., A, B, C, K matrices)
            values: Matrix values as flat list

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SLOT_SET_PARAM_ARRAY",
            {
                "slot": slot,
                "key": key,
                "values": values,
            },
        )

        if ok:
            return ServiceResult.success(
                data={"slot": slot, "key": key, "values": values}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set parameter array {key} on slot {slot}"
            )

    # ==================== Observer Operations ====================

    async def observer_config(
        self,
        slot: int,
        num_states: int,
        num_outputs: int,
        num_inputs: int = 1,
        rate_hz: int = 200,
        input_ids: Optional[list[int]] = None,
        output_ids: Optional[list[int]] = None,
        estimate_ids: Optional[list[int]] = None,
    ) -> ServiceResult:
        """
        Configure a Luenberger state observer.

        Args:
            slot: Observer slot number (0-3)
            num_states: Number of states to estimate (1-6)
            num_outputs: Number of measurements (1-4)
            num_inputs: Number of control inputs (1-2)
            rate_hz: Observer update rate in Hz (50-1000)
            input_ids: Signal IDs for control inputs (u)
            output_ids: Signal IDs for measurements (y)
            estimate_ids: Signal IDs where state estimates (x̂) are written

        Returns:
            ServiceResult
        """
        payload = {
            "slot": slot,
            "num_states": num_states,
            "num_inputs": num_inputs,
            "num_outputs": num_outputs,
            "rate_hz": rate_hz,
        }

        if input_ids is not None:
            payload["input_ids"] = input_ids
        if output_ids is not None:
            payload["output_ids"] = output_ids
        if estimate_ids is not None:
            payload["estimate_ids"] = estimate_ids

        ok, error = await self.client.send_reliable(
            "CMD_OBSERVER_CONFIG",
            payload,
        )

        if ok:
            self._observers[slot] = ObserverSlot(
                slot=slot,
                rate_hz=rate_hz,
            )
            return ServiceResult.success(data=payload)
        else:
            return ServiceResult.failure(
                error=error or f"Failed to configure observer slot {slot}"
            )

    async def observer_enable(self, slot: int, enable: bool = True) -> ServiceResult:
        """
        Enable or disable an observer slot.

        Args:
            slot: Slot number (0-7)
            enable: True to enable, False to disable

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_OBSERVER_ENABLE",
            {
                "slot": slot,
                "enable": enable,
            },
        )

        if ok:
            if slot in self._observers:
                self._observers[slot].enabled = enable
            return ServiceResult.success(
                data={"slot": slot, "enabled": enable}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to {'enable' if enable else 'disable'} observer slot {slot}"
            )

    async def observer_disable(self, slot: int) -> ServiceResult:
        """
        Disable an observer slot.

        Args:
            slot: Slot number (0-7)

        Returns:
            ServiceResult
        """
        return await self.observer_enable(slot, enable=False)

    async def observer_reset(self, slot: int) -> ServiceResult:
        """
        Reset an observer slot.

        Args:
            slot: Slot number (0-7)

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_OBSERVER_RESET",
            {"slot": slot},
        )

        if ok:
            return ServiceResult.success(data={"slot": slot})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to reset observer slot {slot}"
            )

    async def observer_set_param(
        self,
        slot: int,
        key: str,
        value: float,
    ) -> ServiceResult:
        """
        Set an observer parameter.

        Args:
            slot: Slot number (0-7)
            key: Parameter key
            value: Parameter value

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_OBSERVER_SET_PARAM",
            {
                "slot": slot,
                "key": key,
                "value": value,
            },
        )

        if ok:
            return ServiceResult.success(
                data={"slot": slot, "key": key, "value": value}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set observer parameter {key} on slot {slot}"
            )

    async def observer_set_param_array(
        self,
        slot: int,
        key: str,
        values: list,
    ) -> ServiceResult:
        """
        Set observer matrix parameters (A, B, C, L matrices).

        Args:
            slot: Slot number (0-7)
            key: Parameter key (e.g., A, B, C, L)
            values: Matrix values as flat list

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_OBSERVER_SET_PARAM_ARRAY",
            {
                "slot": slot,
                "key": key,
                "values": values,
            },
        )

        if ok:
            return ServiceResult.success(
                data={"slot": slot, "key": key, "values": values}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set observer parameter array {key} on slot {slot}"
            )

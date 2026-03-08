# mara_host/api/controller_slot.py
"""
Controller Slot API.

Provides access to the MCU's controller slots for configuring
PID and state-space controllers.

Example:
    async with Robot("/dev/ttyUSB0") as robot:
        # Configure a PID controller in slot 0
        ctrl = robot.controllers[0]
        await ctrl.configure(
            controller_type="PID",
            rate_hz=100,
            ref_signal_id=0,
            meas_signal_id=1,
            out_signal_id=2,
        )

        # Set PID gains
        await ctrl.set_gains(kp=1.0, ki=0.1, kd=0.01)

        # Enable the controller
        await ctrl.enable()

        # Disable when done
        await ctrl.disable()
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from enum import Enum

if TYPE_CHECKING:
    from mara_host.robot import Robot


class ControllerType(Enum):
    """Controller types."""
    PID = "PID"
    STATE_SPACE = "STATE_SPACE"


@dataclass
class ControllerConfig:
    """Controller slot configuration."""
    slot: int
    controller_type: ControllerType = ControllerType.PID
    rate_hz: int = 100
    ref_signal_id: int = 0
    meas_signal_id: int = 1
    out_signal_id: int = 2
    enabled: bool = False
    # PID gains
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    out_limit: float = 1.0


class ControllerSlot:
    """
    Interface to a single controller slot.

    Each slot can run one controller (PID or state-space) that reads
    from input signals and writes to output signals.

    Usage:
        ctrl = robot.controllers[0]
        await ctrl.configure(controller_type="PID", rate_hz=100)
        await ctrl.set_gains(kp=1.0, ki=0.1, kd=0.01)
        await ctrl.enable()
    """

    def __init__(self, robot: "Robot", slot: int) -> None:
        self._robot = robot
        self._slot = slot
        self._config = ControllerConfig(slot=slot)

    @property
    def slot(self) -> int:
        """Slot number."""
        return self._slot

    @property
    def config(self) -> ControllerConfig:
        """Current configuration."""
        return self._config

    @property
    def is_enabled(self) -> bool:
        """Whether the controller is enabled."""
        return self._config.enabled

    async def configure(
        self,
        controller_type: str = "PID",
        rate_hz: int = 100,
        ref_signal_id: int = 0,
        meas_signal_id: int = 1,
        out_signal_id: int = 2,
    ) -> None:
        """
        Configure the controller slot.

        Args:
            controller_type: "PID" or "STATE_SPACE"
            rate_hz: Control loop rate in Hz
            ref_signal_id: Reference input signal ID
            meas_signal_id: Measurement input signal ID
            out_signal_id: Output signal ID
        """
        await self._robot.client.send_reliable(
            "CMD_CTRL_SLOT_CONFIG",
            {
                "slot": self._slot,
                "controller_type": controller_type,
                "rate_hz": rate_hz,
                "ref_id": ref_signal_id,
                "meas_id": meas_signal_id,
                "out_id": out_signal_id,
            }
        )

        self._config.controller_type = ControllerType(controller_type)
        self._config.rate_hz = rate_hz
        self._config.ref_signal_id = ref_signal_id
        self._config.meas_signal_id = meas_signal_id
        self._config.out_signal_id = out_signal_id

    async def set_gains(
        self,
        kp: Optional[float] = None,
        ki: Optional[float] = None,
        kd: Optional[float] = None,
        out_limit: Optional[float] = None,
    ) -> None:
        """
        Set PID gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            out_limit: Output limit (symmetric)
        """
        if kp is not None:
            await self._set_param("kp", kp)
            self._config.kp = kp

        if ki is not None:
            await self._set_param("ki", ki)
            self._config.ki = ki

        if kd is not None:
            await self._set_param("kd", kd)
            self._config.kd = kd

        if out_limit is not None:
            await self._set_param("out_limit", out_limit)
            self._config.out_limit = out_limit

    async def _set_param(self, key: str, value: float) -> None:
        """Set a single parameter."""
        await self._robot.client.send_reliable(
            "CMD_CTRL_SLOT_SET_PARAM",
            {"slot": self._slot, "key": key, "value": value}
        )

    async def enable(self) -> None:
        """Enable the controller."""
        await self._robot.client.send_reliable(
            "CMD_CTRL_SLOT_ENABLE",
            {"slot": self._slot, "enable": True}
        )
        self._config.enabled = True

    async def disable(self) -> None:
        """Disable the controller."""
        await self._robot.client.send_reliable(
            "CMD_CTRL_SLOT_ENABLE",
            {"slot": self._slot, "enable": False}
        )
        self._config.enabled = False

    async def reset(self) -> None:
        """Reset the controller state (integrator, etc.)."""
        await self._robot.client.send_reliable(
            "CMD_CTRL_SLOT_RESET",
            {"slot": self._slot}
        )


class ControllerSlotManager:
    """
    Manager for all controller slots.

    Access individual slots via indexing:
        ctrl = robot.controllers[0]
        await ctrl.configure(...)

    Or iterate:
        for ctrl in robot.controllers:
            await ctrl.disable()
    """

    NUM_SLOTS = 8

    def __init__(self, robot: "Robot") -> None:
        self._robot = robot
        self._slots = [ControllerSlot(robot, i) for i in range(self.NUM_SLOTS)]

    def __getitem__(self, index: int) -> ControllerSlot:
        if not 0 <= index < self.NUM_SLOTS:
            raise IndexError(f"Controller slot {index} out of range (0-{self.NUM_SLOTS-1})")
        return self._slots[index]

    def __iter__(self):
        return iter(self._slots)

    def __len__(self) -> int:
        return self.NUM_SLOTS

    async def disable_all(self) -> None:
        """Disable all controller slots."""
        for slot in self._slots:
            await slot.disable()

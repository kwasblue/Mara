# mara_host/api/observer_slot.py
"""
Observer Slot API.

Provides access to the MCU's observer slots for configuring
state observers (Kalman, Luenberger, EKF).

Example:
    async with Robot("/dev/ttyUSB0") as robot:
        # Configure a Luenberger observer in slot 0
        obs = robot.observers[0]
        await obs.configure(
            observer_type="LUENBERGER",
            rate_hz=200,
            n_states=2,
            n_inputs=1,
            n_outputs=1,
        )

        # Set matrices
        await obs.set_matrix("A", [[1, 0.01], [0, 1]])
        await obs.set_matrix("L", [[0.1], [0.2]])

        # Enable
        await obs.enable()
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, List
from enum import Enum

if TYPE_CHECKING:
    from mara_host.robot import Robot


class ObserverType(Enum):
    """Observer types."""
    KALMAN = "KALMAN"
    LUENBERGER = "LUENBERGER"
    EKF = "EKF"


@dataclass
class ObserverConfig:
    """Observer slot configuration."""
    slot: int
    observer_type: ObserverType = ObserverType.LUENBERGER
    rate_hz: int = 200
    n_states: int = 2
    n_inputs: int = 1
    n_outputs: int = 1
    enabled: bool = False


class ObserverSlot:
    """
    Interface to a single observer slot.

    Each slot can run one state observer that estimates system state
    from measurements.

    Usage:
        obs = robot.observers[0]
        await obs.configure(observer_type="LUENBERGER", n_states=2)
        await obs.set_matrix("L", [[0.1], [0.2]])
        await obs.enable()
    """

    def __init__(self, robot: "Robot", slot: int) -> None:
        self._robot = robot
        self._slot = slot
        self._config = ObserverConfig(slot=slot)

    @property
    def slot(self) -> int:
        """Slot number."""
        return self._slot

    @property
    def config(self) -> ObserverConfig:
        """Current configuration."""
        return self._config

    @property
    def is_enabled(self) -> bool:
        """Whether the observer is enabled."""
        return self._config.enabled

    async def configure(
        self,
        observer_type: str = "LUENBERGER",
        rate_hz: int = 200,
        n_states: int = 2,
        n_inputs: int = 1,
        n_outputs: int = 1,
    ) -> None:
        """
        Configure the observer slot.

        Args:
            observer_type: "KALMAN", "LUENBERGER", or "EKF"
            rate_hz: Update rate in Hz
            n_states: Number of state variables
            n_inputs: Number of inputs
            n_outputs: Number of outputs

        Raises:
            RuntimeError: If configuration fails
        """
        ok, error = await self._robot.client.send_reliable(
            "CMD_OBSERVER_CONFIG",
            {
                "slot": self._slot,
                "observer_type": observer_type,
                "rate_hz": rate_hz,
                "n_states": n_states,
                "n_inputs": n_inputs,
                "n_outputs": n_outputs,
            }
        )
        if not ok:
            raise RuntimeError(error or "Observer configure failed")

        self._config.observer_type = ObserverType(observer_type)
        self._config.rate_hz = rate_hz
        self._config.n_states = n_states
        self._config.n_inputs = n_inputs
        self._config.n_outputs = n_outputs

    async def set_matrix(self, name: str, values: List[List[float]]) -> None:
        """
        Set an observer matrix.

        Args:
            name: Matrix name ("A", "B", "C", "L", "K", "Q", "R")
            values: 2D list of matrix values (row-major)

        Raises:
            RuntimeError: If setting matrix fails
        """
        # Flatten matrix to 1D array
        flat = []
        for row in values:
            flat.extend(row)

        ok, error = await self._robot.client.send_reliable(
            "CMD_OBSERVER_SET_PARAM_ARRAY",
            {"slot": self._slot, "key": name, "values": flat}
        )
        if not ok:
            raise RuntimeError(error or f"Observer set_matrix({name}) failed")

    async def set_param(self, key: str, value: float) -> None:
        """
        Set a scalar parameter.

        Args:
            key: Parameter name
            value: Parameter value

        Raises:
            RuntimeError: If setting parameter fails
        """
        ok, error = await self._robot.client.send_reliable(
            "CMD_OBSERVER_SET_PARAM",
            {"slot": self._slot, "key": key, "value": value}
        )
        if not ok:
            raise RuntimeError(error or f"Observer set_param({key}) failed")

    async def enable(self) -> None:
        """
        Enable the observer.

        Raises:
            RuntimeError: If enable fails
        """
        ok, error = await self._robot.client.send_reliable(
            "CMD_OBSERVER_ENABLE",
            {"slot": self._slot, "enable": True}
        )
        if not ok:
            raise RuntimeError(error or "Observer enable failed")
        self._config.enabled = True

    async def disable(self) -> None:
        """
        Disable the observer.

        Raises:
            RuntimeError: If disable fails
        """
        ok, error = await self._robot.client.send_reliable(
            "CMD_OBSERVER_ENABLE",
            {"slot": self._slot, "enable": False}
        )
        if not ok:
            raise RuntimeError(error or "Observer disable failed")
        self._config.enabled = False

    async def reset(self) -> None:
        """
        Reset the observer state.

        Raises:
            RuntimeError: If reset fails
        """
        ok, error = await self._robot.client.send_reliable(
            "CMD_OBSERVER_RESET",
            {"slot": self._slot}
        )
        if not ok:
            raise RuntimeError(error or "Observer reset failed")


class ObserverSlotManager:
    """
    Manager for all observer slots.

    Access individual slots via indexing:
        obs = robot.observers[0]
        await obs.configure(...)
    """

    NUM_SLOTS = 4

    def __init__(self, robot: "Robot") -> None:
        self._robot = robot
        self._slots = [ObserverSlot(robot, i) for i in range(self.NUM_SLOTS)]

    def __getitem__(self, index: int) -> ObserverSlot:
        if not 0 <= index < self.NUM_SLOTS:
            raise IndexError(f"Observer slot {index} out of range (0-{self.NUM_SLOTS-1})")
        return self._slots[index]

    def __iter__(self):
        return iter(self._slots)

    def __len__(self) -> int:
        return self.NUM_SLOTS

    async def disable_all(self) -> None:
        """Disable all observer slots."""
        for slot in self._slots:
            await slot.disable()

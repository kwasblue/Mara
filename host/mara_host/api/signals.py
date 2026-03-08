# mara_host/api/signals.py
"""
Signal Bus API.

Provides access to the MCU's signal bus for control systems.
Signals are named floating-point values that can be read/written
and used by controllers/observers.

Example:
    async with Robot("/dev/ttyUSB0") as robot:
        # Define signals
        await robot.signals.define(0, "velocity_ref", initial=0.0)
        await robot.signals.define(1, "velocity_meas", initial=0.0)
        await robot.signals.define(2, "motor_output", initial=0.0)

        # Set/get values
        await robot.signals.set(0, 1.5)  # Set reference to 1.5
        value = await robot.signals.get(1)  # Read measurement

        # List all signals
        signals = await robot.signals.list()

        # Clear all signals
        await robot.signals.clear()
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from enum import Enum

if TYPE_CHECKING:
    from mara_host.robot import Robot


class SignalKind(Enum):
    """Signal types."""
    CONTINUOUS = "continuous"  # Real-valued, sampled at control rate
    DISCRETE = "discrete"      # Integer states
    EVENT = "event"            # Trigger pulses


@dataclass
class Signal:
    """A signal in the signal bus."""
    id: int
    name: str
    kind: SignalKind = SignalKind.CONTINUOUS
    value: float = 0.0


class SignalBus:
    """
    Interface to the MCU's signal bus.

    The signal bus is a shared memory space where controllers and observers
    can read/write signals. Each signal has:
    - ID (0-255): Unique identifier
    - Name: Human-readable name
    - Kind: continuous, discrete, or event
    - Value: Current floating-point value

    Usage:
        signals = robot.signals
        await signals.define(0, "error", initial=0.0)
        await signals.set(0, 1.5)
        value = await signals.get(0)
    """

    def __init__(self, robot: "Robot") -> None:
        self._robot = robot
        self._signals: dict[int, Signal] = {}

    async def define(
        self,
        signal_id: int,
        name: str,
        kind: SignalKind = SignalKind.CONTINUOUS,
        initial: float = 0.0,
    ) -> Signal:
        """
        Define a new signal.

        Args:
            signal_id: Unique ID (0-255)
            name: Human-readable name
            kind: Signal type (continuous, discrete, event)
            initial: Initial value

        Returns:
            The created Signal object
        """
        if not 0 <= signal_id <= 255:
            raise ValueError(f"Signal ID must be 0-255, got {signal_id}")

        await self._robot.client.send_reliable(
            "CMD_CTRL_SIGNAL_DEFINE",
            {
                "signal_id": signal_id,
                "name": name,
                "signal_kind": kind.value,
                "initial_value": initial,
            }
        )

        signal = Signal(id=signal_id, name=name, kind=kind, value=initial)
        self._signals[signal_id] = signal
        return signal

    async def set(self, signal_id: int, value: float) -> None:
        """
        Set a signal value.

        Args:
            signal_id: Signal ID
            value: Value to set
        """
        await self._robot.client.send_reliable(
            "CMD_CTRL_SIGNAL_SET",
            {"signal_id": signal_id, "value": value}
        )

        if signal_id in self._signals:
            self._signals[signal_id].value = value

    async def get(self, signal_id: int) -> float:
        """
        Get a signal value.

        Args:
            signal_id: Signal ID

        Returns:
            Current signal value
        """
        # Request value - response comes via telemetry
        await self._robot.client.send_reliable(
            "CMD_CTRL_SIGNAL_GET",
            {"signal_id": signal_id}
        )

        # Return cached value for now
        if signal_id in self._signals:
            return self._signals[signal_id].value
        return 0.0

    async def delete(self, signal_id: int) -> None:
        """
        Delete a signal.

        Args:
            signal_id: Signal ID to delete
        """
        await self._robot.client.send_reliable(
            "CMD_CTRL_SIGNAL_DELETE",
            {"signal_id": signal_id}
        )

        if signal_id in self._signals:
            del self._signals[signal_id]

    async def clear(self) -> None:
        """Clear all signals."""
        await self._robot.client.send_reliable(
            "CMD_CTRL_SIGNALS_CLEAR",
            {}
        )
        self._signals.clear()

    async def list(self) -> list[Signal]:
        """
        List all defined signals.

        Returns:
            List of Signal objects
        """
        await self._robot.client.send_reliable(
            "CMD_CTRL_SIGNALS_LIST",
            {}
        )
        return list(self._signals.values())

    def __getitem__(self, signal_id: int) -> Optional[Signal]:
        """Get cached signal by ID."""
        return self._signals.get(signal_id)

    def __contains__(self, signal_id: int) -> bool:
        """Check if signal exists."""
        return signal_id in self._signals

# mara_host/services/control/signal_service.py
"""
Signal bus service for signal management.

Provides high-level operations for defining and manipulating
signals in the MCU signal bus system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.command.payloads import (
    CtrlSignalDefinePayload,
    CtrlSignalDeletePayload,
    CtrlSignalGetPayload,
    CtrlSignalSetPayload,
)
from mara_host.services.types import (
    SignalDefineResponse,
    SignalDeleteResponse,
    SignalGetResponse,
    SignalSetResponse,
    SignalListResponse,
)

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class SignalKind(str, Enum):
    """Signal types in the signal bus."""

    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    EVENT = "event"


@dataclass
class Signal:
    """Signal definition."""

    signal_id: int
    name: str
    kind: SignalKind = SignalKind.CONTINUOUS
    value: float = 0.0


class SignalService:
    """
    Service for signal bus management.

    Manages signals in the MCU signal bus system. Signals are used
    by controllers and observers for data flow between components.

    Example:
        signal_svc = SignalService(client)

        # Define signals
        await signal_svc.define(0, "velocity_ref", kind="continuous")
        await signal_svc.define(1, "velocity_meas", kind="continuous")

        # Set signal value
        await signal_svc.set(0, 1.5)

        # Get signal value (from cached state)
        value = signal_svc.get(0)

        # List all signals
        await signal_svc.list()

        # Clear all signals
        await signal_svc.clear()
    """

    def __init__(self, client: "MaraClient"):
        """
        Initialize signal service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._signals: dict[int, Signal] = {}

    @property
    def signals(self) -> dict[int, Signal]:
        """Get cached signals dict."""
        return self._signals.copy()

    def get_cached(self, signal_id: int) -> Optional[Signal]:
        """
        Get cached signal by ID.

        Args:
            signal_id: Signal ID

        Returns:
            Signal if cached, None otherwise
        """
        return self._signals.get(signal_id)

    async def define(
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
        payload = CtrlSignalDefinePayload(
            id=signal_id,
            name=name,
            signal_kind=kind,
            initial=initial_value,
        )
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            self._signals[signal_id] = Signal(
                signal_id=signal_id,
                name=name,
                kind=SignalKind(kind),
                value=initial_value,
            )
            return ServiceResult.success(
                data=SignalDefineResponse(signal_id=signal_id, name=name)
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to define signal {signal_id}"
            )

    async def delete(self, signal_id: int) -> ServiceResult:
        """
        Delete a signal from the signal bus.

        Args:
            signal_id: Signal ID to delete

        Returns:
            ServiceResult
        """
        payload = CtrlSignalDeletePayload(id=signal_id)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            self._signals.pop(signal_id, None)
            return ServiceResult.success(data=SignalDeleteResponse(signal_id=signal_id))
        else:
            return ServiceResult.failure(
                error=error or f"Failed to delete signal {signal_id}"
            )

    async def set(self, signal_id: int, value: float) -> ServiceResult:
        """
        Set a signal value.

        Args:
            signal_id: Signal ID
            value: Value to set

        Returns:
            ServiceResult
        """
        payload = CtrlSignalSetPayload(id=signal_id, value=value)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            if signal_id in self._signals:
                self._signals[signal_id].value = value
            return ServiceResult.success(
                data=SignalSetResponse(signal_id=signal_id, value=value)
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set signal {signal_id}"
            )

    async def get(self, signal_id: int) -> ServiceResult:
        """
        Get a signal value from the MCU.

        Note: This requests the current value from the MCU.
        For cached values, use get_cached().

        Args:
            signal_id: Signal ID

        Returns:
            ServiceResult with value in data
        """
        payload = CtrlSignalGetPayload(id=signal_id)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            # Note: actual value would come from response payload
            # For now, return cached value
            cached = self._signals.get(signal_id)
            value = cached.value if cached else 0.0
            return ServiceResult.success(
                data=SignalGetResponse(signal_id=signal_id, value=value)
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to get signal {signal_id}"
            )

    async def list(self) -> ServiceResult:
        """
        Request list of all signals from the MCU.

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CTRL_SIGNALS_LIST",
            {},
        )

        if ok:
            return ServiceResult.success(
                data=SignalListResponse(signals=tuple(self._signals.keys()))
            )
        else:
            return ServiceResult.failure(error=error or "Failed to list signals")

    async def clear(self) -> ServiceResult:
        """
        Clear all signals from the signal bus.

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

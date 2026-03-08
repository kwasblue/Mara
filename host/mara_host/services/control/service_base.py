# mara_host/services/control/service_base.py
"""
Base classes for control services.

Provides common functionality for services that manage
configurations and states by ID.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Callable, Generic, Optional, Type, TypeVar, TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient

# Type variables for config and state types
ConfigT = TypeVar("ConfigT")
StateT = TypeVar("StateT")


class ConfigurableService(Generic[ConfigT, StateT], ABC):
    """
    Base class for services that manage configurations and states by ID.

    Provides common patterns:
    - Client storage
    - Config/state dictionary management
    - get_config/get_state with auto-creation
    - Helper methods for command sending with error handling

    Type Parameters:
        ConfigT: Configuration dataclass type
        StateT: State dataclass type

    Example:
        @dataclass
        class MotorConfig:
            motor_id: int
            max_speed: float = 1.0

        @dataclass
        class MotorState:
            motor_id: int
            speed: float = 0.0

        class MotorService(ConfigurableService[MotorConfig, MotorState]):
            config_class = MotorConfig
            state_class = MotorState
            id_field = "motor_id"

            def _create_default_config(self, item_id: int) -> MotorConfig:
                return MotorConfig(motor_id=item_id)

            def _create_default_state(self, item_id: int) -> MotorState:
                return MotorState(motor_id=item_id)
    """

    # Subclasses should set these
    config_class: Type[ConfigT] = None
    state_class: Type[StateT] = None
    id_field: str = "id"  # Name of the ID field in config/state dataclasses

    def __init__(self, client: "MaraClient"):
        """
        Initialize service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._configs: dict[int, ConfigT] = {}
        self._states: dict[int, StateT] = {}

    def _create_default_config(self, item_id: int) -> ConfigT:
        """
        Create default config for an item.

        Override this method to customize default config creation.

        Args:
            item_id: Item identifier

        Returns:
            Default configuration
        """
        if self.config_class is not None:
            return self.config_class(**{self.id_field: item_id})
        raise NotImplementedError("Subclass must implement _create_default_config")

    def _create_default_state(self, item_id: int) -> StateT:
        """
        Create default state for an item.

        Override this method to customize default state creation.

        Args:
            item_id: Item identifier

        Returns:
            Default state
        """
        if self.state_class is not None:
            return self.state_class(**{self.id_field: item_id})
        raise NotImplementedError("Subclass must implement _create_default_state")

    def get_config(self, item_id: int) -> ConfigT:
        """
        Get configuration for an item (creates default if not exists).

        Args:
            item_id: Item identifier

        Returns:
            Configuration for the item
        """
        if item_id not in self._configs:
            self._configs[item_id] = self._create_default_config(item_id)
        return self._configs[item_id]

    def get_state(self, item_id: int) -> StateT:
        """
        Get state for an item (creates default if not exists).

        Args:
            item_id: Item identifier

        Returns:
            State for the item
        """
        if item_id not in self._states:
            self._states[item_id] = self._create_default_state(item_id)
        return self._states[item_id]

    def has_config(self, item_id: int) -> bool:
        """Check if configuration exists for an item."""
        return item_id in self._configs

    def has_state(self, item_id: int) -> bool:
        """Check if state exists for an item."""
        return item_id in self._states

    def get_all_configs(self) -> dict[int, ConfigT]:
        """Get all configurations."""
        return self._configs.copy()

    def get_all_states(self) -> dict[int, StateT]:
        """Get all states."""
        return self._states.copy()

    def clear_configs(self) -> None:
        """Clear all configurations."""
        self._configs.clear()

    def clear_states(self) -> None:
        """Clear all states."""
        self._states.clear()

    async def _send_reliable(
        self,
        command: str,
        payload: dict,
        error_message: Optional[str] = None,
    ) -> ServiceResult:
        """
        Send a reliable command and return ServiceResult.

        Args:
            command: Command name
            payload: Command payload
            error_message: Custom error message (uses default if not provided)

        Returns:
            ServiceResult with success/failure
        """
        ok, error = await self.client.send_reliable(command, payload)
        if ok:
            return ServiceResult.success(data=payload)
        else:
            return ServiceResult.failure(
                error=error or error_message or f"Command {command} failed"
            )

    async def _send_auto(
        self,
        command: str,
        payload: dict,
    ) -> ServiceResult:
        """
        Send a fire-and-forget command and return success.

        Args:
            command: Command name
            payload: Command payload

        Returns:
            ServiceResult (always success since no ACK)
        """
        await self.client.send_auto(command, payload)
        return ServiceResult.success(data=payload)

    async def _send_command(
        self,
        command: str,
        payload: dict,
        request_ack: bool = True,
        error_message: Optional[str] = None,
        on_success: Optional[Callable[[], None]] = None,
    ) -> ServiceResult:
        """
        Send a command with configurable acknowledgment.

        Args:
            command: Command name
            payload: Command payload
            request_ack: If True, wait for ACK (reliable)
            error_message: Custom error message
            on_success: Callback to run on success (e.g., update local state)

        Returns:
            ServiceResult
        """
        if request_ack:
            result = await self._send_reliable(command, payload, error_message)
        else:
            result = await self._send_auto(command, payload)

        if result.ok and on_success:
            on_success()

        return result

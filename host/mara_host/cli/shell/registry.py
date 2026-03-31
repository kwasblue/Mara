# mara_host/cli/commands/run/shell/registry.py
"""Command registration for the interactive shell."""

from typing import Callable, Awaitable, Any, Dict, List, Tuple

# Type for command handlers: async def handler(shell, args: list[str]) -> Optional[str]
CommandHandler = Callable[["InteractiveShell", List[str]], Awaitable[Any]]

# Global registries populated by @command decorator
COMMANDS: Dict[str, Tuple[CommandHandler, str]] = {}
GROUPS: Dict[str, List[str]] = {}


def command(name: str, description: str, group: str = "General"):
    """
    Register a shell command.

    Usage:
        @command("arm", "Arm the robot", group="Safety")
        async def cmd_arm(shell, args: list[str]) -> None:
            ...

    Args:
        name: Command name (what user types)
        description: Help text shown in 'help' command
        group: Category for grouping in help output
    """
    def decorator(fn: CommandHandler) -> CommandHandler:
        COMMANDS[name] = (fn, description)
        GROUPS.setdefault(group, []).append(name)
        return fn
    return decorator


def alias(name: str, target: str):
    """
    Create an alias for an existing command.

    Usage:
        alias("exit", "quit")  # 'exit' does same as 'quit'
    """
    if target in COMMANDS:
        handler, desc = COMMANDS[target]
        COMMANDS[name] = (handler, desc)
        # Don't add aliases to groups (they clutter help)


def get_commands() -> Dict[str, Tuple[CommandHandler, str]]:
    """Get all registered commands."""
    return COMMANDS


def get_groups() -> Dict[str, List[str]]:
    """Get command groups for help display."""
    return GROUPS

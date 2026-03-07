# mara_host/cli/commands/pins/__init__.py
"""
Pin management CLI commands.

This package provides CLI commands for ESP32 GPIO pin management:
- pinout: Visual board diagram
- list: Show all pins with status
- free: Show available pins
- info: Detailed pin information
- assign: Assign pins by name
- remove: Remove pin assignments
- suggest: Get pin recommendations
- validate: Validate assignments
- conflicts: Check for conflicts
- interactive: Interactive mode
- wizard: Guided setup wizards
- clear: Clear all assignments
"""

from mara_host.cli.commands.pins._registry import register

__all__ = ["register"]

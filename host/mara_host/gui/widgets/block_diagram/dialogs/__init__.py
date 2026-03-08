# mara_host/gui/widgets/block_diagram/dialogs/__init__.py
"""Configuration dialogs for block diagram elements."""

from .block_config import BlockConfigDialog
from .pid_config import PIDConfigDialog

__all__ = [
    "BlockConfigDialog",
    "PIDConfigDialog",
]

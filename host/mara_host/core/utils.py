# mara_host/core/utils.py
"""
Core utility functions.

Common utilities shared across the mara_host package.
"""

from typing import TypeVar

T = TypeVar('T', int, float)


def clamp(value: T, min_val: T, max_val: T) -> T:
    """
    Clamp a value to a range.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Value clamped to [min_val, max_val]

    Example:
        >>> clamp(5, 0, 10)
        5
        >>> clamp(-5, 0, 10)
        0
        >>> clamp(15, 0, 10)
        10
    """
    return max(min_val, min(max_val, value))

# mara_host/gui/widgets/block_diagram/dialogs/block_config.py
"""Generic configuration dialog for blocks using dict-based schema."""

from typing import Any, Optional

from PySide6.QtWidgets import QWidget

from .base import BaseBlockConfigDialog, FieldDef


def _schema_to_fields(schema: dict[str, dict]) -> list[FieldDef]:
    """
    Convert dict-based schema to FieldDef list.

    Args:
        schema: Dict mapping field names to config dicts

    Returns:
        List of FieldDef objects
    """
    fields = []
    for name, config in schema.items():
        field_type = config.get("type", "str")
        fields.append(
            FieldDef(
                name=name,
                label=config.get("label", name.replace("_", " ").title()),
                field_type=field_type,
                default=config.get("default"),
                min_val=config.get("min", -1e9),
                max_val=config.get("max", 1e9),
                decimals=config.get("decimals", 4),
                choices=config.get("choices"),
                group=config.get("group"),
                suffix=config.get("suffix"),
                tooltip=config.get("tooltip"),
                live_update=config.get("live_update", False),
            )
        )
    return fields


def _infer_schema(properties: dict) -> dict[str, dict]:
    """
    Infer schema from property types.

    Args:
        properties: Dict of property values

    Returns:
        Dict-based schema
    """
    schema = {}
    for key, value in properties.items():
        if key.startswith("_"):
            continue  # Skip private properties

        field = {"label": key.replace("_", " ").title()}

        if isinstance(value, bool):
            field["type"] = "bool"
        elif isinstance(value, int):
            field["type"] = "int"
            field["min"] = -10000
            field["max"] = 10000
        elif isinstance(value, float):
            field["type"] = "float"
            field["min"] = -10000.0
            field["max"] = 10000.0
            field["decimals"] = 4
        elif isinstance(value, str):
            field["type"] = "str"
        elif isinstance(value, list):
            continue  # Skip lists for auto-inference
        else:
            continue

        schema[key] = field

    return schema


class BlockConfigDialog(BaseBlockConfigDialog):
    """
    Generic configuration dialog for blocks.

    Can be used directly for simple blocks by passing a schema dict,
    or subclassed for more complex configuration needs.

    This class provides compatibility with the dict-based schema format
    while using the BaseBlockConfigDialog infrastructure.

    Example:
        schema = {
            "speed": {
                "type": "float",
                "label": "Speed",
                "min": 0.0,
                "max": 1.0,
            },
            "enabled": {
                "type": "bool",
                "label": "Enabled",
            },
        }
        dialog = BlockConfigDialog(properties, schema=schema, title="Motor Config")
    """

    show_live_tune = False  # Generic dialogs don't support live tune by default

    def __init__(
        self,
        properties: dict[str, Any],
        schema: Optional[dict[str, dict]] = None,
        title: str = "Block Configuration",
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize dialog.

        Args:
            properties: Current block properties
            schema: Optional schema defining fields:
                {
                    "field_name": {
                        "type": "int" | "float" | "str" | "bool" | "choice",
                        "label": "Display Label",
                        "min": 0,          # For numeric
                        "max": 100,        # For numeric
                        "decimals": 2,     # For float
                        "choices": [...],  # For choice type
                        "group": "Group Name",  # Optional grouping
                    }
                }
            title: Dialog title
            parent: Parent widget
        """
        # Store schema for compatibility
        self._schema = schema or _infer_schema(properties)

        # Convert schema to fields before calling super().__init__
        self.__class__.fields = _schema_to_fields(self._schema)
        self.__class__.dialog_title = title

        super().__init__(properties, parent=parent, controller=None, slot=0)

# Extensibility Guide

This guide explains how to extend the MARA system. Every extension point requires **only 1 file**.

## Quick Reference

| To Add | Create File | Convention |
|--------|-------------|------------|
| CLI command | `cli/commands/mycommand.py` | Has `register()` function |
| GUI panel | `gui/panels/mypanel.py` | Has `PANEL_META` dict |
| Widget | `gui/widgets/controls/mywidget.py` | Add to `_EXPORTS` |
| Block diagram block | `gui/widgets/block_diagram/blocks/myblock.py` | Add to `_EXPORTS` |
| Workflow | `workflows/calibration/myworkflow.py` | Add to `_EXPORTS` |
| Hardware | `tools/schema/hardware/_sensors.py` | Add to `SENSOR_HARDWARE` |
| Command schema | `tools/schema/commands/_mydomain.py` | Has `*_COMMANDS` dict |
| Service | `services/myservice/` | Add to `_EXPORTS` |

---

## CLI Commands

Create a file in `cli/commands/` with a `register()` function:

```python
# cli/commands/mycommand.py
"""My awesome command."""

def register(subparsers):
    parser = subparsers.add_parser(
        "mycommand",
        help="Do something awesome",
    )
    parser.add_argument("--flag", action="store_true")
    parser.set_defaults(func=cmd_mycommand)

def cmd_mycommand(args):
    print("Hello from mycommand!")
    return 0
```

**That's it!** The command is auto-discovered. Run `mara mycommand`.

---

## GUI Panels

Create a file in `gui/panels/` with `PANEL_META` and a Panel class:

```python
# gui/panels/mypanel.py
"""My panel description."""

# Required: Panel metadata for auto-discovery
PANEL_META = {
    "id": "mypanel",        # Unique ID
    "label": "My Panel",    # Sidebar label
    "order": 50,            # Lower = higher in sidebar
}

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from mara_host.gui.core import GuiSignals, RobotController, GuiSettings

class MyPanelPanel(QWidget):  # Must end with "Panel"
    def __init__(self, signals: GuiSignals, controller: RobotController, settings: GuiSettings):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello from My Panel!"))
```

**That's it!** The panel appears in the sidebar automatically.

---

## Hardware (Sensors, Actuators)

Add an entry to the hardware registry:

```python
# tools/schema/hardware/_sensors.py

SENSOR_HARDWARE = {
    # ... existing sensors ...

    "mysensor": {
        "type": "sensor",
        "interface": "i2c",  # i2c, gpio, uart, spi, adc

        "gui": {
            "label": "My Sensor",
            "color": "#22C55E",
            "outputs": [("data", "DATA")],
        },

        "commands": {
            "CMD_MYSENSOR_ATTACH": {
                "description": "Attach sensor",
                "payload": {"sensor_id": {"type": "int", "default": 0}},
            },
        },

        "telemetry": {
            "section": "TELEM_MYSENSOR",
            "id": 0x0A,
            "format": "sensor_id(u8) value(i16)",
            "size": 3,
        },
    },
}
```

Then run `mara generate all`. See [ADDING_HARDWARE.md](./ADDING_HARDWARE.md) for complete guide.

---

## Command Schemas

Create a file in `tools/schema/commands/` with a `*_COMMANDS` dict:

```python
# tools/schema/commands/_myfeature.py
"""My feature commands."""

MYFEATURE_COMMANDS: dict[str, dict] = {
    "CMD_MY_THING": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Does a thing",
        "payload": {
            "param": {"type": "int", "default": 0},
        },
    },
}
```

**That's it!** Run `mara generate all` to update generated code.

---

## Widgets

Create a widget file and add to `_EXPORTS` in the subpackage:

```python
# gui/widgets/controls/myslider.py
from PySide6.QtWidgets import QWidget

class MySliderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # ... widget implementation
```

Then add to `gui/widgets/controls/__init__.py`:
```python
_EXPORTS = {
    # ... existing exports
    "MySliderWidget": "myslider",
}
```

Now usable as:
```python
from mara_host.gui.widgets import MySliderWidget
# or
from mara_host.gui.widgets.controls import MySliderWidget
```

---

## Workflows

Create a workflow extending `BaseWorkflow`:

```python
# workflows/calibration/my_calibration.py
from mara_host.workflows.base import BaseWorkflow, WorkflowResult

class MyCalibrationWorkflow(BaseWorkflow):
    async def run(self, **kwargs) -> WorkflowResult:
        self.emit_progress(0, "Starting...")
        # ... workflow steps
        self.emit_progress(100, "Done!")
        return WorkflowResult(ok=True, data={"result": "value"})
```

Then add to `workflows/__init__.py`:
```python
_EXPORTS = {
    # ... existing exports
    "MyCalibrationWorkflow": "calibration",
}
```

---

## Services

Import pattern makes services available at the top level:

```python
# Import directly
from mara_host.services import StateService, MotorService

# Or from subpackage
from mara_host.services.control import StateService
```

To add a new service, create a package in `services/` and add to the `_EXPORTS` dict in `services/__init__.py`.

---

## Auto-Discovery Patterns Used

| Extension | Pattern | How It Works |
|-----------|---------|--------------|
| CLI Commands | Scan + register() | `cli/main.py` scans `commands/` for modules with `register()` |
| GUI Panels | Scan + PANEL_META | `main_window.py` scans `panels/` for modules with `PANEL_META` |
| Widgets | Lazy import | `__getattr__` loads from `_EXPORTS` dict on first access |
| Block Diagram | Lazy import | `blocks/__init__.py` uses `_EXPORTS` dict |
| Workflows | Lazy import | `workflows/__init__.py` uses `_EXPORTS` dict |
| Command Schemas | Glob + merge | `commands/__init__.py` globs `_*.py` and merges `*_COMMANDS` dicts |
| Hardware | Registry | `hardware/_sensors.py` defines `SENSOR_HARDWARE` dict |
| Services | Lazy import | `__getattr__` loads modules on first access |

---

## Order Values

Panel `order` values control sidebar position (lower = higher):

| Order | Panel |
|-------|-------|
| 10 | Dashboard |
| 20 | Control |
| 30 | Camera |
| 40 | Commands |
| 50 | Calibration |
| 60 | Testing |
| 70 | Advanced |
| 80 | Diagram |
| 90 | Session |
| 100 | Pinout |
| 110 | Firmware |
| 120 | Config |
| 130 | Logs |

Use values between existing panels to insert new ones.

---

## Benefits

1. **No registration files to edit** - Just create your file
2. **No imports to add** - Auto-discovered
3. **No lists to update** - Auto-merged
4. **Consistent pattern** - Same approach everywhere
5. **Self-documenting** - Metadata in the file itself

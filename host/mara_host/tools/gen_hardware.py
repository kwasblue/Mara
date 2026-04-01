#!/usr/bin/env python3
"""
Generate hardware artifacts from typed schema definitions.

Reads from:
    - SENSORS (schema/hardware/_sensors.py)
    - ACTUATORS (schema/hardware/_actuators.py)
    - TRANSPORTS (schema/hardware/_transports.py)

Generates:
    - Firmware stubs: ISensor/IActuator/ITransport skeletons with TODOs
    - Python API classes: Inheriting from base classes
    - CLI shell commands: Shell command registration (future)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mara_host.tools.schema.hardware import (
    SENSORS,
    ACTUATORS,
    TRANSPORTS,
    SensorDef,
    ActuatorDef,
    TransportDef,
)
from mara_host.tools.schema.telemetry.core import TelemetrySectionDef, FieldDef
from mara_host.tools.schema.commands.core import UNSET, _UnsetType
from mara_host.tools.schema.paths import ROOT, FIRMWARE_INCLUDE


# -----------------------------------------------------------------------------
# Output Paths
# -----------------------------------------------------------------------------

# Firmware output directories
FW_SENSOR_DIR = FIRMWARE_INCLUDE / "sensor" / "generated"
FW_ACTUATOR_DIR = FIRMWARE_INCLUDE / "actuator" / "generated"
FW_TRANSPORT_DIR = FIRMWARE_INCLUDE / "transport" / "generated"

# Python output directories
PY_API_DIR = ROOT.parent / "api" / "generated"


# -----------------------------------------------------------------------------
# Type Mapping
# -----------------------------------------------------------------------------

def cpp_type_for_field(field: FieldDef) -> str:
    """Map telemetry field format to C++ type."""
    fmt_map = {
        "B": "uint8_t",
        "b": "int8_t",
        "H": "uint16_t",
        "h": "int16_t",
        "I": "uint32_t",
        "i": "int32_t",
        "f": "float",
    }
    return fmt_map.get(field.fmt, "uint8_t")


def python_type_for_field(field: FieldDef) -> str:
    """Map telemetry field format to Python type."""
    fmt_map = {
        "B": "int",
        "b": "int",
        "H": "int",
        "h": "int",
        "I": "int",
        "i": "int",
        "f": "float",
    }
    return fmt_map.get(field.fmt, "int")


def python_default_for_field(field: FieldDef) -> str:
    """Get Python default value for a field."""
    if field.fmt == "f":
        return "0.0"
    return "0"


# -----------------------------------------------------------------------------
# Firmware Stub Generation
# -----------------------------------------------------------------------------

def generate_sensor_firmware_stub(sensor: SensorDef) -> str:
    """Generate C++ firmware stub for a sensor."""
    feature_flag = sensor.firmware.feature_flag
    class_name = sensor.firmware.class_name

    # Build Reading struct fields
    reading_fields = []
    to_json_lines = []
    for field in sensor.telemetry.fields:
        cpp_type = cpp_type_for_field(field)
        reading_fields.append(f"        {cpp_type} {field.name} = 0;")
        to_json_lines.append(f'        out["{field.name}"] = reading_.{field.name};')

    reading_struct = "\n".join(reading_fields)
    to_json_body = "\n".join(to_json_lines)

    return f'''// AUTO-GENERATED from SensorDef("{sensor.name}")
// Implement init() and loop() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if {feature_flag}

#include "sensor/ISensor.h"
#include <ArduinoJson.h>

namespace mara {{

class {class_name} : public ISensor {{
public:
    // Auto-generated from telemetry fields
    struct Reading {{
{reading_struct}
    }};

    const char* name() const override {{ return "{sensor.name}"; }}
    uint32_t sampleIntervalMs() const override {{ return {sensor.firmware.sample_interval_ms}; }}

    void init() override {{
        // TODO: Initialize hardware (I2C, GPIO, etc.)
        online_ = true;
    }}

    void loop(uint32_t now_ms) override {{
        if (!online_) return;

        // TODO: Sample hardware and update reading_
        // Example for {sensor.interface} interface:
        //   reading_.value = readHardware();

        lastSampleMs_ = now_ms;
    }}

    void toJson(JsonObject& out) const override {{
{to_json_body}
    }}

    const Reading& reading() const {{ return reading_; }}

private:
    Reading reading_;
    uint32_t lastSampleMs_ = 0;
}};

}} // namespace mara

#endif // {feature_flag}
'''


def generate_actuator_firmware_stub(actuator: ActuatorDef) -> str:
    """Generate C++ firmware stub for an actuator."""
    feature_flag = actuator.firmware.feature_flag
    class_name = actuator.firmware.class_name

    # Build state fields and toJson if telemetry exists
    state_fields = ""
    to_json_body = ""
    if actuator.telemetry:
        fields = []
        json_lines = []
        for field in actuator.telemetry.fields:
            cpp_type = cpp_type_for_field(field)
            fields.append(f"        {cpp_type} {field.name} = 0;")
            json_lines.append(f'        out["{field.name}"] = state_.{field.name};')
        state_fields = "\n".join(fields)
        to_json_body = "\n".join(json_lines)

    state_struct = f"""
    // Auto-generated from telemetry fields
    struct State {{
{state_fields}
    }};
""" if state_fields else ""

    to_json_method = f"""
    void toJson(JsonObject& out) const override {{
{to_json_body}
    }}
""" if to_json_body else ""

    state_member = "    State state_;" if state_fields else ""
    state_getter = "    const State& state() const { return state_; }" if state_fields else ""

    return f'''// AUTO-GENERATED from ActuatorDef("{actuator.name}")
// Implement init() and apply() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if {feature_flag}

#include "actuator/IActuator.h"
#include <ArduinoJson.h>

namespace mara {{

class {class_name} : public IActuator {{
public:
{state_struct}
    const char* name() const override {{ return "{actuator.name}"; }}

    void init() override {{
        // TODO: Initialize hardware (PWM, GPIO, etc.)
        attached_ = true;
    }}

    void apply(const JsonObject& cmd) override {{
        // TODO: Apply command to hardware
        // Commands available: {', '.join(actuator.commands.keys())}
    }}

    void stop() override {{
        // TODO: Emergency stop
    }}
{to_json_method}
    {state_getter}

private:
    bool attached_ = false;
{state_member}
}};

}} // namespace mara

#endif // {feature_flag}
'''


def generate_transport_firmware_stub(transport: TransportDef) -> str:
    """Generate C++ firmware stub for a transport."""
    feature_flag = transport.firmware.feature_flag
    class_name = transport.firmware.class_name

    return f'''// AUTO-GENERATED from TransportDef("{transport.name}")
// Implement init(), send(), and receive() with transport-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if {feature_flag}

#include "transport/ITransport.h"
#include <ArduinoJson.h>

namespace mara {{

class {class_name} : public ITransport {{
public:
    const char* name() const override {{ return "{transport.name}"; }}
    const char* layer() const {{ return "{transport.layer}"; }}

    void init() override {{
        // TODO: Initialize transport ({transport.layer} layer)
        connected_ = false;
    }}

    bool send(const uint8_t* data, size_t len) override {{
        // TODO: Send data over transport
        return false;
    }}

    size_t receive(uint8_t* buffer, size_t maxLen) override {{
        // TODO: Receive data from transport
        return 0;
    }}

    bool isConnected() const override {{ return connected_; }}

private:
    bool connected_ = false;
}};

}} // namespace mara

#endif // {feature_flag}
'''


# -----------------------------------------------------------------------------
# Python API Generation
# -----------------------------------------------------------------------------

def generate_sensor_python_api(sensor: SensorDef) -> str:
    """Generate Python API class for a sensor."""
    api_class = sensor.python.api_class
    reading_class = sensor.python.reading_class
    topic = sensor.python.telemetry_topic

    # Build reading dataclass fields
    fields = []
    parse_lines = []
    for field in sensor.telemetry.fields:
        py_type = python_type_for_field(field)
        default = python_default_for_field(field)
        fields.append(f"    {field.name}: {py_type} = {default}")
        parse_lines.append(f'            {field.name}=data.get("{field.name}", {default}),')

    # Add timestamp field
    fields.append("    ts_ms: int = 0")
    parse_lines.append('            ts_ms=data.get("ts_ms", 0),')

    fields_block = "\n".join(fields)
    parse_block = "\n".join(parse_lines)

    return f'''# AUTO-GENERATED from SensorDef("{sensor.name}")
# Do not edit directly - modify schema/hardware/_sensors.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class {reading_class}:
    """{sensor.description} reading."""
{fields_block}


class {api_class}(TelemetrySensor[{reading_class}]):
    """
    {sensor.description}

    Interface: {sensor.interface}
    Telemetry topic: {topic}
    """

    telemetry_topic = "{topic}"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(robot, sensor_id, auto_subscribe)

    def _parse_reading(self, data: dict) -> {reading_class}:
        return {reading_class}(
{parse_block}
        )
'''


def generate_actuator_python_api(actuator: ActuatorDef) -> str:
    """Generate Python API class for an actuator."""
    api_class = actuator.python.api_class
    state_class = actuator.python.reading_class

    # Build state dataclass fields if telemetry exists
    fields = []
    parse_lines = []
    if actuator.telemetry:
        for field in actuator.telemetry.fields:
            py_type = python_type_for_field(field)
            default = python_default_for_field(field)
            fields.append(f"    {field.name}: {py_type} = {default}")
            parse_lines.append(f'            {field.name}=data.get("{field.name}", {default}),')
        fields.append("    ts_ms: int = 0")
        parse_lines.append('            ts_ms=data.get("ts_ms", 0),')

    fields_block = "\n".join(fields) if fields else "    pass  # No telemetry fields"
    parse_block = "\n".join(parse_lines) if parse_lines else "            pass"

    # Build command methods
    command_methods = []
    for cmd_name, cmd_def in actuator.commands.items():
        method_name = cmd_name.lower().replace("cmd_", "")

        # Build method signature
        sig_parts = []
        call_parts = []
        for field_name, field_spec in cmd_def.payload.items():
            py_type = "int" if field_spec.type == "int" else (
                "float" if field_spec.type == "float" else (
                    "bool" if field_spec.type == "bool" else "str"
                )
            )
            # Check if default is UNSET (required field with no default)
            has_default = not isinstance(field_spec.default, _UnsetType)
            if field_spec.required and not has_default:
                sig_parts.append(f"{field_name}: {py_type}")
            else:
                default = repr(field_spec.default) if has_default else "None"
                sig_parts.append(f"{field_name}: {py_type} = {default}")
            call_parts.append(f'"{field_name}": {field_name}')

        sig = ", ".join(sig_parts)
        if sig:
            sig = ", " + sig
        call_dict = ", ".join(call_parts)

        command_methods.append(f'''
    async def {method_name}(self{sig}) -> None:
        """{cmd_def.description}"""
        await self._robot.client.send_json_cmd("{cmd_name}", {{{call_dict}}})
''')

    methods_block = "".join(command_methods)

    return f'''# AUTO-GENERATED from ActuatorDef("{actuator.name}")
# Do not edit directly - modify schema/hardware/_actuators.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class {state_class}:
    """{actuator.description} state."""
{fields_block}


class {api_class}:
    """
    {actuator.description}

    Interface: {actuator.interface}
    """

    def __init__(self, robot: "Robot", actuator_id: int = 0) -> None:
        self._robot = robot
        self._actuator_id = actuator_id

    @property
    def robot(self) -> "Robot":
        return self._robot

    @property
    def actuator_id(self) -> int:
        return self._actuator_id
{methods_block}
'''


# -----------------------------------------------------------------------------
# Main Generator
# -----------------------------------------------------------------------------

def write_file_if_changed(path: Path, content: str) -> bool:
    """Write file only if content changed. Returns True if written."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return False

    path.write_text(content, encoding="utf-8")
    return True


def main():
    print("[gen_hardware] Generating hardware artifacts from typed schema...")

    written = 0
    skipped = 0

    # --- Firmware Stubs ---
    print("[gen_hardware] Generating firmware stubs...")

    for name, sensor in SENSORS.items():
        filename = f"{sensor.firmware.class_name}.h"
        path = FW_SENSOR_DIR / filename
        content = generate_sensor_firmware_stub(sensor)
        if write_file_if_changed(path, content):
            print(f"  [sensor] {filename}")
            written += 1
        else:
            skipped += 1

    for name, actuator in ACTUATORS.items():
        filename = f"{actuator.firmware.class_name}.h"
        path = FW_ACTUATOR_DIR / filename
        content = generate_actuator_firmware_stub(actuator)
        if write_file_if_changed(path, content):
            print(f"  [actuator] {filename}")
            written += 1
        else:
            skipped += 1

    for name, transport in TRANSPORTS.items():
        filename = f"{transport.firmware.class_name}.h"
        path = FW_TRANSPORT_DIR / filename
        content = generate_transport_firmware_stub(transport)
        if write_file_if_changed(path, content):
            print(f"  [transport] {filename}")
            written += 1
        else:
            skipped += 1

    # --- Python APIs ---
    print("[gen_hardware] Generating Python API classes...")

    for name, sensor in SENSORS.items():
        filename = f"{name}.py"
        path = PY_API_DIR / filename
        content = generate_sensor_python_api(sensor)
        if write_file_if_changed(path, content):
            print(f"  [sensor] {filename}")
            written += 1
        else:
            skipped += 1

    for name, actuator in ACTUATORS.items():
        filename = f"{name}.py"
        path = PY_API_DIR / filename
        content = generate_actuator_python_api(actuator)
        if write_file_if_changed(path, content):
            print(f"  [actuator] {filename}")
            written += 1
        else:
            skipped += 1

    # --- Generate __init__.py for Python API ---
    init_content = generate_python_api_init()
    init_path = PY_API_DIR / "__init__.py"
    if write_file_if_changed(init_path, init_content):
        print(f"  [init] __init__.py")
        written += 1
    else:
        skipped += 1

    print(f"[gen_hardware] Done. {written} files written, {skipped} unchanged.")


def generate_python_api_init() -> str:
    """Generate __init__.py for the generated API module."""
    imports = []
    all_exports = []

    for name, sensor in SENSORS.items():
        api_class = sensor.python.api_class
        reading_class = sensor.python.reading_class
        imports.append(f"from .{name} import {api_class}, {reading_class}")
        all_exports.extend([api_class, reading_class])

    for name, actuator in ACTUATORS.items():
        api_class = actuator.python.api_class
        state_class = actuator.python.reading_class
        imports.append(f"from .{name} import {api_class}, {state_class}")
        all_exports.extend([api_class, state_class])

    imports_block = "\n".join(imports)
    all_block = ",\n    ".join(f'"{e}"' for e in all_exports)

    return f'''# AUTO-GENERATED - Do not edit directly
# Generated from schema/hardware definitions

{imports_block}

__all__ = [
    {all_block},
]
'''


if __name__ == "__main__":
    main()

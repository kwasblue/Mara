#!/usr/bin/env python3
"""
Run all code generators from schema.py.

This is the single entry point for regenerating all generated code artifacts
for both the Host (Python) and MCU (C++) projects.

Usage:
    python generate_all.py

Generated artifacts:
    - Commands: CommandDefs.h, command_defs.py, client_commands.py, commands.json
    - Version: Version.h, version.py
    - Pins: PinConfig.h, pin_config.py
    - GPIO Channels: GpioChannelDefs.h, gpio_channels.py
    - Binary Commands: BinaryCommands.h, binary_commands.py, json_to_binary.py
    - CAN Bus: CanDefs.h, can_defs_generated.py
"""

import sys
from pathlib import Path

# Ensure the tools directory is in the path
TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(TOOLS_DIR))


def main():
    print("=" * 60)
    print("Running all code generators from schema.py")
    print("=" * 60)
    print()

    # Import and run each generator
    import gen_commands
    print("-" * 60)
    gen_commands.main()
    print()

    import generate_pins
    print("-" * 60)
    generate_pins.main()
    print()

    import gpio_mapping_gen
    print("-" * 60)
    gpio_mapping_gen.main()
    print()

    import gen_binary_commands
    print("-" * 60)
    gen_binary_commands.main()
    print()

    import gen_telemetry
    print("-" * 60)
    gen_telemetry.main()
    print()

    import gen_can
    print("-" * 60)
    gen_can.main()
    print()

    import gen_mcp_servers
    print("-" * 60)
    gen_mcp_servers.main()
    print()

    print("=" * 60)
    print("All generators completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

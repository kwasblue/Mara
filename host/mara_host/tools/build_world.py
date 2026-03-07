#!/usr/bin/env python3
"""
gen_all.py

Single entry point to regenerate all auto-generated artifacts for the robot platform:

  - Pins:
      - PinConfig.h       (MCU / ESP32)
      - pin_config.py     (Host / Python)

  - Commands:
      - commands.json     (schema/catalog)
      - CommandDefs.h     (MCU / ESP32)
      - command_defs.py   (Host / Python)

  - GPIO Channels:
      - gpio_channels.json   (schema/catalog)
      - GpioChannelDefs.h    (MCU / ESP32)
      - gpio_channels.py     (Host / Python)

Run:
    python gen_all.py

Optionally, you can still run the individual scripts directly:
    python gen_pins.py
    python gen_commands.py
    python gen_gpio_channels.py
"""

from pathlib import Path
import sys

# Ensure we can import sibling modules when run from other directories
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the individual generators
import generate_pins
import gen_commands
import gpio_mapping_gen
import gen_version


def main() -> None:
    print("=== [gen_all] Starting full schema/code generation ===\n")

    # 1) Pins (PinConfig.h + pin_config.py)
    print(">>> [gen_all] Running gen_pins.py ...")
    generate_pins.main()
    print(">>> [gen_all] gen_pins.py done.\n")

    # 2) Commands (commands.json + CommandDefs.h + command_defs.py)
    print(">>> [gen_all] Running gen_commands.py ...")
    gen_commands.main()
    print(">>> [gen_all] gen_commands.py done.\n")

    # 3) GPIO Channels (gpio_channels.json + GpioChannelDefs.h + gpio_channels.py)
    print(">>> [gen_all] Running gen_gpio_channels.py ...")
    gpio_mapping_gen.main()
    print(">>> [gen_all] gen_gpio_channels.py done.\n")

    # 4) Version Info (Version.h + version.py)
    print(">>> [gen_all] Running gen_version.py ...")
    gen_version.main()
    print(">>> [gen_all] gen_version.py done.\n")   

    print("=== [gen_all] All generators completed successfully. ===")


if __name__ == "__main__":
    main()

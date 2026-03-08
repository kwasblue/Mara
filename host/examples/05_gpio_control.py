#!/usr/bin/env python3
"""
Example 05: GPIO Control

Demonstrates:
- Writing to GPIO pins (LEDs, relays)
- Reading GPIO pins (buttons, switches)
- Toggle functionality
- Using the GPIO API

Prerequisites:
- ESP32 with GPIO pins configured
- LED connected to a GPIO pin for visual feedback

Usage:
    python 05_gpio_control.py /dev/ttyUSB0
    python 05_gpio_control.py tcp:192.168.1.100

Note: Update PIN_LED to match your hardware setup.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mara_host import Robot
from mara_host.api import GPIO


# Configure these for your hardware
PIN_LED = 2       # Built-in LED on many ESP32 boards
PIN_BUTTON = 0    # Boot button on many ESP32 boards
CHANNEL_LED = 0   # Logical channel for LED
CHANNEL_BTN = 1   # Logical channel for button


async def main():
    if len(sys.argv) < 2:
        print("Usage: python 05_gpio_control.py <port_or_tcp>")
        return

    # Parse connection argument
    arg = sys.argv[1]
    if arg.startswith("tcp:"):
        host = arg[4:]
        port = 8080
        if ":" in host:
            host, port_str = host.rsplit(":", 1)
            port = int(port_str)
        robot = Robot(host=host, tcp_port=port)
    else:
        robot = Robot(port=arg)

    print("="*50)
    print("GPIO Control Example")
    print("="*50)
    print(f"LED pin: {PIN_LED}")
    print(f"Button pin: {PIN_BUTTON}")
    print()

    try:
        await robot.connect()
        print(f"Connected to {robot.name}\n")

        # Create GPIO API
        gpio = GPIO(robot)

        # Register channels
        await gpio.register(channel=CHANNEL_LED, pin=PIN_LED, mode="output")
        await gpio.register(channel=CHANNEL_BTN, pin=PIN_BUTTON, mode="input")

        # -------------------------------------------------------
        # 1. Basic GPIO Write
        # -------------------------------------------------------
        print("1. GPIO Write - Blink LED")
        print("   Blinking LED 5 times...")

        for i in range(5):
            await gpio.high(CHANNEL_LED)  # LED ON
            await asyncio.sleep(0.2)
            await gpio.low(CHANNEL_LED)   # LED OFF
            await asyncio.sleep(0.2)
            print(f"   Blink {i+1}/5")

        print()

        # -------------------------------------------------------
        # 2. GPIO Toggle
        # -------------------------------------------------------
        print("2. GPIO Toggle")
        print("   Toggling LED 5 times...")

        for i in range(5):
            await gpio.toggle(CHANNEL_LED)
            await asyncio.sleep(0.3)
            print(f"   Toggle {i+1}/5")

        # Ensure LED is off
        await gpio.low(CHANNEL_LED)
        print()

        # -------------------------------------------------------
        # 3. GPIO Read
        # -------------------------------------------------------
        print("3. GPIO Read")
        print(f"   Reading button pin {PIN_BUTTON}...")
        print("   (Press the BOOT button on ESP32 to see changes)")
        print("   Monitoring for 5 seconds...")

        # Track button state via bus events
        button_states = []

        def on_gpio_ack(data):
            if "value" in data:
                button_states.append(data["value"])

        robot.bus.subscribe("cmd.CMD_GPIO_READ", on_gpio_ack)

        for i in range(5):
            await gpio.read(CHANNEL_BTN)
            await asyncio.sleep(1)
            if button_states:
                print(f"   [{i+1}s] Button value: {button_states[-1]}")
            else:
                print(f"   [{i+1}s] Waiting for response...")

        print()

        # -------------------------------------------------------
        # 4. Pattern Generation
        # -------------------------------------------------------
        print("4. Pattern Generation - SOS")
        print("   Blinking SOS pattern...")

        # SOS: ... --- ...
        async def blink(duration):
            await gpio.high(CHANNEL_LED)
            await asyncio.sleep(duration)
            await gpio.low(CHANNEL_LED)
            await asyncio.sleep(0.1)

        # S: three short
        for _ in range(3):
            await blink(0.1)
        await asyncio.sleep(0.2)

        # O: three long
        for _ in range(3):
            await blink(0.3)
        await asyncio.sleep(0.2)

        # S: three short
        for _ in range(3):
            await blink(0.1)

        print("   SOS pattern complete!")
        print()

        # -------------------------------------------------------
        # 5. Using direct client commands
        # -------------------------------------------------------
        print("5. Direct client commands")
        print("   Using client.cmd_gpio_write directly...")

        # The GPIO API wraps these, but you can use them directly
        await robot.client.cmd_gpio_write(channel=CHANNEL_LED, value=1)
        await asyncio.sleep(0.5)
        await robot.client.cmd_gpio_write(channel=CHANNEL_LED, value=0)
        print("   Done!")
        print()

        print("All GPIO tests complete!")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Ensure LED is off
        try:
            await gpio.low(CHANNEL_LED)
        except:
            pass
        await robot.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

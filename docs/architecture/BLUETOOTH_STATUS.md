# Bluetooth transport status

## Summary

Bluetooth Classic SPP transport is implemented in the MARA repo on both firmware and host sides. As of the latest stabilization pass, the firmware no longer aborts during boot by calling `BluetoothSerial::setPin()` before `begin()`. Practical Linux pairing is still blocked by ESP32/BlueZ authentication behavior, but the transport now boots cleanly enough to keep the rest of the service stack alive.

## What is complete

### Firmware
- `firmware/mcu/include/transport/BleTransport.h` uses `BluetoothSerial` for Classic Bluetooth SPP transport.
- `firmware/mcu/platformio.ini` enables `HAS_BLE=1` in the active/default `esp32_usb` full build path.
- The board advertises as:
  - name: `ESP32-SPP`
  - service: `Serial Port`
  - UUID: `00001101-0000-1000-8000-00805f9b34fb`
  - channel: `1`

### Host
- Host transport exists via `host/mara_host/transport/bluetooth_transport.py`.
- Connection/runtime/CLI plumbing is wired through:
  - `host/mara_host/services/transport/connection_service.py`
  - `host/mara_host/cli/context.py`
  - `host/mara_host/robot.py`
  - `host/mara_host/runtime/robot_runtime.py`
  - `host/mara_host/config/robot_config.py`
  - `host/mara_host/cli/commands/run/ble.py`
  - `host/mara_host/cli/commands/run/shell.py`
  - `host/mara_host/mcp/runtime.py`
  - `host/mara_host/mcp/server.py`
  - `host/mara_host/mcp/http_server.py`

## What was verified
- Firmware builds and flashes successfully with Bluetooth enabled.
- Linux discovery sees `ESP32-SPP`.
- SDP discovery succeeds.
- BlueZ reports the SPP service and RFCOMM channel:
  - `UUID: Serial Port (00001101-0000-1000-8000-00805f9b34fb)`
  - `Channel: 1`

## Current blocker

Pairing fails during authentication on this Linux/BlueZ setup.

Observed behavior:
- `bluetoothctl` can discover the device
- pairing starts
- BlueZ requests numeric confirmation
- pairing fails with:
  - `org.bluez.Error.AuthenticationFailed`

Observed final state after failed attempts:
- `Paired: no`
- `Bonded: no`
- `Trusted: yes` or `no` depending on attempt
- `Connected: no`
- `LegacyPairing: no`

## Experiments attempted
- baseline `BluetoothSerial.begin(name)`
- explicit SSP enable + confirm callback + confirm reply
- fixed PIN via `setPin("1234")`
- GAP IO capability override to `ESP_BT_IO_CAP_NONE`

These did not produce a usable Linux pairing flow in this environment.

## Conclusion

The repo-native Bluetooth transport implementation is in place, but practical Linux use is currently blocked by ESP32 Arduino `BluetoothSerial` / Bluedroid pairing behavior rather than MARA host/runtime plumbing.

## Recommendation
- Prefer TCP for wireless control.
- Keep USB serial for setup and recovery.
- Keep BLE disabled in the default `esp32_usb` dev image until ESP32 Classic Bluetooth can boot reliably alongside the rest of the transport stack on this board/profile.
- Treat Bluetooth transport as experimental until there is a reason to invest in lower-level ESP-IDF/Bluedroid auth work.

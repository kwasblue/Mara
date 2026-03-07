# mara_host/examples/__init__.py
"""
Examples demonstrating the full mara_host system.

Examples:
    01_serial_connection.py     - Connect to ESP32 via USB serial
    02_tcp_connection.py        - Connect to ESP32 via WiFi/TCP
    03_command_basics.py        - Send commands and handle ACKs
    04_telemetry_stream.py      - Receive and process telemetry data
    05_gpio_control.py          - Control GPIO pins
    06_motor_control.py         - DC motor and motion control
    07_encoder_feedback.py      - Read encoder sensors
    08_session_recording.py     - Record sessions for analysis
    09_full_robot_control.py    - Complete control loop example

Run examples:
    cd mara_host/examples
    python 01_serial_connection.py

Prerequisites:
    - ESP32 with mara_host firmware connected
    - For serial: USB cable connected
    - For TCP: ESP32 and host on same network
"""

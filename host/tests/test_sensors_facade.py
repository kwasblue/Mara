import time

from mara_host.config import RobotConfig


def test_robot_sensors_facade_builds_interfaces_from_config():
    cfg = RobotConfig.from_dict(
        {
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {
                "imu": {"type": "imu", "degradation": {"required": True, "allow_missing": True}},
                "front_ultra": {"type": "ultrasonic", "sensor_id": 2, "trig_pin": 5, "echo_pin": 18},
            },
        }
    )

    robot = cfg.create_robot()
    facade = robot.sensors

    assert facade.names() == ["front_ultra", "imu"]
    assert facade.interface("imu").__class__.__name__ == "IMU"
    assert facade.interface("front_ultra").__class__.__name__ == "Ultrasonic"
    assert facade.health("imu").required is True
    assert facade.health("imu").allow_missing is True
    assert facade.health("front_ultra").sensor_id == 2


def test_robot_sensors_facade_updates_health_from_telemetry():
    cfg = RobotConfig.from_dict(
        {
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {
                "imu": {"type": "imu"},
                "front_ultra": {"type": "ultrasonic", "sensor_id": 0},
            },
        }
    )

    robot = cfg.create_robot()
    facade = robot.sensors

    class Entry:
        def __init__(self, kind, sensor_id, present, healthy, degraded, stale, detail=0):
            self.kind = kind
            self.sensor_id = sensor_id
            self.present = present
            self.healthy = healthy
            self.degraded = degraded
            self.stale = stale
            self.detail = detail

    class Packet:
        ts_ms = 1234
        sensors = [
            Entry("imu", 0, True, True, False, False),
            Entry("ultrasonic", 0, True, False, True, False, 2),
        ]

    facade._on_sensor_health(Packet())

    assert facade.health("imu").healthy is True
    assert facade.health("imu").degraded is False
    assert facade.health("imu").last_telemetry_ts_ms == 1234
    assert facade.health("front_ultra").healthy is False
    assert facade.health("front_ultra").degraded is True
    assert facade.health("front_ultra").detail == 2


def test_robot_sensors_facade_enforces_explicit_stale_after_ms_policy():
    cfg = RobotConfig.from_dict(
        {
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {
                "imu": {
                    "type": "imu",
                    "degradation": {"required": True, "allow_missing": False, "stale_after_ms": 25, "fail_open": False},
                }
            },
        }
    )

    facade = cfg.create_robot().sensors

    class Entry:
        kind = "imu"
        sensor_id = 0
        present = True
        healthy = True
        degraded = False
        stale = False
        detail = 0

    class Packet:
        ts_ms = 55
        sensors = [Entry()]

    facade._on_sensor_health(Packet())
    health = facade.health("imu")
    assert health.available is True

    health.last_update_monotonic_s = time.monotonic() - 0.050
    assert facade.health("imu").stale is True
    decision = facade.decision("imu")
    assert decision.reason == "stale"
    assert decision.blocking is True


def test_robot_sensors_facade_evaluates_control_graph_requirements_against_policy():
    cfg = RobotConfig.from_dict(
        {
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {
                "imu": {
                    "type": "imu",
                    "degradation": {"required": True, "allow_missing": True, "fail_open": True, "fallback": "hold_last"},
                }
            },
        }
    )

    facade = cfg.create_robot().sensors
    report = facade.evaluate_graph_requirements(
        {
            "schema_version": 1,
            "slots": [
                {
                    "id": "imu_pitch_servo",
                    "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                    "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
                }
            ],
        }
    )

    assert report.ok is True
    assert report.decisions[0].kind == "imu"
    assert report.decisions[0].reason == "missing"
    assert report.decisions[0].fallback == "hold_last"


def test_robot_sensors_facade_builds_generic_interface_for_lidar_when_configured():
    cfg = RobotConfig.from_dict(
        {
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {
                "front_lidar": {"type": "lidar", "topic": "telemetry.lidar"},
            },
        }
    )

    facade = cfg.create_robot().sensors
    interface = facade.interface("front_lidar")
    assert interface is not None
    assert interface.__class__.__name__ == "TelemetryMirrorSensor"

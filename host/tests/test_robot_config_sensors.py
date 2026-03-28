from mara_host.config import RobotConfig


def test_robot_config_builds_sensor_abstractions_and_topics():
    cfg = RobotConfig.from_dict(
        {
            "name": "testbot",
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {
                "imu": {
                    "type": "imu",
                    "degradation": {"required": True, "allow_missing": True, "stale_after_ms": 250},
                },
                "ultrasonic": {
                    "trig_pin": 5,
                    "echo_pin": 18,
                    "sensor_id": 2,
                },
            },
        }
    )

    imu = cfg.get_sensor("imu")
    ultra = cfg.get_sensor("ultrasonic")

    assert imu is not None
    assert imu.transport == "telemetry"
    assert imu.topic == "telemetry.imu"
    assert imu.degradation.required is True
    assert imu.degradation.allow_missing is True
    assert imu.degradation.stale_after_ms == 250

    assert ultra is not None
    assert ultra.sensor_id == 2
    assert ultra.pins == {"trig_pin": 5, "echo_pin": 18}
    assert [sensor.name for sensor in cfg.iter_sensors()] == ["imu", "ultrasonic"]


def test_robot_config_warns_for_degradable_required_sensor_and_bad_policy():
    cfg = RobotConfig.from_dict(
        {
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {
                "imu": {
                    "enabled": False,
                    "degradation": {"required": True, "allow_missing": True, "stale_after_ms": -5},
                }
            },
        }
    )

    report = cfg.validate_report()

    assert any("stale_after_ms must be positive" in err for err in report.errors)
    assert any("marked required but also allow_missing=true" in warning for warning in report.warnings)
    assert any("disabled but marked required" in warning for warning in report.warnings)


def test_create_robot_preserves_config_reference_for_incremental_sensor_lookup():
    cfg = RobotConfig.from_dict(
        {
            "transport": {"type": "serial", "port": "/dev/null"},
            "sensors": {"imu": {}},
        }
    )

    robot = cfg.create_robot()

    assert robot.config is cfg
    assert robot.get_sensor_config("imu") is cfg.get_sensor("imu")

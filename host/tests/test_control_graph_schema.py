from mara_host.tools.schema.control_graph.schema import (
    GRAPH_SCHEMA_VERSION,
    ControlGraphValidationError,
    GraphNodeConfig,
    GraphSlotConfig,
    ControlGraphConfig,
    graph_json_schema,
    normalize_graph_config,
    normalize_graph_model,
)
from mara_host.tools.schema.control_graph.builders import (
    PIDConfig,
    build_pid_graph,
    build_simple_pid_graph,
)


def test_normalize_graph_config_applies_defaults() -> None:
    cfg = {
        "slots": [
            {
                "id": "imu_pitch_servo",
                "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                "transforms": [
                    {"type": "deadband", "params": {"threshold": 1.0}},
                    {"type": "scale", "params": {"factor": 3.0}},
                    {"type": "clamp", "params": {"min": -90.0, "max": 90.0}},
                    {"type": "offset", "params": {"value": 90.0}},
                ],
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            }
        ]
    }

    out = normalize_graph_config(cfg)

    assert out["schema_version"] == GRAPH_SCHEMA_VERSION
    assert out["slots"][0]["enabled"] is True
    assert out["slots"][0]["rate_hz"] is None
    assert out["slots"][0]["source"]["type"] == "imu_axis"
    assert out["slots"][0]["sink"]["type"] == "servo_angle"


def test_normalize_graph_model_returns_typed_objects() -> None:
    model = normalize_graph_model(
        {
            "slots": [
                {
                    "id": "const_gpio",
                    "source": {"type": "constant", "params": {"value": 1.0}},
                    "sink": {"type": "gpio_write", "params": {"channel": 0}},
                }
            ]
        }
    )

    assert isinstance(model, ControlGraphConfig)
    assert model.schema_version == GRAPH_SCHEMA_VERSION
    assert isinstance(model.slots[0], GraphSlotConfig)
    assert isinstance(model.slots[0].source, GraphNodeConfig)
    assert model.slots[0].sink is not None
    assert model.to_dict()["slots"][0]["sink"]["type"] == "gpio_write"


def test_normalize_graph_config_accepts_typed_objects_as_compat_input() -> None:
    model = ControlGraphConfig(
        slots=(
            GraphSlotConfig(
                id="typed",
                source=GraphNodeConfig(type="constant", params={"value": 0.5}),
                sink=GraphNodeConfig(type="gpio_write", params={"channel": 1}),
            ),
        )
    )

    out = normalize_graph_config(model)
    assert out["schema_version"] == GRAPH_SCHEMA_VERSION
    assert out["slots"][0]["id"] == "typed"
    assert out["slots"][0]["sink"]["params"]["channel"] == 1


def test_normalize_graph_config_rejects_unknown_type() -> None:
    cfg = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "slots": [
            {
                "id": "bad",
                "source": {"type": "nope", "params": {}},
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            }
        ],
    }

    try:
        normalize_graph_config(cfg)
        assert False, "expected validation error"
    except ControlGraphValidationError as exc:
        assert "unknown" in str(exc)


def test_normalize_graph_config_rejects_duplicate_slot_id() -> None:
    cfg = {
        "slots": [
            {
                "id": "dup",
                "source": {"type": "constant", "params": {"value": 1.0}},
                "sink": {"type": "gpio_write", "params": {"channel": 0}},
            },
            {
                "id": "dup",
                "source": {"type": "constant", "params": {"value": 0.0}},
                "sink": {"type": "gpio_write", "params": {"channel": 1}},
            },
        ]
    }

    try:
        normalize_graph_config(cfg)
        assert False, "expected validation error"
    except ControlGraphValidationError as exc:
        assert "duplicate slot id" in str(exc)


def test_graph_json_schema_has_slot_shape() -> None:
    schema = graph_json_schema()
    assert schema["properties"]["schema_version"]["const"] == GRAPH_SCHEMA_VERSION
    assert "slot" in schema["definitions"]
    assert "slots" in schema["properties"]


def test_normalize_graph_config_accepts_stateful_generic_transforms() -> None:
    cfg = {
        "slots": [
            {
                "id": "imu_pitch_servo",
                "rate_hz": 20,
                "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                "transforms": [
                    {"type": "deadband", "params": {"threshold": 2.0}},
                    {"type": "clamp", "params": {"min": -25.0, "max": 25.0}},
                    {"type": "scale", "params": {"factor": 0.8}},
                    {"type": "offset", "params": {"value": 90.0}},
                    {"type": "clamp", "params": {"min": 60.0, "max": 120.0}},
                    {"type": "lowpass", "params": {"alpha": 0.25}},
                    {"type": "delta_gate", "params": {"threshold": 1.0}},
                    {"type": "slew_rate", "params": {"rate": 90.0}},
                ],
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            }
        ]
    }

    out = normalize_graph_config(cfg)
    kinds = [node["type"] for node in out["slots"][0]["transforms"]]
    assert "delta_gate" in kinds
    assert "slew_rate" in kinds


def test_normalize_graph_config_rejects_negative_slew_rate() -> None:
    cfg = {
        "slots": [
            {
                "id": "bad_slew",
                "source": {"type": "constant", "params": {"value": 0.0}},
                "transforms": [{"type": "slew_rate", "params": {"rate": -1.0}}],
                "sink": {"type": "gpio_write", "params": {"channel": 0}},
            }
        ]
    }

    try:
        normalize_graph_config(cfg)
        assert False, "expected validation error"
    except ControlGraphValidationError as exc:
        assert "rate" in str(exc)


def test_normalize_graph_config_accepts_signal_read_source() -> None:
    """Test signal_read source for cross-slot communication."""
    cfg = {
        "slots": [
            {
                "id": "read_from_signal",
                "source": {"type": "signal_read", "params": {"signal_id": 5}},
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            }
        ]
    }

    out = normalize_graph_config(cfg)
    assert out["slots"][0]["source"]["type"] == "signal_read"
    assert out["slots"][0]["source"]["params"]["signal_id"] == 5
    assert out["slots"][0]["source"]["params"]["fallback"] == 0.0


def test_normalize_graph_config_accepts_signal_write_sink() -> None:
    """Test signal_write sink for cross-slot communication."""
    cfg = {
        "slots": [
            {
                "id": "write_to_signal",
                "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                "transforms": [{"type": "scale", "params": {"factor": 2.0}}],
                "sink": {"type": "signal_write", "params": {"signal_id": 10}},
            }
        ]
    }

    out = normalize_graph_config(cfg)
    assert out["slots"][0]["sink"]["type"] == "signal_write"
    assert out["slots"][0]["sink"]["params"]["signal_id"] == 10


def test_normalize_graph_config_accepts_signal_transforms() -> None:
    """Test signal_recall and signal_add transforms for merging."""
    cfg = {
        "slots": [
            {
                "id": "merge_signals",
                "source": {"type": "signal_read", "params": {"signal_id": 1}},
                "transforms": [
                    {"type": "tap", "params": {"name": "a"}},
                    {"type": "signal_recall", "params": {"signal_id": 2}},
                    {"type": "tap", "params": {"name": "b"}},
                    {"type": "sum", "params": {"inputs": ["a", "b"]}},
                ],
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            }
        ]
    }

    out = normalize_graph_config(cfg)
    kinds = [t["type"] for t in out["slots"][0]["transforms"]]
    assert "signal_recall" in kinds


def test_normalize_graph_config_signal_add_with_scale() -> None:
    """Test signal_add transform with scale parameter."""
    cfg = {
        "slots": [
            {
                "id": "add_scaled_signal",
                "source": {"type": "signal_read", "params": {"signal_id": 1}},
                "transforms": [
                    {"type": "signal_add", "params": {"signal_id": 2, "scale": 0.5}},
                ],
                "sink": {"type": "motor_speed", "params": {"motor_id": 0}},
            }
        ]
    }

    out = normalize_graph_config(cfg)
    signal_add = out["slots"][0]["transforms"][0]
    assert signal_add["type"] == "signal_add"
    assert signal_add["params"]["signal_id"] == 2
    assert signal_add["params"]["scale"] == 0.5


def test_parallel_slots_via_signals() -> None:
    """Test the full parallel processing pattern with signal bus."""
    cfg = {
        "slots": [
            # Chain A: process IMU and write to signal 1
            {
                "id": "chain_a",
                "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                "transforms": [{"type": "scale", "params": {"factor": 0.5}}],
                "sink": {"type": "signal_write", "params": {"signal_id": 1}},
            },
            # Chain B: process same IMU differently and write to signal 2
            {
                "id": "chain_b",
                "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                "transforms": [{"type": "offset", "params": {"value": 10.0}}],
                "sink": {"type": "signal_write", "params": {"signal_id": 2}},
            },
            # Merger: read both signals, sum, output to servo
            {
                "id": "merger",
                "source": {"type": "signal_read", "params": {"signal_id": 1}},
                "transforms": [
                    {"type": "signal_add", "params": {"signal_id": 2}},
                ],
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            },
        ]
    }

    out = normalize_graph_config(cfg)
    assert len(out["slots"]) == 3
    assert out["slots"][0]["sink"]["type"] == "signal_write"
    assert out["slots"][1]["sink"]["type"] == "signal_write"
    assert out["slots"][2]["source"]["type"] == "signal_read"


def test_build_simple_pid_graph() -> None:
    """Test PID graph builder generates valid config."""
    graph = build_simple_pid_graph(
        motor_id=0,
        encoder_id=0,
        kp=1.0,
        ki=0.1,
        kd=0.01,
        ticks_per_rad=400.0,
    )

    # Should validate successfully
    out = normalize_graph_config(graph)

    # Should have 6 slots: encoder, error, P, I, D, output
    assert len(out["slots"]) == 6

    # Check slot structure
    slot_ids = [s["id"] for s in out["slots"]]
    assert "pid_encoder" in slot_ids
    assert "pid_error" in slot_ids
    assert "pid_p" in slot_ids
    assert "pid_i" in slot_ids
    assert "pid_d" in slot_ids
    assert "pid_output" in slot_ids

    # Final slot should output to motor
    output_slot = next(s for s in out["slots"] if s["id"] == "pid_output")
    assert output_slot["sink"]["type"] == "motor_speed"
    assert output_slot["sink"]["params"]["motor_id"] == 0


def test_build_pid_graph_with_config() -> None:
    """Test PID graph builder with full config object."""
    config = PIDConfig(
        motor_id=1,
        encoder_id=1,
        kp=2.0,
        ki=0.5,
        kd=0.1,
        i_min=-50.0,
        i_max=50.0,
        output_min=-0.5,
        output_max=0.5,
        ticks_per_rad=200.0,
        d_lowpass_alpha=0.3,  # Add lowpass filter on D term
        prefix="motor1",
    )

    graph = build_pid_graph(config)
    out = normalize_graph_config(graph.to_dict())

    # Check custom prefix
    slot_ids = [s["id"] for s in out["slots"]]
    assert "motor1_encoder" in slot_ids
    assert "motor1_output" in slot_ids

    # Check D term has lowpass filter
    d_slot = next(s for s in out["slots"] if s["id"] == "motor1_d")
    transform_types = [t["type"] for t in d_slot["transforms"]]
    assert "derivative" in transform_types
    assert "lowpass" in transform_types

    # Check output limits
    output_slot = next(s for s in out["slots"] if s["id"] == "motor1_output")
    clamp_transform = next(t for t in output_slot["transforms"] if t["type"] == "clamp")
    assert clamp_transform["params"]["min"] == -0.5
    assert clamp_transform["params"]["max"] == 0.5

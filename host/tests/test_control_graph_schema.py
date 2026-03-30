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

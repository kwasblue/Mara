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

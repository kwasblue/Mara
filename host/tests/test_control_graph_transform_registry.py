from mara_host.tools.schema.control_graph.transforms import TRANSFORM_DEFS


def test_transform_registry_exposes_incremental_plugin_set():
    expected = {
        "abs",
        "negate",
        "map",
        "hysteresis",
        "median",
        "threshold",
        "toggle",
        "oscillator",
        "pulse",
        "derivative",
        "integrator",
        "tap",
        "recall",
        "sum",
    }
    assert expected.issubset(set(TRANSFORM_DEFS))


def test_transform_registry_preserves_impl_keys_for_plugin_dispatch():
    assert TRANSFORM_DEFS["tap"].impl_key == "transform.tap"
    assert TRANSFORM_DEFS["recall"].impl_key == "transform.recall"
    assert TRANSFORM_DEFS["sum"].impl_key == "transform.sum"

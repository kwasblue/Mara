import json
from pathlib import Path



def test_basic_metrics_outputs(tmp_path: Path):
    """Test basic_metrics computes session metrics correctly."""
    from mara_host.research.metrics import basic_metrics

    session = tmp_path / "session.jsonl"
    rows = [
        {"ts_ns": 1, "event": "transport.rx", "n": 10},
        {"ts_ns": 2, "event": "transport.tx", "n": 20},
        {"ts_ns": 3, "event": "transport.rx", "n": 15},
        {"ts_ns": 4, "event": "stats.snapshot", "connected": True},
    ]
    session.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    m = basic_metrics(str(session))
    assert isinstance(m, dict)
    assert "counts" in m
    assert "bytes" in m
    assert m["counts"]["rx"] == 2
    assert m["counts"]["tx"] == 1
    assert m["bytes"]["rx_total"] == 25
    assert m["bytes"]["tx_total"] == 20

import json
from pathlib import Path

import pytest


def _import_metrics_and_bench():
    from mara_host.research.metrics import basic_metrics  # type: ignore

    # Your tree shows mara_host/research/bechmarks.py (typo), so support both
    try:
        from mara_host.research.bechmarks import run_benchmark  # type: ignore
    except Exception:
        from mara_host.research.benchmarks import run_benchmark  # type: ignore

    return basic_metrics, run_benchmark


def test_basic_metrics_and_benchmark_outputs(tmp_path: Path):
    basic_metrics, run_benchmark = _import_metrics_and_bench()

    session = tmp_path / "session.jsonl"
    rows = [
        {"ts_ns": 1, "event": "cmd.sent", "seq": 1, "cmd_type": "CMD_PING"},
        {"ts_ns": 2, "event": "cmd.ack", "seq": 1, "ok": True},
        {"ts_ns": 3, "event": "stats.snapshot", "connected": True},
    ]
    session.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    m = basic_metrics(str(session))
    assert isinstance(m, dict)

    out_json = tmp_path / "benchmark_out.json"
    run_benchmark(str(session), str(out_json))

    assert out_json.exists()
    parsed = json.loads(out_json.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)

import json
from pathlib import Path

import pytest

# Skip if pandas not installed (research module requires pandas)
pandas = pytest.importorskip("pandas", reason="pandas not installed")


def _import_replay():
    from mara_host.research.replay import SessionReplay  # type: ignore
    return SessionReplay


def test_session_replay_to_dataframe(tmp_path: Path):
    SessionReplay = _import_replay()

    p = tmp_path / "session.jsonl"
    rows = [
        {"ts_ns": 1, "event": "cmd.sent", "seq": 10, "cmd_type": "CMD_PING"},
        {"ts_ns": 2, "event": "cmd.ack", "seq": 10, "ok": True},
        {"ts_ns": 3, "event": "stats.snapshot", "connected": True},
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    rep = SessionReplay(str(p))
    df = rep.to_dataframe()

    # keep assertions flexible: just confirm basics
    assert len(df) == 3
    assert "event" in df.columns
    assert "ts_ns" in df.columns

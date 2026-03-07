import json
from pathlib import Path

import pytest


def _import_bus_and_recording():
    from mara_host.core.event_bus import EventBus  # type: ignore

    # recording wrapper lives in mara_host/research/recording.py per your tree
    from mara_host.research.recording import RecordingEventBus  # type: ignore

    # MaraLogBundle lives in mara_host/logger/logger.py per your tree
    try:
        from mara_host.logger.logger import MaraLogBundle  # type: ignore
    except Exception:
        from mara_host.logging.logger import MaraLogBundle  # type: ignore

    return EventBus, RecordingEventBus, MaraLogBundle


def test_recording_event_bus_passthrough_and_logs(tmp_path: Path):
    EventBus, RecordingEventBus, MaraLogBundle = _import_bus_and_recording()

    # Create a log bundle in tmp dir
    bundle = MaraLogBundle(name="testbus", log_dir=str(tmp_path), console=False)

    inner = EventBus()
    rec = RecordingEventBus(inner_bus=inner, bundle=bundle)

    got = {}

    def handler(data):
        got["data"] = data

    rec.subscribe("demo.topic", handler)
    rec.publish("demo.topic", {"k": 123})

    assert got["data"] == {"k": 123}

    # Ensure JSONL got *something* recorded
    bundle.close()
    jsonl_path = Path(bundle.events.path)
    assert jsonl_path.exists()
    text = jsonl_path.read_text(encoding="utf-8").strip()
    assert text, "Expected recording JSONL to be non-empty"

    # and it’s valid JSONL
    for line in text.splitlines():
        json.loads(line)

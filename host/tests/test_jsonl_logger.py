import json
from pathlib import Path



def _import_jsonl_logger():
    # Current structure shows mara_host/logger/logger.py
    try:
        from mara_host.logger.logger import JsonlLogger  # type: ignore
        return JsonlLogger
    except Exception:
        # Older path you showed earlier: mara_host/logging/logger.py
        from mara_host.logging.logger import JsonlLogger  # type: ignore
        return JsonlLogger


def test_jsonl_logger_writes_valid_json_lines(tmp_path: Path):
    JsonlLogger = _import_jsonl_logger()

    p = tmp_path / "session.jsonl"
    logger = JsonlLogger(str(p))
    logger.write("hello", a=1, b={"x": 2}, c=[1, 2, 3])
    logger.write("bytes_test", blob=b"\x01\x02\x03\x04")
    logger.close()

    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    for line in lines:
        obj = json.loads(line)
        assert "ts_ns" in obj
        assert "event" in obj

    obj2 = json.loads(lines[1])
    assert obj2["event"] == "bytes_test"
    # Your normalizer turns bytes into a dict
    assert isinstance(obj2["blob"], dict)
    assert "bytes_len" in obj2["blob"]

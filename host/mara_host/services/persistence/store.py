from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from mara_host.tools.schema.control_graph.schema import ControlGraphConfig, normalize_graph_model


class JsonArtifactStore:
    """Minimal JSON-backed persistence store for host-side MARA artifacts."""

    def __init__(self, root: str | Path, namespace: str):
        self.root = Path(root).expanduser()
        self.namespace = namespace
        self.path = self.root / f"{namespace}.json"

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text())

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.path)
        return payload

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


class ControlGraphStore(JsonArtifactStore):
    """Stores control-graph definitions only; execution state is sanitized on restore."""

    def __init__(self, root: str | Path):
        super().__init__(root, "control_graph")

    def save_graph(self, graph: dict[str, Any] | ControlGraphConfig, *, source: str = "host") -> dict[str, Any]:
        graph_model = normalize_graph_model(graph)
        payload = {
            "kind": "control_graph",
            "version": 1,
            "saved_at": time.time(),
            "source": source,
            "graph": graph_model.to_dict(),
        }
        return self.save(payload)

    def load_graph(self) -> dict[str, Any] | None:
        model = self.load_graph_model()
        return model.to_dict() if model is not None else None

    def load_graph_model(self) -> ControlGraphConfig | None:
        payload = self.load()
        if not payload:
            return None
        graph = payload.get("graph")
        if not isinstance(graph, dict):
            return None
        return normalize_graph_model(graph)


class CalibrationStore(JsonArtifactStore):
    """Stores calibration snapshots keyed by subsystem/name."""

    def __init__(self, root: str | Path):
        super().__init__(root, "calibrations")

    def upsert(self, name: str, values: dict[str, Any], *, calibration_type: str = "generic") -> dict[str, Any]:
        payload = self.load() or {"kind": "calibrations", "version": 1, "records": {}}
        payload.setdefault("records", {})[name] = {
            "type": calibration_type,
            "saved_at": time.time(),
            "values": values,
        }
        return self.save(payload)


class DiagnosticRecordStore(JsonArtifactStore):
    """Stores lightweight diagnostic snapshots for later inspection."""

    def __init__(self, root: str | Path):
        super().__init__(root, "diagnostics")

    def append(self, name: str, details: dict[str, Any]) -> dict[str, Any]:
        payload = self.load() or {"kind": "diagnostics", "version": 1, "records": []}
        payload.setdefault("records", []).append(
            {
                "name": name,
                "captured_at": time.time(),
                "details": details,
            }
        )
        return self.save(payload)

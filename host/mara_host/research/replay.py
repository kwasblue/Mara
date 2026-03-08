# mara_host/research/replay.py
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Optional
import pandas as pd

class SessionReplay:
    def __init__(self, jsonl_path: str):
        self.path = str(jsonl_path)
        self.rows = list(self._load(self.path))

    def _load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

    async def replay(self, speed: float = 1.0, *, event_prefix: Optional[str] = None) -> AsyncIterator[dict[str, Any]]:
        """
        Replays rows with original timing scaled by 'speed'.
        Uses your Jsonl schema: ts_ns + event + other fields.
        """
        prev_ts = None
        for row in self.rows:
            if event_prefix and not str(row.get("event", "")).startswith(event_prefix):
                continue

            ts = int(row.get("ts_ns", 0))
            if prev_ts is not None and ts and prev_ts:
                dt_s = (ts - prev_ts) / 1e9
                await asyncio.sleep(max(0.0, dt_s / max(speed, 1e-9)))

            yield row
            prev_ts = ts

    def to_dataframe(self):
        return pd.DataFrame(self.rows)


async def replay_bus_publishes(bus, jsonl_path: str, speed: float = 1.0):
    """
    Replays only bus.publish events back into a bus so your modules can re-consume.
    """
    rep = SessionReplay(jsonl_path)
    async for row in rep.replay(speed=speed, event_prefix="bus."):
        if row["event"] == "bus.publish":
            bus.publish(row["topic"], row["data"])

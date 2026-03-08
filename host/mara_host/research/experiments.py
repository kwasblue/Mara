# mara_host/research/experiments.py
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

def _maybe_await(x):
    import asyncio
    return x if not asyncio.iscoroutine(x) else x

@dataclass
class ExperimentConfig:
    name: str
    duration_s: float
    parameters: dict[str, Any]

@dataclass
class ExperimentResult:
    name: str
    parameters: dict[str, Any]
    metrics: dict[str, Any]
    session_jsonl: str
    started_ns: int
    ended_ns: int


class ExperimentRunner:
    """
    Usage:
      - start a MaraLogBundle per run (unique name)
      - apply parameters to robot/sim
      - run duration
      - compute metrics from the resulting jsonl
    """
    def __init__(
        self,
        *,
        log_dir: str = "logs",
        apply_params: Callable[[ExperimentConfig], Any],
        run_body: Callable[[ExperimentConfig], Any],
        compute_metrics: Callable[[str], dict[str, Any]],
    ):
        self.log_dir = log_dir
        self.apply_params = apply_params
        self.run_body = run_body
        self.compute_metrics = compute_metrics

    async def run(self, cfg: ExperimentConfig, *, bundle_factory):
        started = time.time_ns()

        bundle = bundle_factory(cfg.name)  # returns MaraLogBundle (your logger)
        try:
            await _maybe_await(self.apply_params(cfg))
            await _maybe_await(self.run_body(cfg))
        finally:
            bundle.close()

        session_jsonl = str(Path(self.log_dir) / f"{cfg.name}.jsonl")
        metrics = self.compute_metrics(session_jsonl)

        ended = time.time_ns()
        return ExperimentResult(
            name=cfg.name,
            parameters=cfg.parameters,
            metrics=metrics,
            session_jsonl=session_jsonl,
            started_ns=started,
            ended_ns=ended,
        )

    async def sweep(self, base: ExperimentConfig, param: str, values: list[Any], *, bundle_factory):
        out = []
        for v in values:
            cfg = ExperimentConfig(
                name=f"{base.name}_{param}={v}",
                duration_s=base.duration_s,
                parameters={**base.parameters, param: v},
            )
            out.append(await self.run(cfg, bundle_factory=bundle_factory))
        return out

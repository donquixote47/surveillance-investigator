"""Run one session day: background market plus a sampled mix of injected scenarios."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .agents import build_background
from .config import SimConfig
from .scenarios import SCENARIOS, ScenarioSpec, false_specs, inject, true_specs
from .session import Session, SessionTables
from .types import NS_PER_S


@dataclass
class MixConfig:
    true_per_session: float = 1.3  # expected number of TRUE_ABUSE injections per session
    false_per_session: float = 4.0
    first_injection_after_s: int = 20 * 60  # let the book warm up
    last_injection_before_s: int = 20 * 60
    min_gap_s: int = 240  # between injection starts


def _weighted_pick(rng: np.random.Generator, specs: list[ScenarioSpec]) -> ScenarioSpec:
    w = np.array([s.weight for s in specs], dtype=float)
    return specs[int(rng.choice(len(specs), p=w / w.sum()))]


def run_session(
    cfg: SimConfig, seed: int, date: str, mix: MixConfig | None = None, scenario_ids: list[str] | None = None
) -> SessionTables:
    """`scenario_ids` forces an explicit list of scenarios (used by tests); otherwise the mix is sampled."""
    mix = mix or MixConfig()
    session = Session(cfg, seed, date)
    session.start_background_processes()
    build_background(session)

    rng = session.rng
    if scenario_ids is None:
        n_true = int(rng.poisson(mix.true_per_session))
        n_false = int(rng.poisson(mix.false_per_session))
        chosen = [_weighted_pick(rng, true_specs()) for _ in range(n_true)] + [
            _weighted_pick(rng, false_specs()) for _ in range(n_false)
        ]
    else:
        chosen = [SCENARIOS[s] for s in scenario_ids]
    rng.shuffle(chosen)  # type: ignore[arg-type]

    lo = session.open_ts + mix.first_injection_after_s * NS_PER_S
    hi = session.close_ts - mix.last_injection_before_s * NS_PER_S
    n = len(chosen)
    if n:
        # spread starts evenly with jitter, keeping a minimum gap
        slot = (hi - lo) / n
        starts = sorted(int(lo + slot * i + rng.uniform(0, max(1, slot - mix.min_gap_s * NS_PER_S))) for i in range(n))
        tag = date[5:7] + date[8:10]
        for k, (spec, t0) in enumerate(zip(chosen, starts, strict=True)):
            tid = f"T-X{tag}-{k + 1:02d}"
            inject(session, spec, tid, t0)

    session.run()
    return session.tables()

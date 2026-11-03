"""One simulated trading session: clock, book, background agents, market events, scenarios."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .book import OrderBook
from .config import SimConfig
from .kernel import Kernel
from .types import (
    NS_PER_MS,
    NS_PER_S,
    ORDER_EVENT_COLUMNS,
    TRADE_COLUMNS,
    Injection,
    MarketEvent,
    MarketEventType,
    TraderProfile,
)


def hhmm_to_ts(date: str, hhmm: str) -> int:
    """'2026-10-05', '09:30' -> ns since epoch (naive, treated as venue local time)."""
    return int(pd.Timestamp(f"{date} {hhmm}").value)


@dataclass
class SessionTables:
    order_events: pd.DataFrame
    trades: pd.DataFrame
    traders: pd.DataFrame
    market_events: pd.DataFrame
    instrument_stats: pd.DataFrame
    injections: pd.DataFrame
    cases_history: pd.DataFrame = field(default_factory=pd.DataFrame)


class Session:
    def __init__(self, cfg: SimConfig, seed: int, date: str) -> None:
        self.cfg = cfg
        self.seed = seed
        self.date = date
        self.rng = np.random.default_rng(seed)
        self.open_ts = hhmm_to_ts(date, cfg.session_open)
        self.close_ts = hhmm_to_ts(date, cfg.session_close)
        self.kernel = Kernel(self.open_ts, self.close_ts)
        self.book = OrderBook(cfg.instrument, cfg.tick_size, lambda: self.kernel.now)
        self.instrument = cfg.instrument
        self.traders: dict[str, TraderProfile] = {}
        self.market_events: list[MarketEvent] = []
        self.injections: list[Injection] = []
        self.cases_history: list[dict] = []
        self.fundamental: float = float(cfg.initial_price_ticks)
        self.fv_listeners: list[Callable[[float], None]] = []
        self.event_listeners: list[Callable[[MarketEvent], None]] = []
        self._depth_samples: list[tuple[int, int, int]] = []  # (bid5, ask5, spread_ticks)
        self._mid_samples: list[tuple[int, float]] = []

    # ----- time helpers -----
    @property
    def now(self) -> int:
        return self.kernel.now

    def ts_at(self, hhmm: str) -> int:
        return hhmm_to_ts(self.date, hhmm)

    def ms(self, n: float) -> int:
        return int(n * NS_PER_MS)

    def s(self, n: float) -> int:
        return int(n * NS_PER_S)

    def at(self, ts: int, fn: Callable[..., object], *args: object, **kwargs: object) -> None:
        self.kernel.schedule(ts, fn, *args, **kwargs)

    def after(self, delay_ns: int, fn: Callable[..., object], *args: object, **kwargs: object) -> None:
        self.kernel.schedule_in(delay_ns, fn, *args, **kwargs)

    def uniform_ns(self, lo_ms: float, hi_ms: float) -> int:
        return int(self.rng.uniform(lo_ms, hi_ms) * NS_PER_MS)

    # ----- market state helpers -----
    def depth5_estimate(self) -> int:
        """Running average of one-side top-5 depth from the periodic sampler; a floor keeps
        early-session scenarios sane."""
        if not self._depth_samples:
            return 800
        arr = np.array([(b + a) / 2 for b, a, _ in self._depth_samples[-180:]])
        return max(200, int(arr.mean()))

    def mid_or_fundamental(self) -> float:
        m = self.book.mid_ticks()
        return self.fundamental if m is None else m

    def register_trader(self, profile: TraderProfile) -> TraderProfile:
        self.traders[profile.trader_id] = profile
        return profile

    def add_market_event(
        self, ts: int, type_: MarketEventType, description: str, instrument: str | None = None
    ) -> None:
        ev = MarketEvent(ts=ts, instrument=instrument or self.instrument, type=type_, description=description)
        self.market_events.append(ev)
        self.at(ts, self._fire_event, ev)

    def _fire_event(self, ev: MarketEvent) -> None:
        if ev.type in (MarketEventType.MACRO_PRINT, MarketEventType.NEWS):
            lo, hi = self.cfg.background.event_jump_ticks
            jump = int(self.rng.integers(lo, hi + 1)) * (1 if self.rng.random() < 0.5 else -1)
            self.fundamental += jump
        for fn in list(self.event_listeners):
            fn(ev)

    # ----- periodic processes -----
    def _fundamental_step(self) -> None:
        bg = self.cfg.background
        mu = float(self.cfg.initial_price_ticks)
        self.fundamental += bg.fundamental_theta * (mu - self.fundamental) + self.rng.normal(
            0.0, bg.fundamental_sigma_ticks
        )
        for fn in self.fv_listeners:
            fn(self.fundamental)
        self.after(NS_PER_S, self._fundamental_step)

    def _sample_depth(self) -> None:
        b5, a5 = self.book.depth_top(5)
        bb, ba = self.book.best_bid(), self.book.best_ask()
        spread = (ba - bb) if (bb is not None and ba is not None) else 0
        self._depth_samples.append((b5, a5, spread))
        m = self.book.mid_ticks()
        if m is not None:
            self._mid_samples.append((self.now, m))
        self.after(self.cfg.depth_sample_s * NS_PER_S, self._sample_depth)

    # ----- run -----
    def start_background_processes(self) -> None:
        self.at(self.open_ts, self._fundamental_step)
        self.at(self.open_ts + self.s(1), self._sample_depth)
        self.add_market_event(self.open_ts, MarketEventType.OPEN, "continuous trading opens")
        self.add_market_event(self.close_ts, MarketEventType.CLOSE, "continuous trading closes")

    def run(self) -> None:
        self.kernel.run()

    # ----- export -----
    def tables(self) -> SessionTables:
        oe = pd.DataFrame.from_records(self.book.order_events, columns=list(ORDER_EVENT_COLUMNS))
        tr = pd.DataFrame.from_records(self.book.trades, columns=list(TRADE_COLUMNS))
        for df in (oe, tr):
            df["ts"] = df["ts"].astype("int64")
            df["date"] = self.date
        traders = pd.DataFrame(
            [
                {
                    "trader_id": p.trader_id,
                    "name": p.name,
                    "desk": p.desk,
                    "role": str(p.role),
                    "registered_mm_instruments": json.dumps(p.registered_mm_instruments),
                    "typical_order_size": p.typical_order_size,
                    "typical_daily_otr": p.typical_daily_otr,
                    "risk_limit_events": json.dumps(p.risk_limit_events),
                }
                for p in self.traders.values()
            ]
        )
        me = pd.DataFrame(
            [
                {
                    "ts": e.ts,
                    "instrument": e.instrument,
                    "type": str(e.type),
                    "description": e.description,
                    "date": self.date,
                }
                for e in sorted(self.market_events, key=lambda e: e.ts)
            ]
        )
        depth = np.array(self._depth_samples) if self._depth_samples else np.zeros((1, 3))
        stats = pd.DataFrame(
            [
                {
                    "instrument": self.instrument,
                    "date": self.date,
                    "adv": int(self.book.traded_qty),
                    "n_trades": len(self.book.trades),
                    "avg_spread_ticks": float(depth[:, 2].mean()),
                    "avg_depth_top5": float(((depth[:, 0] + depth[:, 1]) / 2).mean()),
                    "tick_size": self.cfg.tick_size,
                    "open_ticks": self.cfg.initial_price_ticks,
                    "close_ticks": float(self._mid_samples[-1][1]) if self._mid_samples else float("nan"),
                }
            ]
        )
        inj = pd.DataFrame(
            [
                {
                    "scenario_id": i.scenario_id,
                    "trader_id": i.trader_id,
                    "instrument": i.instrument,
                    "date": self.date,
                    "t_start": i.t_start,
                    "t_end": i.t_end,
                    "truth": str(i.truth),
                    "expected_disposition": str(i.expected_disposition),
                    "key_discriminators": json.dumps(i.key_discriminators),
                    "expected_tools": json.dumps(i.expected_tools),
                    "notes": i.notes,
                }
                for i in self.injections
            ]
        )
        hist = pd.DataFrame(self.cases_history)
        return SessionTables(oe, tr, traders, me, stats, inj, hist)

"""Simulation configuration. Every number here is a modelling choice, not a market fact."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BackgroundConfig(BaseModel):
    # fundamental: Ornstein-Uhlenbeck in ticks, stepped once per second
    fundamental_sigma_ticks: float = 0.18
    fundamental_theta: float = 0.002
    event_jump_ticks: tuple[int, int] = (3, 8)

    # market makers
    n_market_makers: int = 2
    mm_quote_size: tuple[int, int] = (250, 400)
    mm_half_spread_ticks: int = 2
    mm_requote_threshold_ticks: int = 1
    mm_imbalance_skew_ticks: int = 2  # max skew from top-5 imbalance
    mm_imbalance_dead_zone: float = 0.30  # |imbalance| below this does not move the quotes
    mm_event_pull_ms: tuple[int, int] = (300, 700)
    mm_event_widen_ticks: int = 3
    mm_event_widen_s: int = 30

    # noise traders
    noise_rate_per_s: float = 0.6
    noise_size: tuple[int, int] = (40, 220)
    noise_market_order_prob: float = 0.25
    noise_offset_ticks: tuple[int, int] = (0, 4)
    noise_lifetime_mean_s: float = 25.0
    noise_event_cancel_prob: float = 0.6

    # value traders
    n_value_traders: int = 3
    value_check_s: float = 2.0
    value_threshold_ticks: int = 2
    value_size: tuple[int, int] = (100, 300)

    # agency client flow
    client_rate_per_min: float = 1.5
    client_size: tuple[int, int] = (200, 1500)

    # background algo parents (two-sided agency algo desk)
    algo_parents_per_session: int = 4
    algo_parent_size: tuple[int, int] = (3000, 8000)
    algo_child_size: tuple[int, int] = (150, 300)
    algo_duration_min: tuple[int, int] = (20, 60)

    # market events
    macro_prints: tuple[str, ...] = ("10:30", "14:30")
    news_prob: float = 0.5
    news_window: tuple[str, str] = ("09:45", "16:30")


class SimConfig(BaseModel):
    instrument: str = "SYN.A"
    tick_size: float = 0.01
    initial_price_ticks: int = 10_000  # 100.00
    session_open: str = "09:00"
    session_close: str = "17:30"
    depth_sample_s: int = 10
    background: BackgroundConfig = Field(default_factory=BackgroundConfig)

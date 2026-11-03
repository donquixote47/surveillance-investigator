"""Background participants. None of them manipulates; every alert they cause is a false positive."""

from __future__ import annotations

from .session import Session
from .types import (
    NS_PER_MS,
    NS_PER_S,
    MarketEvent,
    MarketEventType,
    Order,
    OrderType,
    Role,
    Side,
    TraderProfile,
)


def _rint(session: Session, lo_hi: tuple[int, int]) -> int:
    lo, hi = lo_hi
    return int(session.rng.integers(lo, hi + 1))


class MarketMaker:
    """Two-sided quotes around a noisy fair-value estimate, skewed by top-of-book imbalance.
    Re-quotes (cancel/replace) whenever the target mid moves by the threshold, replaces a quote
    that was filled, and pulls both quotes on a market event before re-quoting wider."""

    def __init__(self, session: Session, trader_id: str, desk: str = "ETF-MM") -> None:
        self.s = session
        bg = session.cfg.background
        self.id = trader_id
        self.size = _rint(session, bg.mm_quote_size)
        self.half = bg.mm_half_spread_ticks
        self.threshold = bg.mm_requote_threshold_ticks
        self.skew_ticks = bg.mm_imbalance_skew_ticks
        self.quotes: dict[Side, str | None] = {Side.BUY: None, Side.SELL: None}
        self.quote_mid: int | None = None
        self.widen_until = 0
        self.bias = float(session.rng.normal(0.0, 0.3))
        session.register_trader(
            TraderProfile(
                trader_id=trader_id,
                name=f"Desk {trader_id}",
                desk=desk,
                role=Role.MARKET_MAKER,
                registered_mm_instruments=[session.instrument],
                typical_order_size=self.size,
                typical_daily_otr=0.0,  # filled in from the simulated tape at build time
            )
        )
        session.fv_listeners.append(self.on_fair_value)
        session.event_listeners.append(self.on_event)
        session.book.add_fill_listener(trader_id, self.on_fill)
        session.at(session.open_ts + session.ms(50), self.requote, None)

    def target_mid(self, fv: float) -> int:
        """Fair value plus a skew for a *strong* top-of-book imbalance. The dead zone keeps ordinary
        noise from causing a re-quote every second; a spoof-sized imbalance still moves the quotes."""
        b5, a5 = self.s.book.depth_top(8)
        imb = 0.0 if (b5 + a5) == 0 else (b5 - a5) / (b5 + a5)
        skew = imb * self.skew_ticks if abs(imb) >= self.s.cfg.background.mm_imbalance_dead_zone else 0.0
        return round(fv + self.bias + skew)

    def on_fair_value(self, fv: float) -> None:
        tm = self.target_mid(fv)
        missing = any(q is None for q in self.quotes.values())
        if self.quote_mid is None or abs(tm - self.quote_mid) >= self.threshold or missing:
            self.requote(tm)

    def requote(self, tm: int | None) -> None:
        if tm is None:
            tm = self.target_mid(self.s.fundamental)
        for side in (Side.BUY, Side.SELL):
            oid = self.quotes[side]
            if oid is not None and oid in self.s.book.open:
                self.s.book.cancel(oid)
            self.quotes[side] = None
        self.quote_mid = tm
        self.s.after(self.s.uniform_ns(3, 25), self._place_quotes, tm)

    def _place_quotes(self, tm: int | None) -> None:
        if tm is None or self.quote_mid != tm:
            return  # quotes pulled for an event, or superseded by a newer requote
        half = self.half + (self.s.cfg.background.mm_event_widen_ticks if self.s.now < self.widen_until else 0)
        for side, px in ((Side.BUY, tm - half), (Side.SELL, tm + half)):
            if self.quotes[side] is None:
                o = self.s.book.submit(self.id, side, self.size, px)
                self.quotes[side] = o.order_id if o.remaining > 0 else None

    def on_fill(self, order: Order, qty: int, price: int, is_aggr: bool) -> None:
        if order.remaining == 0:
            for side, oid in self.quotes.items():
                if oid == order.order_id:
                    self.quotes[side] = None
            self.s.after(self.s.uniform_ns(50, 200), self._place_quotes, self.quote_mid)

    def on_event(self, ev: MarketEvent) -> None:
        if ev.type not in (MarketEventType.MACRO_PRINT, MarketEventType.NEWS):
            return
        bg = self.s.cfg.background
        self.widen_until = self.s.now + bg.mm_event_widen_s * NS_PER_S
        for side in (Side.BUY, Side.SELL):
            oid = self.quotes[side]
            if oid is not None and oid in self.s.book.open:
                self.s.after(self.s.uniform_ns(5, 120), self.s.book.cancel, oid)
            self.quotes[side] = None
        self.quote_mid = None
        self.s.after(self.s.uniform_ns(*bg.mm_event_pull_ms), self.requote, None)


class NoisePopulation:
    """Poisson arrivals of small passive and marketable orders from a pool of noise traders."""

    def __init__(self, session: Session, n_traders: int = 12) -> None:
        self.s = session
        self.bg = session.cfg.background
        self.ids = [f"T-NOISE-{i:02d}" for i in range(1, n_traders + 1)]
        for tid in self.ids:
            session.register_trader(TraderProfile(tid, f"Retail flow {tid[-2:]}", "RETAIL", Role.CLIENT, [], 120, 0.0))
        self.open_orders: dict[
            str, None
        ] = {}  # insertion-ordered; a set would make RNG consumption depend on hash seeds
        session.event_listeners.append(self.on_event)
        session.at(session.open_ts + session.ms(200), self.arrive)

    def arrive(self) -> None:
        rng = self.s.rng
        tid = self.ids[int(rng.integers(len(self.ids)))]
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        size = _rint(self.s, self.bg.noise_size)
        book = self.s.book
        if (
            rng.random() < self.bg.noise_market_order_prob
            and book.best_bid() is not None
            and book.best_ask() is not None
        ):
            book.submit(tid, side, size, None, OrderType.MARKET)
        else:
            off = _rint(self.s, self.bg.noise_offset_ticks)
            ref = book.best_bid() if side is Side.BUY else book.best_ask()
            if ref is None:
                ref = round(self.s.fundamental) + (-2 if side is Side.BUY else 2)
            px = ref - off if side is Side.BUY else ref + off
            o = book.submit(tid, side, size, px)
            if o.remaining > 0:
                self.open_orders[o.order_id] = None
                life = rng.exponential(self.bg.noise_lifetime_mean_s)
                self.s.after(int(life * NS_PER_S), self._expire, o.order_id)
        gap = rng.exponential(1.0 / self.bg.noise_rate_per_s)
        self.s.after(int(gap * NS_PER_S), self.arrive)

    def _expire(self, oid: str) -> None:
        self.open_orders.pop(oid, None)
        if oid in self.s.book.open:
            self.s.book.cancel(oid)

    def on_event(self, ev: MarketEvent) -> None:
        if ev.type not in (MarketEventType.MACRO_PRINT, MarketEventType.NEWS):
            return
        for oid in list(self.open_orders):
            if oid in self.s.book.open and self.s.rng.random() < self.bg.noise_event_cancel_prob:
                self.s.after(self.s.uniform_ns(0, 200), self._expire, oid)


class ValueTrader:
    """Trades toward the fundamental when the mid has drifted away from it."""

    def __init__(self, session: Session, trader_id: str) -> None:
        self.s = session
        self.bg = session.cfg.background
        self.id = trader_id
        session.register_trader(
            TraderProfile(trader_id, f"Fund {trader_id[-2:]}", "ASSET-MGR", Role.CLIENT, [], 200, 0.0)
        )
        session.at(session.open_ts + session.s(5) + session.uniform_ns(0, 2000), self.check)

    def check(self) -> None:
        book = self.s.book
        m = book.mid_ticks()
        if m is not None:
            dev = self.s.fundamental - m
            if (
                abs(dev) >= self.bg.value_threshold_ticks
                and book.best_bid() is not None
                and book.best_ask() is not None
            ):
                side = Side.BUY if dev > 0 else Side.SELL
                book.submit(self.id, side, _rint(self.s, self.bg.value_size), None, OrderType.MARKET)
        self.s.after(int(self.bg.value_check_s * NS_PER_S) + self.s.uniform_ns(0, 500), self.check)


class AgencyDesk:
    """Routes client orders: mostly passive limits at the touch, some marketable, with a parent id
    per client order and a time-out cancel of the unfilled remainder."""

    def __init__(self, session: Session, trader_id: str = "T-AGY-01") -> None:
        self.s = session
        self.bg = session.cfg.background
        self.id = trader_id
        self.client_seq = 0
        session.register_trader(TraderProfile(trader_id, "Agency execution", "AGENCY", Role.AGENCY, [], 600, 0.0))
        session.at(session.open_ts + session.s(30), self.arrive)

    def arrive(self) -> None:
        rng = self.s.rng
        book = self.s.book
        self.client_seq += 1
        parent = f"C-{self.s.date[-5:].replace('-', '')}-{self.client_seq:04d}"
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        size = _rint(self.s, self.bg.client_size)
        if rng.random() < 0.3 and book.best_bid() is not None and book.best_ask() is not None:
            book.submit(self.id, side, size, None, OrderType.MARKET, parent_order_id=parent)
        else:
            ref = book.best_bid() if side is Side.BUY else book.best_ask()
            if ref is not None:
                o = book.submit(self.id, side, size, ref, parent_order_id=parent)
                if o.remaining > 0:
                    self.s.after(self.s.s(rng.uniform(120, 600)), self._timeout, o.order_id)
        gap = rng.exponential(60.0 / self.bg.client_rate_per_min)
        self.s.after(int(gap * NS_PER_S), self.arrive)

    def _timeout(self, oid: str) -> None:
        if oid in self.s.book.open:
            self.s.book.cancel(oid)


class AlgoDesk:
    """Two-sided agency algo desk running TWAP parents whose child orders are pegged to the same-side
    touch and re-pegged (cancel/replace) when it moves. Looks like constant cancelling; it is not."""

    def __init__(self, session: Session, trader_id: str = "T-ALGO-01") -> None:
        self.s = session
        self.bg = session.cfg.background
        self.id = trader_id
        self.parent_seq = 0
        self.active: dict[str, dict] = {}  # child order_id -> parent state
        session.register_trader(TraderProfile(trader_id, "Algo execution", "ALGO", Role.ALGO, [], 220, 0.0))
        session.book.add_fill_listener(trader_id, self.on_fill)
        session.fv_listeners.append(self.on_tick)
        n = self.bg.algo_parents_per_session
        span = session.close_ts - session.open_ts - session.s(3600)
        for i in range(n):
            t0 = session.open_ts + session.s(600) + int(span * (i + session.rng.random() * 0.8) / n)
            session.at(t0, self.start_parent)

    def start_parent(self) -> None:
        self.parent_seq += 1
        side = Side.BUY if self.parent_seq % 2 == 1 else Side.SELL
        parent = {
            "id": f"P-{self.s.date[-5:].replace('-', '')}-{self.parent_seq:03d}",
            "side": side,
            "remaining": _rint(self.s, self.bg.algo_parent_size),
            "child_size": _rint(self.s, self.bg.algo_child_size),
            "interval_ns": 0,
            "child": None,
        }
        duration = _rint(self.s, self.bg.algo_duration_min) * 60
        n_children = max(1, parent["remaining"] // parent["child_size"])
        parent["interval_ns"] = int(duration * NS_PER_S / n_children)
        self._next_child(parent)

    def _next_child(self, parent: dict) -> None:
        if parent["remaining"] <= 0:
            return
        if parent["child"] is not None and parent["child"] in self.s.book.open:
            # previous child still working; re-peg it and try again later
            self.s.after(parent["interval_ns"], self._next_child, parent)
            return
        side = parent["side"]
        ref = self.s.book.best_bid() if side is Side.BUY else self.s.book.best_ask()
        if ref is None:
            self.s.after(parent["interval_ns"], self._next_child, parent)
            return
        qty = min(parent["child_size"], parent["remaining"])
        o = self.s.book.submit(self.id, side, qty, ref, OrderType.PEGGED, parent_order_id=parent["id"])
        if o.remaining > 0:
            parent["child"] = o.order_id
            self.active[o.order_id] = parent
        else:
            parent["remaining"] -= qty
        self.s.after(parent["interval_ns"], self._next_child, parent)

    def on_tick(self, fv: float) -> None:
        # re-peg working children to the current same-side touch
        for oid, parent in list(self.active.items()):
            o = self.s.book.open.get(oid)
            if o is None:
                self.active.pop(oid, None)
                continue
            ref = self.s.book.best_bid() if o.side is Side.BUY else self.s.book.best_ask()
            if ref is not None and ref != o.price_ticks:
                remaining = o.remaining
                self.s.book.cancel(oid)
                self.active.pop(oid, None)
                self.s.after(self.s.uniform_ns(2, 15), self._replace_child, parent, o.side, remaining)

    def _replace_child(self, parent: dict, side: Side, qty: int) -> None:
        ref = self.s.book.best_bid() if side is Side.BUY else self.s.book.best_ask()
        if ref is None:
            return
        o = self.s.book.submit(self.id, side, qty, ref, OrderType.PEGGED, parent_order_id=parent["id"])
        if o.remaining > 0:
            parent["child"] = o.order_id
            self.active[o.order_id] = parent
        else:
            parent["remaining"] -= qty
            parent["child"] = None

    def on_fill(self, order: Order, qty: int, price: int, is_aggr: bool) -> None:
        parent = self.active.get(order.order_id)
        if parent is None:
            return
        parent["remaining"] -= qty
        if order.remaining == 0:
            self.active.pop(order.order_id, None)
            parent["child"] = None


def build_background(session: Session) -> None:
    bg = session.cfg.background
    for i in range(1, bg.n_market_makers + 1):
        MarketMaker(session, f"T-MM-{i:02d}")
    NoisePopulation(session)
    for i in range(1, bg.n_value_traders + 1):
        ValueTrader(session, f"T-VAL-{i:02d}")
    AgencyDesk(session)
    AlgoDesk(session)
    # scheduled market events
    for hhmm in bg.macro_prints:
        jitter = int(session.rng.integers(-90, 90)) * NS_PER_S
        session.add_market_event(
            session.ts_at(hhmm) + jitter, MarketEventType.MACRO_PRINT, f"scheduled macro print {hhmm}", "*"
        )
    if session.rng.random() < bg.news_prob:
        lo, hi = (session.ts_at(x) for x in bg.news_window)
        t = int(session.rng.integers(lo, hi))
        session.add_market_event(t, MarketEventType.NEWS, "unscheduled issuer news", session.instrument)


__all__ = [
    "NS_PER_MS",
    "AgencyDesk",
    "AlgoDesk",
    "MarketMaker",
    "NoisePopulation",
    "ValueTrader",
    "build_background",
]

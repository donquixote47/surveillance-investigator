"""Scenario catalogue: scripted sequences by one trader, each with its ground-truth label.

Every scenario is written so that the deliberately noisy detector in `src/detector/rule.py` fires on it.
TRUE_ABUSE scenarios are spoofing or layering; FALSE_POSITIVE scenarios are the legitimate behaviours an
analyst must tell apart (domain primer, table 2.3). Third-party actions inside a script (a client hitting a
quote, an adverse price move) are part of the scenario's world, not of the trader's conduct.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .session import Session
from .types import Disposition, Injection, MarketEventType, OrderType, Role, Side, TraderProfile, Truth

CORE_TOOLS = [
    "get_alert",
    "get_order_events",
    "compute_discriminators",
    "get_trader_profile",
    "get_market_events",
]
CLOSE_TOOLS = [*CORE_TOOLS, "get_trader_alert_history"]  # policy 04: history before a CLOSE_FP

# The catalogue is versioned because the mix is SAMPLED from it: adding a scenario changes which scenario every
# later draw picks, so a dataset built before the addition could no longer be rebuilt from its seed. A scenario
# carries the catalogue version it first appears in (`since`), a build names the catalogue it samples from, and
# the manifest records it. seed7 and seed8 are catalogue 1.
#   1  the fifteen scenarios of the first build (2026-11-02)
#   2  + S-SPOOF-6, a market maker REGISTERED on the instrument who spoofs (2026-11-16)
CATALOGUE_LATEST = 2


@dataclass
class ScenarioSpec:
    id: str
    truth: Truth
    expected_disposition: Disposition
    role: Role
    desk: str
    key_discriminators: list[str]
    expected_tools: list[str]
    notes: str
    weight: float
    run: Callable[[Session, str, int], int]  # (session, trader_id, t0) -> t_end
    registered_here: bool = False
    profile_size: int = 500
    profile_otr: float = 4.0
    extra: dict = field(default_factory=dict)
    since: int = 1  # the catalogue version this scenario first appears in


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------


INSTITUTIONAL = ("T-INST-01", "T-INST-02", "T-INST-03")


def _counterparty(session: Session) -> str:
    """A client who trades only when a scenario needs a counterparty and never rests orders, so the
    scripted market order cannot be stopped by self-trade prevention against its own resting order."""
    for i, tid in enumerate(INSTITUTIONAL, start=1):
        if tid not in session.traders:
            session.register_trader(
                TraderProfile(tid, f"Institution {i:02d}", "INSTITUTIONAL", Role.CLIENT, [], 1500, 1.5)
            )
    return INSTITUTIONAL[int(session.rng.integers(len(INSTITUTIONAL)))]


def _touch(session: Session, side: Side) -> int:
    """Best price on `side`'s own side of the book (bid for BUY, ask for SELL), with a fallback."""
    book = session.book
    ref = book.best_bid() if side is Side.BUY else book.best_ask()
    if ref is None:
        ref = round(session.fundamental) + (-2 if side is Side.BUY else 2)
    return ref


def _away(session: Session, side: Side, ticks: int) -> int:
    """Price `ticks` away from the touch on the passive side (below the bid for BUY, above the ask for SELL)."""
    ref = _touch(session, side)
    return ref - ticks if side is Side.BUY else ref + ticks


def _improve(session: Session, side: Side, ticks: int) -> int:
    """Price `ticks` better than the touch on the trader's own side, capped so it never crosses the spread."""
    book = session.book
    ref = _touch(session, side)
    if side is Side.BUY:
        cap = (book.best_ask() - 1) if book.best_ask() is not None else ref + ticks
        return min(ref + ticks, cap)
    cap = (book.best_bid() + 1) if book.best_bid() is not None else ref - ticks
    return max(ref - ticks, cap)


def _place_improving(
    session: Session, trader_id: str, side: Side, qty: int, ticks: int, store: list[str], **kw
) -> None:
    o = session.book.submit(trader_id, side, qty, _improve(session, side, ticks), **kw)
    if o.remaining > 0:
        store.append(o.order_id)


def _market(session: Session, trader_id: str, side: Side, qty: int, parent: str | None = None) -> None:
    book = session.book
    if book.best_bid() is None or book.best_ask() is None:
        return
    book.submit(trader_id, side, qty, None, OrderType.MARKET, parent_order_id=parent)


def _place(session: Session, trader_id: str, side: Side, qty: int, away_ticks: int, store: list[str], **kw) -> None:
    px = _away(session, side, away_ticks)
    o = session.book.submit(trader_id, side, qty, px, **kw)
    if o.remaining > 0:
        store.append(o.order_id)


def _cancel_many(session: Session, order_ids: list[str]) -> None:
    for oid in order_ids:
        session.book.cancel(oid)


def _cancel_all(session: Session, trader_id: str) -> None:
    session.book.cancel_all(trader_id)


def _profile(session: Session, spec: ScenarioSpec, trader_id: str) -> TraderProfile:
    return session.register_trader(
        TraderProfile(
            trader_id=trader_id,
            name=f"Trader {trader_id[-4:]}",
            desk=spec.desk,
            role=spec.role,
            registered_mm_instruments=[session.instrument]
            if spec.registered_here
            else list(spec.extra.get("mm_elsewhere", [])),
            typical_order_size=spec.profile_size,
            typical_daily_otr=spec.profile_otr,
        )
    )


def _spoof_cycle(
    session: Session,
    tid: str,
    t0: int,
    spoof_side: Side,
    mult: float,
    away: int,
    wait_s: float,
    cancel_ms: tuple[float, float],
    levels: int = 1,
    partial_fill_frac: float = 0.0,
) -> int:
    """Place `levels` resting orders on `spoof_side` totalling mult x depth, trade the other side after
    wait_s, cancel the resting orders cancel_ms later. Returns the time of the last cancel."""
    d = session.depth5_estimate()
    total = int(mult * d)
    per = max(1, total // levels)
    ids: list[str] = []
    for k in range(levels):
        session.at(t0 + session.ms(k * 15), _place, session, tid, spoof_side, per, away + k, ids)
    t_fill = t0 + session.s(wait_s)
    # the genuine trade is sized like a normal participant's, not like the spoof: 10-20% of the spoof,
    # capped at 0.5 x depth so it does not sweep the book
    genuine = min(int(total * session.rng.uniform(0.10, 0.20)), int(0.5 * d))
    session.at(t_fill, _market, session, tid, spoof_side.opposite, genuine)
    lo, hi = cancel_ms
    if partial_fill_frac > 0:
        # "caught in the book": a late buyer sweeps into the resting order 100-250 ms after the spoofer traded,
        # before he can pull it; the cancel then follows the hit
        cp = _counterparty(session)
        t_hit = t_fill + session.uniform_ns(100, 250)
        session.at(t_hit, _market, session, cp, spoof_side.opposite, int(total * partial_fill_frac))
        lo = max(lo, 300)
        hi = max(hi, lo + 100)
    t_cancel = t_fill + session.uniform_ns(lo, hi)
    if levels == 1:
        session.at(t_cancel, _cancel_many, session, ids)
        return t_cancel
    t_last = t_cancel
    for k in range(levels):
        t_k = t_cancel + session.uniform_ns(0, 900)
        t_last = max(t_last, t_k)
        session.at(t_k, lambda s, i, k=k: _cancel_many(s, i[k : k + 1]) if k < len(i) else None, session, ids)
    return t_last


def _rand_side(session: Session) -> Side:
    return Side.SELL if session.rng.random() < 0.5 else Side.BUY


# ----------------------------------------------------------------------------------------------
# TRUE_ABUSE
# ----------------------------------------------------------------------------------------------


def s_spoof_1(session: Session, tid: str, t0: int) -> int:
    rng = session.rng
    return _spoof_cycle(
        session,
        tid,
        t0,
        _rand_side(session),
        float(rng.uniform(8, 15)),
        int(rng.integers(2, 5)),
        float(rng.uniform(1.5, 3.5)),
        (100, 500),
    )


def s_spoof_2(session: Session, tid: str, t0: int) -> int:
    rng = session.rng
    n = int(rng.integers(3, 7))
    side = _rand_side(session)
    t = t0
    t_end = t0
    for _ in range(n):
        t_end = _spoof_cycle(
            session,
            tid,
            t,
            side,
            float(rng.uniform(8, 12)),
            int(rng.integers(2, 5)),
            float(rng.uniform(1.0, 2.5)),
            (100, 500),
        )
        t = t_end + session.s(float(rng.uniform(60, 150)))
    return t_end


def s_layer_1(session: Session, tid: str, t0: int) -> int:
    rng = session.rng
    return _spoof_cycle(
        session, tid, t0, _rand_side(session), 10.0, 1, float(rng.uniform(1.0, 3.0)), (50, 100), levels=5
    )


def s_spoof_5(session: Session, tid: str, t0: int) -> int:
    rng = session.rng
    return _spoof_cycle(
        session,
        tid,
        t0,
        _rand_side(session),
        float(rng.uniform(8, 12)),
        2,
        float(rng.uniform(2.0, 3.0)),
        (300, 800),
        partial_fill_frac=float(rng.uniform(0.15, 0.30)),
    )


def _add_history(session: Session, tid: str, n: int, note: str, scenario: str = "SPOOFING") -> None:
    import pandas as pd

    base = pd.Timestamp(session.date)
    for k in range(n):
        when = base - pd.Timedelta(days=int(7 + k * 9))
        session.cases_history.append(
            {
                "alert_id": f"H-{tid}-{k + 1:02d}",
                "trader_id": tid,
                "instrument": session.instrument,
                "date": when.strftime("%Y-%m-%d"),
                "scenario": scenario,
                "proposed_disposition": "CLOSE_FP",
                "recorded_disposition": "CLOSE_FP",
                "recorded_by": "L1-analyst-02",
                "analyst_note": note,
                "override": False,
            }
        )


def s_spoof_4(session: Session, tid: str, t0: int) -> int:
    _add_history(
        session,
        tid,
        6,
        "pegged execution algo on this name; cancels symmetric; parent order explains children",
    )
    rng = session.rng
    return _spoof_cycle(
        session,
        tid,
        t0,
        _rand_side(session),
        float(rng.uniform(8, 12)),
        int(rng.integers(2, 4)),
        float(rng.uniform(1.5, 3.0)),
        (100, 400),
    )


def s_spoof_6(session: Session, tid: str, t0: int) -> int:
    """A market maker REGISTERED on this instrument who spoofs. He quotes both sides the way F-MM-1 does for
    35-50 s, pulls his quotes, and one to two seconds later runs one spoof cycle: a single large order away from the
    touch on one side, a market order the other way once the book has skewed, the cancel within half a second.

    Why it exists (review 2026-11-16): in seed7 all 82 alerts on a market maker registered on the instrument are
    false positives, so nothing tested the cheapest wrong reading of the profile, "registered, therefore close".
    The detector's 60 s window holds the two-sided quoting as well as the spoof, so the trader's cancels in the
    window are mostly symmetric quote cancels and his profile, his desk and his typical size are a market maker's;
    only the one large one-sided order, the trade that followed it and the cancel say otherwise."""
    rng = session.rng
    d = session.depth5_estimate()
    size = int(1.2 * d)
    session.traders[tid].typical_order_size = size  # he IS a market maker: his typical size is what he quotes
    quotes: dict[Side, list[str]] = {Side.BUY: [], Side.SELL: []}

    def requote() -> None:
        for side in (Side.BUY, Side.SELL):
            _cancel_many(session, quotes[side])
            quotes[side].clear()
        for side in (Side.BUY, Side.SELL):
            session.after(session.uniform_ns(3, 20), _place_improving, session, tid, side, size, 1, quotes[side])

    quote_s = float(rng.uniform(35, 50))
    t = t0
    end_quotes = t0 + session.s(quote_s)
    while t < end_quotes:
        session.at(t, requote)
        t += session.s(float(rng.uniform(1.5, 3.0)))
    # a client trades against his quotes, as in F-MM-1: the window holds an ordinary market-making execution too
    session.at(
        t0 + session.s(quote_s * float(rng.uniform(0.3, 0.6))),
        lambda: _market(session, _counterparty(session), _rand_side(session), int(0.6 * d)),
    )
    t_pull = end_quotes + session.ms(200)
    session.at(t_pull, _cancel_all, session, tid)
    t_spoof = t_pull + session.s(float(rng.uniform(1.0, 2.0)))
    return _spoof_cycle(
        session,
        tid,
        t_spoof,
        _rand_side(session),
        float(rng.uniform(8, 12)),
        int(rng.integers(2, 4)),
        float(rng.uniform(1.5, 3.0)),
        (100, 500),
    )


# ----------------------------------------------------------------------------------------------
# FALSE_POSITIVE
# ----------------------------------------------------------------------------------------------


def f_mm_1(session: Session, tid: str, t0: int) -> int:
    """Registered market maker re-quoting both sides for ~90 s; a client hits one quote."""
    d = session.depth5_estimate()
    size = int(1.2 * d)
    session.traders[tid].typical_order_size = size  # a market maker's typical size is what he quotes
    quotes: dict[Side, list[str]] = {Side.BUY: [], Side.SELL: []}

    def requote() -> None:
        for side in (Side.BUY, Side.SELL):
            _cancel_many(session, quotes[side])
            quotes[side].clear()
        for side in (Side.BUY, Side.SELL):
            # quote one tick inside the touch (never crossing): a competitive market maker is first in queue
            session.after(session.uniform_ns(3, 20), _place_improving, session, tid, side, size, 1, quotes[side])

    t = t0
    end = t0 + session.s(90)
    while t < end:
        session.at(t, requote)
        t += session.s(float(session.rng.uniform(1.5, 3.0)))
    for when in (30, 45, 70):
        session.at(
            t0 + session.s(when),
            lambda: _market(session, _counterparty(session), _rand_side(session), int(0.6 * d)),
        )
    session.at(end + session.s(1), _cancel_all, session, tid)
    return end + session.s(1)


def f_algo_1(session: Session, tid: str, t0: int) -> int:
    """Agency algo desk working a buy parent and a sell parent at once; children pegged, re-pegged every few seconds."""
    d = session.depth5_estimate()
    child = int(1.0 * d)
    session.traders[tid].typical_order_size = child  # the desk's typical size is its child size
    parents = {Side.BUY: f"P-{tid}-B", Side.SELL: f"P-{tid}-S"}
    children: dict[Side, list[str]] = {Side.BUY: [], Side.SELL: []}

    def repeg(side: Side) -> None:
        _cancel_many(session, children[side])
        children[side].clear()
        session.after(
            session.uniform_ns(2, 15),
            _place,
            session,
            tid,
            side,
            child,
            0,
            children[side],
            order_type=OrderType.PEGGED,
            parent_order_id=parents[side],
        )

    t = t0
    end = t0 + session.s(120)
    while t < end:
        for side in (Side.BUY, Side.SELL):
            session.at(t + session.uniform_ns(0, 300), repeg, side)
        t += session.s(float(session.rng.uniform(2.0, 4.0)))
    for k, when in enumerate((30, 70, 100)):
        side = Side.BUY if k % 2 == 0 else Side.SELL
        session.at(t0 + session.s(when), lambda sd=side: _market(session, _counterparty(session), sd, int(0.5 * d)))
    session.at(end + session.s(1), _cancel_all, session, tid)
    return end + session.s(1)


def f_risk_1(session: Session, tid: str, t0: int) -> int:
    """Prop trader working large resting bids and a small ask; the firm's risk system pulls everything."""
    d = session.depth5_estimate()
    ids: list[str] = []
    for k in range(3):
        session.at(t0 + session.s(5 * k), _place, session, tid, Side.BUY, int(2.0 * d), 1 + k, ids)
    session.at(t0 + session.s(16), _place_improving, session, tid, Side.SELL, int(0.3 * d), 1, ids)
    t_hit = t0 + session.s(20)
    session.at(t_hit, lambda: _market(session, _counterparty(session), Side.BUY, int(1.0 * d)))
    t_kill = t_hit + session.s(1)
    session.at(t_kill, _cancel_all, session, tid)
    session.traders[tid].risk_limit_events.append(
        {
            "ts": t_kill,
            "instrument": "*",
            "reason": "intraday loss limit breached; automated kill switch cancelled all resting orders",
        }
    )
    return t_kill


def f_news_1(session: Session, tid: str, t0: int) -> int:
    """Large resting bids, a small hedge sale, then issuer news: everyone cancels within 200 ms, so does our trader."""
    d = session.depth5_estimate()
    ids: list[str] = []
    for k in range(2):
        session.at(t0 + session.s(3 * k), _place, session, tid, Side.BUY, int(2.8 * d), 1 + k, ids)
    t_news = t0 + session.s(30)
    hedge: list[str] = []
    session.at(t_news - session.s(4), _place_improving, session, tid, Side.SELL, int(0.2 * d), 1, hedge)
    session.at(t_news - session.s(2.5), lambda: _market(session, _counterparty(session), Side.BUY, int(1.0 * d)))
    session.add_market_event(
        t_news, MarketEventType.NEWS, "issuer announces unscheduled trading update", session.instrument
    )
    t_cancel = t_news + session.uniform_ns(50, 200)
    session.at(t_cancel, _cancel_many, session, ids)
    return t_cancel


def f_ice_1(session: Session, tid: str, t0: int) -> int:
    """Agency iceberg buy for one client (large, small visible tip), a second client's small sale, then the first
    client pulls."""
    d = session.depth5_estimate()
    ids: list[str] = []
    session.at(
        t0,
        _place_improving,
        session,
        tid,
        Side.BUY,
        int(8 * d),
        1,
        ids,
        order_type=OrderType.ICEBERG,
        parent_order_id=f"C-{tid}-A",
        peak=int(0.3 * d),
    )
    for k in range(3):
        session.at(
            t0 + session.s(4 + 6 * k),
            lambda: _market(session, _counterparty(session), Side.SELL, int(1.0 * d)),
        )
    sale: list[str] = []
    session.at(
        t0 + session.s(23),
        _place_improving,
        session,
        tid,
        Side.SELL,
        int(0.2 * d),
        1,
        sale,
        parent_order_id=f"C-{tid}-B",
    )
    session.at(t0 + session.s(25), lambda: _market(session, _counterparty(session), Side.BUY, int(1.0 * d)))
    t_cancel = t0 + session.s(27)
    session.at(t_cancel, _cancel_many, session, ids)
    return t_cancel


def f_partial_1(session: Session, tid: str, t0: int) -> int:
    """Large buy at the touch, partially executed; small hedge sale; size reduced after the partial; the rest
    completes."""
    d = session.depth5_estimate()
    q = int(5.0 * d)
    ids: list[str] = []
    session.at(t0, _place_improving, session, tid, Side.BUY, q, 1, ids)
    for k in range(2):
        session.at(
            t0 + session.s(3 + 4 * k),
            lambda: _market(session, _counterparty(session), Side.SELL, int(0.6 * d)),
        )
    hedge: list[str] = []
    session.at(t0 + session.s(13), _place_improving, session, tid, Side.SELL, int(0.15 * d), 1, hedge)
    session.at(t0 + session.s(15), lambda: _market(session, _counterparty(session), Side.BUY, int(2.2 * d)))

    def reduce() -> None:
        # cut the working order down to a small residual (the trader has most of what he wanted)
        if ids and ids[0] in session.book.open:
            o = session.book.open[ids[0]]
            residual = max(1, int(0.08 * q))
            if o.remaining > residual:
                session.book.modify(ids[0], new_remaining=residual)

    session.at(t0 + session.s(17), reduce)
    session.at(t0 + session.s(40), lambda: _market(session, _counterparty(session), Side.SELL, int(0.08 * q) + 50))
    return t0 + session.s(41)


def f_fat_1(session: Session, tid: str, t0: int) -> int:
    """Ten times the intended size, cancelled within two seconds, re-entered at the right size. No opposite fill."""
    d = session.depth5_estimate()
    intended = int(0.9 * d)
    ids: list[str] = []
    session.at(t0, _place, session, tid, Side.BUY, intended * 10, 1, ids)
    t_cancel = t0 + session.uniform_ns(800, 2000)
    session.at(t_cancel, _cancel_many, session, ids)
    fixed: list[str] = []
    session.at(t_cancel + session.ms(400), _place, session, tid, Side.BUY, intended, 1, fixed)
    session.at(t_cancel + session.s(300), _cancel_many, session, fixed)
    return t_cancel + session.ms(400)


def f_stop_1(session: Session, tid: str, t0: int) -> int:
    """Momentum trader buys, adds large resting bids, the market turns, he pulls the bids and sells at a loss."""
    d = session.depth5_estimate()
    session.at(t0, _market, session, tid, Side.BUY, int(0.5 * d))
    ids: list[str] = []
    # bids 5-7 ticks behind the touch: far enough that after the turn they are still below the best bid, so
    # his stop-out sale hits other people's bids rather than being blocked by self-trade prevention
    for k in range(3):
        session.at(t0 + session.s(2 + 2 * k), _place, session, tid, Side.BUY, int(1.8 * d), 5 + k, ids)

    def market_turns() -> None:
        # the turn has to outweigh the upward skew his own resting bids put on the market makers' quotes
        session.fundamental -= 3.0

    session.at(t0 + session.s(10), market_turns)

    def stop_out() -> None:
        # if the market gapped down through his own bids, the venue's self-trade prevention would block the
        # sale; a real trader pulls the bid that sits at the touch first, then sells
        book = session.book
        bb = book.best_bid()
        for o in book.resting_for(tid, Side.BUY):
            if bb is not None and o.price_ticks is not None and o.price_ticks >= bb:
                book.cancel(o.order_id)
        _market(session, tid, Side.SELL, int(0.5 * d))

    t_sell = t0 + session.s(20)
    session.at(t_sell, stop_out)
    t_cancel = t_sell + session.ms(600)
    session.at(t_cancel, _cancel_many, session, ids)
    return t_cancel


def f_spooflike_hard_1(session: Session, tid: str, t0: int) -> int:
    """Registered market maker long inventory: big asks walked down one tick at a time, small bids; sells into
    buyers, is occasionally hit on the bid. One-sided cancels and a price that falls while he sells."""
    d = session.depth5_estimate()
    session.traders[tid].typical_order_size = int(1.5 * d)  # he always quotes big on the side he wants to trade
    asks: list[str] = []
    bids: list[str] = []
    step = {"n": 0}

    def requote() -> None:
        _cancel_many(session, asks)
        asks.clear()
        _cancel_many(session, bids)
        bids.clear()
        step["n"] += 1
        # asks one tick inside the touch (first in queue: he wants to sell), bids one tick behind (rarely hit)
        session.after(session.uniform_ns(3, 15), _place_improving, session, tid, Side.SELL, int(1.5 * d), 1, asks)
        session.after(session.uniform_ns(3, 15), _place, session, tid, Side.BUY, int(0.3 * d), 1, bids)

    def drift_down() -> None:
        session.fundamental -= 0.2  # about six ticks over the 90 s episode

    t = t0
    end = t0 + session.s(90)
    while t < end:
        session.at(t, requote)
        session.at(t + session.ms(500), drift_down)
        t += session.s(3)
    for when in range(8, 90, 11):  # buyers keep coming: he is the first ask in queue and sells to each of them
        session.at(t0 + session.s(when), lambda: _market(session, _counterparty(session), Side.BUY, int(0.6 * d)))
    session.at(t0 + session.s(45), lambda: _market(session, _counterparty(session), Side.SELL, int(0.6 * d)))
    session.at(end + session.s(1), _cancel_all, session, tid)
    return end + session.s(1)


# ----------------------------------------------------------------------------------------------
# catalogue
# ----------------------------------------------------------------------------------------------

SCENARIOS: dict[str, ScenarioSpec] = {
    "S-SPOOF-1": ScenarioSpec(
        "S-SPOOF-1",
        Truth.TRUE_ABUSE,
        Disposition.ESCALATE,
        Role.PROP,
        "PROP-EQ",
        [
            "single large resting order 8-15x depth away from the touch",
            "opposite-side fill shortly before cancel",
            "cancel within 500 ms of the fill",
            "one-sided",
            "no market event",
        ],
        CORE_TOOLS,
        "Classic single spoof.",
        0.30,
        s_spoof_1,
    ),
    "S-SPOOF-2": ScenarioSpec(
        "S-SPOOF-2",
        Truth.TRUE_ABUSE,
        Disposition.DRAFT_STOR,
        Role.PROP,
        "PROP-EQ",
        [
            "pattern repeated 3-6 times in 10 minutes",
            "each cycle: large order, opposite fill, cancel",
            "one-sided",
        ],
        CORE_TOOLS,
        "Repeated spoof; repetitions_in_session is the tell.",
        0.15,
        s_spoof_2,
    ),
    "S-LAYER-1": ScenarioSpec(
        "S-LAYER-1",
        Truth.TRUE_ABUSE,
        Disposition.ESCALATE,
        Role.PROP,
        "PROP-EQ",
        [
            "five orders at successive price levels on one side, aggregate ~10x depth",
            "opposite-side fill",
            "all layers cancelled within 1 s",
        ],
        CORE_TOOLS,
        "Layering.",
        0.20,
        s_layer_1,
    ),
    "S-SPOOF-3": ScenarioSpec(
        "S-SPOOF-3",
        Truth.TRUE_ABUSE,
        Disposition.ESCALATE,
        Role.MARKET_MAKER,
        "MM-OTHER",
        [
            "trader is a market maker but NOT registered on this instrument",
            "one-sided large order and opposite fill",
            "no two-sided quoting here",
        ],
        CORE_TOOLS,
        "Misleading profile: market maker elsewhere, spoofer here.",
        0.10,
        s_spoof_1,
        extra={"mm_elsewhere": ["SYN.B"]},
    ),
    "S-SPOOF-4": ScenarioSpec(
        "S-SPOOF-4",
        Truth.TRUE_ABUSE,
        Disposition.ESCALATE,
        Role.ALGO,
        "ALGO-EXEC",
        [
            "six prior CLOSE_FP dispositions in history",
            "current window shows a one-sided spoof, not pegged symmetric cancels",
            "memory must not override current evidence",
        ],
        [*CORE_TOOLS, "get_trader_alert_history"],
        "The trusted-trader trap.",
        0.10,
        s_spoof_4,
        profile_size=250,
        profile_otr=12.0,
    ),
    "S-SPOOF-5": ScenarioSpec(
        "S-SPOOF-5",
        Truth.TRUE_ABUSE,
        Disposition.ESCALATE,
        Role.PROP,
        "PROP-EQ",
        [
            "spoof order partially executed by a late third-party sweep right after the opposite-side trade",
            "remainder cancelled within a second of the hit",
            "one-sided",
        ],
        CORE_TOOLS,
        "Messy spoof: the spoofer got caught in the book before he could pull the order.",
        0.15,
        s_spoof_5,
    ),
    "S-SPOOF-6": ScenarioSpec(
        "S-SPOOF-6",
        Truth.TRUE_ABUSE,
        Disposition.ESCALATE,
        Role.MARKET_MAKER,
        "ETF-MM",
        [
            "registered market maker on this instrument, and it does not explain the pattern",
            "one large one-sided order several times the depth, away from the touch, never executed",
            "opposite-side execution, then the large order cancelled within half a second",
            "the two-sided quoting earlier in the window is ordinary; the large order is not a quote",
        ],
        CORE_TOOLS,
        "The registered-therefore-close trap: features (a) and (b) override the registration.",
        0.15,
        s_spoof_6,
        registered_here=True,
        profile_size=900,
        profile_otr=40.0,
        since=2,
    ),
    "F-MM-1": ScenarioSpec(
        "F-MM-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.MARKET_MAKER,
        "ETF-MM",
        [
            "registered market maker on this instrument",
            "two-sided symmetric quotes and cancels",
            "cancels follow re-quotes, not own fills",
            "quote size typical for the desk",
        ],
        CLOSE_TOOLS,
        "Market making.",
        0.25,
        f_mm_1,
        registered_here=True,
        profile_size=900,
        profile_otr=40.0,
    ),
    "F-ALGO-1": ScenarioSpec(
        "F-ALGO-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.ALGO,
        "ALGO-EXEC",
        [
            "PEGGED child orders with parent ids on both sides",
            "cancels symmetric and correlated with touch moves",
            "no opposite fill benefits from a cancel",
        ],
        CLOSE_TOOLS,
        "Algorithmic re-pricing.",
        0.25,
        f_algo_1,
        profile_size=700,
        profile_otr=25.0,
    ),
    "F-RISK-1": ScenarioSpec(
        "F-RISK-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.PROP,
        "PROP-EQ",
        [
            "all resting orders on both sides cancelled in the same instant",
            "risk_limit_events entry at the cancel time",
            "no beneficial opposite fill",
        ],
        CLOSE_TOOLS,
        "Kill switch.",
        0.0625,
        f_risk_1,
    ),
    "F-NEWS-1": ScenarioSpec(
        "F-NEWS-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.PROP,
        "PROP-EQ",
        [
            "market event within 200 ms before the cancels",
            "market-wide cancel storm, not only this trader",
            "hedge sale precedes the event",
        ],
        CLOSE_TOOLS,
        "News reaction.",
        0.0625,
        f_news_1,
    ),
    "F-ICE-1": ScenarioSpec(
        "F-ICE-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.AGENCY,
        "AGENCY",
        [
            "ICEBERG order type with partial executions (genuine intent)",
            "opposite fill belongs to a different client parent order",
            "client pulled the order",
        ],
        CLOSE_TOOLS,
        "Iceberg for one client, sale for another.",
        0.0625,
        f_ice_1,
        profile_size=800,
        profile_otr=3.0,
    ),
    "F-PARTIAL-1": ScenarioSpec(
        "F-PARTIAL-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.PROP,
        "PROP-EQ",
        [
            "large order partially executed before the size reduction",
            "MODIFY reduction, not a cancel",
            "order later completed",
        ],
        CLOSE_TOOLS,
        "Modification after a partial fill.",
        0.0625,
        f_partial_1,
    ),
    "F-FAT-1": ScenarioSpec(
        "F-FAT-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.PROP,
        "PROP-EQ",
        [
            "one-off order ten times the trader's typical size",
            "cancelled within 2 s with no opposite fill",
            "corrected order follows immediately",
        ],
        CLOSE_TOOLS,
        "Fat finger.",
        0.0625,
        f_fat_1,
    ),
    "F-STOP-1": ScenarioSpec(
        "F-STOP-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.PROP,
        "PROP-EQ",
        [
            "price moved against the resting side before the trader traded",
            "opposite fill was a sale below the earlier purchase (a loss)",
            "price kept falling after the cancels: nothing to revert",
        ],
        CLOSE_TOOLS,
        "Momentum trader stopped out.",
        0.0625,
        f_stop_1,
    ),
    "F-SPOOFLIKE-HARD-1": ScenarioSpec(
        "F-SPOOFLIKE-HARD-1",
        Truth.FALSE_POSITIVE,
        Disposition.CLOSE_FP,
        Role.MARKET_MAKER,
        "ETF-MM",
        [
            "registered market maker on this instrument",
            "same-side fills large (selling inventory), opposite fills small",
            "asks re-priced down step by step while selling",
            "one-sided cancels",
            "price did not snap back after the cancels: no reversion",
        ],
        CLOSE_TOOLS,
        "Hard negative: inventory skew looks like spoofing on OTR alone.",
        0.0625,
        f_spooflike_hard_1,
        registered_here=True,
        profile_size=1000,
        profile_otr=35.0,
    ),
}


def inject(session: Session, spec: ScenarioSpec, trader_id: str, t0: int) -> None:
    """Register the trader now, start the script at t0 (so it sizes itself against the depth at t0)."""
    _profile(session, spec, trader_id)

    def start() -> None:
        t_end = spec.run(session, trader_id, t0)
        session.injections.append(
            Injection(
                scenario_id=spec.id,
                trader_id=trader_id,
                instrument=session.instrument,
                t_start=t0,
                t_end=t_end,
                truth=spec.truth,
                expected_disposition=spec.expected_disposition,
                key_discriminators=list(spec.key_discriminators),
                expected_tools=list(spec.expected_tools),
                notes=spec.notes,
            )
        )

    session.at(t0, start)


def true_specs(catalogue: int = CATALOGUE_LATEST) -> list[ScenarioSpec]:
    return [s for s in SCENARIOS.values() if s.truth is Truth.TRUE_ABUSE and s.since <= catalogue]


def false_specs(catalogue: int = CATALOGUE_LATEST) -> list[ScenarioSpec]:
    return [s for s in SCENARIOS.values() if s.truth is Truth.FALSE_POSITIVE and s.since <= catalogue]

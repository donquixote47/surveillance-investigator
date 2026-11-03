"""Shared vocabulary for the simulator, detector and tools.

Timestamps are integer nanoseconds since the Unix epoch everywhere. Prices are integer ticks
inside the simulator and converted to decimals only when written out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

NS_PER_S = 1_000_000_000
NS_PER_MS = 1_000_000


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def opposite(self) -> Side:
        return Side.SELL if self is Side.BUY else Side.BUY


class EventType(StrEnum):
    NEW = "NEW"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"
    FILL = "FILL"
    PARTIAL_FILL = "PARTIAL_FILL"


class OrderType(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    PEGGED = "PEGGED"
    ICEBERG = "ICEBERG"


class Role(StrEnum):
    MARKET_MAKER = "MARKET_MAKER"
    PROP = "PROP"
    AGENCY = "AGENCY"
    CLIENT = "CLIENT"
    ALGO = "ALGO"


class MarketEventType(StrEnum):
    NEWS = "NEWS"
    MACRO_PRINT = "MACRO_PRINT"
    HALT = "HALT"
    AUCTION = "AUCTION"
    OPEN = "OPEN"
    CLOSE = "CLOSE"


class Truth(StrEnum):
    TRUE_ABUSE = "TRUE_ABUSE"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class Disposition(StrEnum):
    CLOSE_FP = "CLOSE_FP"
    ESCALATE = "ESCALATE"
    DRAFT_STOR = "DRAFT_STOR"


@dataclass(slots=True)
class Order:
    order_id: str
    trader_id: str
    side: Side
    price_ticks: int | None  # None for MARKET orders
    qty: int
    remaining: int
    order_type: OrderType
    parent_order_id: str | None
    ts_new: int
    peak: int | None = None  # ICEBERG visible tip size


# Column order of the order_events table. `qty` is the quantity the event concerns:
# NEW = order size, FILL/PARTIAL_FILL = executed quantity, CANCEL = quantity removed,
# MODIFY = signed delta (negative = reduction). `remaining_qty` is the open quantity after
# the event. `best_bid`/`best_ask` are the touch immediately *before* the event, in ticks.
ORDER_EVENT_COLUMNS = (
    "instrument",
    "ts",
    "order_id",
    "trader_id",
    "event",
    "side",
    "price_ticks",
    "qty",
    "remaining_qty",
    "order_type",
    "parent_order_id",
    "best_bid",
    "best_ask",
)

TRADE_COLUMNS = (
    "instrument",
    "ts",
    "trade_id",
    "buy_order_id",
    "sell_order_id",
    "buy_trader_id",
    "sell_trader_id",
    "price_ticks",
    "qty",
    "aggressor_side",
)


@dataclass(slots=True)
class TraderProfile:
    trader_id: str
    name: str
    desk: str
    role: Role
    registered_mm_instruments: list[str] = field(default_factory=list)
    typical_order_size: int = 0
    typical_daily_otr: float = 0.0
    risk_limit_events: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class MarketEvent:
    ts: int
    instrument: str  # or "*" for market-wide
    type: MarketEventType
    description: str


@dataclass(slots=True)
class Injection:
    """What a scenario did, for labelling. Alerts whose window overlaps [t_start, t_end] for
    the same trader and instrument are attributed to it."""

    scenario_id: str
    trader_id: str
    instrument: str
    t_start: int
    t_end: int
    truth: Truth
    expected_disposition: Disposition
    key_discriminators: list[str]
    expected_tools: list[str]
    notes: str

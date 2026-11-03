"""Limit order book with price-time priority matching and an event tape.

Every change produces one row in the order_events tape (and trades for executions). The tape is
what the detector and the tools consume; the book itself is never exported.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from .types import (
    ORDER_EVENT_COLUMNS,
    TRADE_COLUMNS,
    EventType,
    Order,
    OrderType,
    Side,
)

FillListener = Callable[[Order, int, int, bool], None]  # (order, filled_qty, price_ticks, is_aggressor)


class OrderBook:
    def __init__(self, instrument: str, tick_size: float, clock: Callable[[], int]) -> None:
        self.instrument = instrument
        self.tick_size = tick_size
        self.clock = clock  # returns the current simulated time in ns
        self.bids: dict[int, deque[Order]] = {}
        self.asks: dict[int, deque[Order]] = {}
        self.open: dict[str, Order] = {}
        self.order_events: list[tuple] = []
        self.trades: list[tuple] = []
        self._order_seq = 0
        self._trade_seq = 0
        self._fill_listeners: dict[str, FillListener] = {}  # trader_id -> listener
        self.traded_qty = 0

    # ----- observation -----
    def best_bid(self) -> int | None:
        return max(self.bids) if self.bids else None

    def best_ask(self) -> int | None:
        return min(self.asks) if self.asks else None

    def mid_ticks(self) -> float | None:
        b, a = self.best_bid(), self.best_ask()
        if b is None or a is None:
            return None
        return (a + b) / 2

    def depth_top(self, n: int = 5) -> tuple[int, int]:
        """Aggregate resting size on the top n price levels of each side (bid, ask)."""
        bid_levels = sorted(self.bids, reverse=True)[:n]
        ask_levels = sorted(self.asks)[:n]
        bd = sum(o.remaining for p in bid_levels for o in self.bids[p])
        ad = sum(o.remaining for p in ask_levels for o in self.asks[p])
        return bd, ad

    def snapshot(self, n: int = 5) -> dict:
        bid_levels = sorted(self.bids, reverse=True)[:n]
        ask_levels = sorted(self.asks)[:n]
        return {
            "bids": [(p, sum(o.remaining for o in self.bids[p])) for p in bid_levels],
            "asks": [(p, sum(o.remaining for o in self.asks[p])) for p in ask_levels],
        }

    def resting_for(self, trader_id: str, side: Side | None = None) -> list[Order]:
        return [o for o in self.open.values() if o.trader_id == trader_id and (side is None or o.side == side)]

    def add_fill_listener(self, trader_id: str, fn: FillListener) -> None:
        self._fill_listeners[trader_id] = fn

    # ----- identifiers -----
    def next_order_id(self) -> str:
        self._order_seq += 1
        return f"O-{self._order_seq:08d}"

    # ----- tape -----
    def _record(self, order: Order, event: EventType, qty: int, remaining: int, price: int | None, bb, ba) -> None:
        self.order_events.append(
            (
                self.instrument,
                self.clock(),
                order.order_id,
                order.trader_id,
                str(event),
                str(order.side),
                price,
                qty,
                remaining,
                str(order.order_type),
                order.parent_order_id,
                bb,
                ba,
            )
        )

    # ----- actions -----
    def submit(
        self,
        trader_id: str,
        side: Side,
        qty: int,
        price_ticks: int | None,
        order_type: OrderType = OrderType.LIMIT,
        parent_order_id: str | None = None,
        peak: int | None = None,
    ) -> Order:
        if qty <= 0:
            raise ValueError("qty must be positive")
        if order_type is OrderType.MARKET:
            price_ticks = None
        elif price_ticks is None:
            raise ValueError("limit-type orders need a price")
        order = Order(
            order_id=self.next_order_id(),
            trader_id=trader_id,
            side=side,
            price_ticks=price_ticks,
            qty=qty,
            remaining=qty,
            order_type=order_type,
            parent_order_id=parent_order_id,
            ts_new=self.clock(),
            peak=peak,
        )
        bb, ba = self.best_bid(), self.best_ask()
        self._record(order, EventType.NEW, qty, qty, price_ticks, bb, ba)
        stp = self._match(order)
        if order.remaining > 0:
            if order.order_type is OrderType.MARKET or stp:
                # nothing left to trade against, or the next match would be against the trader's own
                # order (self-trade prevention, cancel-incoming mode): the venue cancels the residual
                self._record(
                    order,
                    EventType.CANCEL,
                    order.remaining,
                    0,
                    order.price_ticks,
                    self.best_bid(),
                    self.best_ask(),
                )
                order.remaining = 0
            else:
                self._rest(order)
        return order

    def cancel(self, order_id: str) -> Order | None:
        order = self.open.get(order_id)
        if order is None:
            return None
        bb, ba = self.best_bid(), self.best_ask()
        self._remove(order)
        self._record(order, EventType.CANCEL, order.remaining, 0, order.price_ticks, bb, ba)
        order.remaining = 0
        return order

    def cancel_all(self, trader_id: str, side: Side | None = None) -> int:
        n = 0
        for o in self.resting_for(trader_id, side):
            self.cancel(o.order_id)
            n += 1
        return n

    def modify(self, order_id: str, new_remaining: int | None = None, new_price: int | None = None) -> Order | None:
        """Change size and/or price of a resting order. A price change or a size increase loses
        queue priority (the order is re-queued at the back of its level), a pure reduction keeps it."""
        order = self.open.get(order_id)
        if order is None:
            return None
        bb, ba = self.best_bid(), self.best_ask()
        old_remaining = order.remaining
        delta = 0
        if new_remaining is not None:
            delta = new_remaining - old_remaining
        price_changed = new_price is not None and new_price != order.price_ticks
        if price_changed or delta > 0:
            self._remove(order)
            if new_price is not None:
                order.price_ticks = new_price
            if new_remaining is not None:
                order.remaining = new_remaining
            if order.remaining > 0:
                self._record(order, EventType.MODIFY, delta, order.remaining, order.price_ticks, bb, ba)
                stp = self._match(order)
                if order.remaining > 0 and not stp:
                    self._rest(order)
                elif order.remaining > 0:
                    self._record(
                        order,
                        EventType.CANCEL,
                        order.remaining,
                        0,
                        order.price_ticks,
                        self.best_bid(),
                        self.best_ask(),
                    )
                    order.remaining = 0
            return order
        if new_remaining is not None:
            order.remaining = new_remaining
        if order.remaining <= 0:
            self._remove(order)
            order.remaining = 0
        self._record(order, EventType.MODIFY, delta, order.remaining, order.price_ticks, bb, ba)
        return order

    # ----- internals -----
    def _book_side(self, side: Side) -> dict[int, deque[Order]]:
        return self.bids if side is Side.BUY else self.asks

    def _rest(self, order: Order) -> None:
        assert order.price_ticks is not None
        self._book_side(order.side).setdefault(order.price_ticks, deque()).append(order)
        self.open[order.order_id] = order

    def _remove(self, order: Order) -> None:
        self.open.pop(order.order_id, None)
        book = self._book_side(order.side)
        level = book.get(order.price_ticks)  # type: ignore[arg-type]
        if level is None:
            return
        try:
            level.remove(order)
        except ValueError:
            pass
        if not level:
            del book[order.price_ticks]  # type: ignore[arg-type]

    def _crosses(self, order: Order) -> bool:
        if order.side is Side.BUY:
            a = self.best_ask()
            return a is not None and (order.price_ticks is None or a <= order.price_ticks)
        b = self.best_bid()
        return b is not None and (order.price_ticks is None or b >= order.price_ticks)

    def _match(self, incoming: Order) -> bool:
        """Match the incoming order against the contra side. Returns True if matching stopped because the
        next resting order belongs to the same trader (self-trade prevention)."""
        contra_book = self.asks if incoming.side is Side.BUY else self.bids
        while incoming.remaining > 0 and self._crosses(incoming):
            level_price = self.best_ask() if incoming.side is Side.BUY else self.best_bid()
            assert level_price is not None
            level = contra_book[level_price]
            resting = level[0]
            if resting.trader_id == incoming.trader_id:
                return True
            visible = resting.remaining if resting.peak is None else min(resting.peak, resting.remaining)
            fill = min(incoming.remaining, visible)
            bb, ba = self.best_bid(), self.best_ask()
            incoming.remaining -= fill
            resting.remaining -= fill
            self._record(
                incoming,
                EventType.FILL if incoming.remaining == 0 else EventType.PARTIAL_FILL,
                fill,
                incoming.remaining,
                level_price,
                bb,
                ba,
            )
            self._record(
                resting,
                EventType.FILL if resting.remaining == 0 else EventType.PARTIAL_FILL,
                fill,
                resting.remaining,
                level_price,
                bb,
                ba,
            )
            self._trade_seq += 1
            buy, sell = (incoming, resting) if incoming.side is Side.BUY else (resting, incoming)
            self.trades.append(
                (
                    self.instrument,
                    self.clock(),
                    f"T-{self._trade_seq:08d}",
                    buy.order_id,
                    sell.order_id,
                    buy.trader_id,
                    sell.trader_id,
                    level_price,
                    fill,
                    str(incoming.side),
                )
            )
            self.traded_qty += fill
            if resting.remaining == 0:
                level.popleft()
                self.open.pop(resting.order_id, None)
                if not level:
                    del contra_book[level_price]
            elif resting.peak is not None:
                # iceberg: replenish the visible tip and lose priority
                level.rotate(-1)
            for order, is_aggr in ((incoming, True), (resting, False)):
                listener = self._fill_listeners.get(order.trader_id)
                if listener is not None:
                    listener(order, fill, level_price, is_aggr)
        return False


__all__ = ["ORDER_EVENT_COLUMNS", "TRADE_COLUMNS", "OrderBook"]

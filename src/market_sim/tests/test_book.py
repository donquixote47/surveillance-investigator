import pandas as pd

from market_sim.book import OrderBook
from market_sim.types import ORDER_EVENT_COLUMNS, EventType, OrderType, Side


class Clock:
    def __init__(self) -> None:
        self.t = 1_000

    def __call__(self) -> int:
        return self.t


def make() -> tuple[OrderBook, Clock]:
    c = Clock()
    return OrderBook("SYN.A", 0.01, c), c


def tape(book: OrderBook) -> pd.DataFrame:
    return pd.DataFrame.from_records(book.order_events, columns=list(ORDER_EVENT_COLUMNS))


def test_limit_rests_and_market_matches_fifo() -> None:
    book, c = make()
    a = book.submit("A", Side.SELL, 100, 10_002)
    c.t += 1
    b = book.submit("B", Side.SELL, 100, 10_002)
    c.t += 1
    assert book.best_ask() == 10_002 and book.best_bid() is None
    m = book.submit("C", Side.BUY, 150, None, OrderType.MARKET)
    assert m.remaining == 0
    assert a.remaining == 0 and b.remaining == 50  # price-time priority: A first
    ev = tape(book)
    fills = ev[ev.event.isin([str(EventType.FILL), str(EventType.PARTIAL_FILL)])]
    assert set(fills.order_id) == {a.order_id, b.order_id, m.order_id}
    assert len(book.trades) == 2 and book.traded_qty == 150


def test_event_tape_records_pre_event_bbo_and_quantities() -> None:
    book, c = make()
    book.submit("A", Side.BUY, 100, 9_998)
    book.submit("A", Side.SELL, 100, 10_002)
    c.t += 1
    o = book.submit("B", Side.BUY, 40, 10_002)  # marketable limit, fully filled
    ev = tape(book)
    new_row = ev[(ev.order_id == o.order_id) & (ev.event == str(EventType.NEW))].iloc[0]
    assert (new_row.best_bid, new_row.best_ask) == (9_998, 10_002)  # touch before the order
    assert new_row.qty == 40 and new_row.remaining_qty == 40
    fill_row = ev[(ev.order_id == o.order_id) & (ev.event == str(EventType.FILL))].iloc[0]
    assert fill_row.qty == 40 and fill_row.remaining_qty == 0


def test_cancel_and_modify() -> None:
    book, c = make()
    o = book.submit("A", Side.BUY, 100, 9_998)
    c.t += 1
    book.modify(o.order_id, new_remaining=30)  # pure reduction keeps the order in the book
    assert book.open[o.order_id].remaining == 30
    ev = tape(book)
    mod = ev[ev.event == str(EventType.MODIFY)].iloc[0]
    assert mod.qty == -70 and mod.remaining_qty == 30
    c.t += 1
    book.cancel(o.order_id)
    assert o.order_id not in book.open
    canc = tape(book)[lambda d: d.event == str(EventType.CANCEL)].iloc[0]
    assert canc.qty == 30 and canc.remaining_qty == 0


def test_market_order_residual_is_cancelled_when_book_is_empty() -> None:
    book, _ = make()
    book.submit("A", Side.SELL, 50, 10_000)
    m = book.submit("B", Side.BUY, 80, None, OrderType.MARKET)
    assert m.remaining == 0
    ev = tape(book)
    assert ((ev.order_id == m.order_id) & (ev.event == str(EventType.CANCEL)) & (ev.qty == 30)).any()


def test_self_trade_prevention_cancels_incoming_residual() -> None:
    book, c = make()
    book.submit("A", Side.SELL, 100, 10_000)  # own resting ask
    c.t += 1
    book.submit("B", Side.SELL, 20, 9_999)  # someone else, better price
    c.t += 1
    m = book.submit("A", Side.BUY, 100, None, OrderType.MARKET)
    assert m.remaining == 0
    ev = tape(book)
    mine = ev[ev.order_id == m.order_id]
    assert (mine.event == str(EventType.FILL)).sum() + (
        mine.event == str(EventType.PARTIAL_FILL)
    ).sum() == 1  # only B's 20
    assert ((mine.event == str(EventType.CANCEL)) & (mine.qty == 80)).any()
    assert book.open  # A's ask is still resting, never traded against itself


def test_iceberg_shows_only_the_tip_and_loses_priority_on_refresh() -> None:
    book, c = make()
    ice = book.submit("A", Side.BUY, 1_000, 9_998, OrderType.ICEBERG, peak=100)
    c.t += 1
    other = book.submit("B", Side.BUY, 100, 9_998)
    c.t += 1
    book.submit("C", Side.SELL, 150, None, OrderType.MARKET)
    # first 100 from the iceberg tip, then the iceberg goes to the back: next 50 from B
    assert ice.remaining == 900 and other.remaining == 50
    ev = tape(book)
    assert ev[(ev.order_id == ice.order_id) & (ev.event == str(EventType.NEW))].iloc[0].qty == 1_000

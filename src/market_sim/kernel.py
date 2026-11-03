"""Discrete-event scheduler: a heap of (ts, seq, callback)."""

from __future__ import annotations

import heapq
from collections.abc import Callable
from typing import Any


class Kernel:
    def __init__(self, start_ts: int, end_ts: int) -> None:
        self.now = start_ts
        self.start_ts = start_ts
        self.end_ts = end_ts
        self._heap: list[tuple[int, int, Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = []
        self._seq = 0
        self.processed = 0

    def schedule(self, ts: int, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if ts < self.now:
            ts = self.now
        self._seq += 1
        heapq.heappush(self._heap, (ts, self._seq, fn, args, kwargs))

    def schedule_in(self, delay_ns: int, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.schedule(self.now + delay_ns, fn, *args, **kwargs)

    def run(self) -> None:
        heap = self._heap
        while heap:
            ts, _seq, fn, args, kwargs = heapq.heappop(heap)
            if ts > self.end_ts:
                break
            self.now = ts
            fn(*args, **kwargs)
            self.processed += 1

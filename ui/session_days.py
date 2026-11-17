"""Which days the analyst screen offers, and which one it opens on.

A surveillance queue holds what the detector has already raised. So the screen opens on today and offers no day
after today, whatever the firm's tables hold: the generalisation set seed8 has session days up to 2026-11-27, and
each of them appears on the screen when that day arrives. Today is offered even when it is not a session day (a
weekend, or any day after the dataset ends); its queue is then empty, as a real one would be.

No Streamlit here, so the rule can be tested without rendering the app.
"""

from __future__ import annotations

from datetime import date

# Session days in the firm's tables, newest first (the way a queue reads): seed8 (November, the generalisation set,
# loaded 2026-11-11) then seed7 (October, the evaluated set). The demo script's alerts are on the October days.
# The focused set seed9 (September) is not listed: it exists for one measurement, not for the queue.
DATASET_DATES = [
    "2026-11-27", "2026-11-26", "2026-11-25", "2026-11-24", "2026-11-23",
    "2026-11-20", "2026-11-19", "2026-11-18", "2026-11-17", "2026-11-16",
    "2026-11-13", "2026-11-12", "2026-11-11", "2026-11-10", "2026-11-09",
    "2026-11-06", "2026-11-05", "2026-11-04", "2026-11-03", "2026-11-02",
    "2026-10-30", "2026-10-29", "2026-10-28", "2026-10-27", "2026-10-26",
    "2026-10-23", "2026-10-22", "2026-10-21", "2026-10-20", "2026-10-19",
    "2026-10-16", "2026-10-15", "2026-10-14", "2026-10-13", "2026-10-12",
    "2026-10-09", "2026-10-08", "2026-10-07", "2026-10-06", "2026-10-05",
]  # fmt: skip


def offered_days(today: str | None = None) -> list[str]:
    """The days the screen offers, newest first: today, then every session day before it.

    `today` is an ISO date (YYYY-MM-DD); by default the date of the machine the screen runs on. The first entry is
    the day the screen opens on.
    """
    today = today or date.today().isoformat()
    return [today, *(d for d in DATASET_DATES if d < today)]

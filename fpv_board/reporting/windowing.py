from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable


def _fmt_hour(dt: datetime) -> str:
    hour = dt.hour % 12
    hour = 12 if hour == 0 else hour
    suffix = "am" if dt.hour < 12 else "pm"
    return f"{hour}{suffix}"


def format_window(start: datetime, end: datetime) -> str:
    return f"{_fmt_hour(start)}-{_fmt_hour(end)}"


def build_flight_windows(hour_rows: Iterable[dict]) -> list[tuple[datetime, datetime]]:
    rows = sorted(hour_rows, key=lambda r: r["hour_start"])
    windows: list[tuple[datetime, datetime]] = []
    current_start: datetime | None = None
    current_end: datetime | None = None

    for row in rows:
        hour = row["hour_start"]
        status = row["status"]
        flyable = status not in {"NOPE", "ERROR"}

        if not flyable:
            if current_start and current_end:
                windows.append((current_start, current_end + timedelta(hours=1)))
            current_start = None
            current_end = None
            continue

        if current_start is None:
            current_start = hour
            current_end = hour
            continue

        assert current_end is not None
        if hour == current_end + timedelta(hours=1):
            current_end = hour
        else:
            windows.append((current_start, current_end + timedelta(hours=1)))
            current_start = hour
            current_end = hour

    if current_start and current_end:
        windows.append((current_start, current_end + timedelta(hours=1)))

    return windows

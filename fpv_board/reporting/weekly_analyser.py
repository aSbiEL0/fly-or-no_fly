from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from fpv_board.reporting.windowing import build_flight_windows, format_window

TZ = ZoneInfo("Europe/London")


def _parse_float(v: str) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _day_summary_sentence(avg_wind: float | None, rainy_ratio: float | None, avg_temp: float | None) -> str:
    if avg_wind is not None and avg_wind >= 7.5:
        return "Very windy overall"
    if rainy_ratio is not None and rainy_ratio >= 0.4:
        return "Showery overall"
    if avg_temp is not None and avg_temp <= 4:
        return "Cold overall"
    return "Mixed but manageable"


def _range(now: datetime) -> tuple[datetime, datetime]:
    now = now.astimezone(TZ)
    weekday = now.weekday()  # Mon=0..Sun=6
    days_since_sat = (weekday - 5) % 7
    start = (now - timedelta(days=days_since_sat)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def load_rows(csv_path: Path, now: datetime) -> list[dict]:
    start, end = _range(now)
    if not csv_path.exists():
        return []

    result: list[dict] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ts = datetime.strptime(row["hour_start_local"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
            if not (start <= ts <= end):
                continue
            result.append(
                {
                    "hour_start": ts.replace(tzinfo=None),
                    "date": ts.date(),
                    "row_type": row.get("row_type", "HOURLY"),
                    "status": row.get("status", "ERROR"),
                    "wind_ms": _parse_float(row.get("wind_ms", "")),
                    "gust_ms": _parse_float(row.get("gust_ms", "")),
                    "temp_c": _parse_float(row.get("temp_c", "")),
                    "rain_probability": _parse_float(row.get("rain_probability", "")),
                }
            )
    return result


def build_past_week_summary(csv_path: Path, now: datetime) -> str:
    rows = load_rows(csv_path, now)
    by_day: dict = defaultdict(list)
    for row in rows:
        by_day[row["date"]].append(row)

    ordered_days = [
        (now.astimezone(TZ).date() - timedelta(days=i))
        for i in range(6, -1, -1)
    ]

    lines = ["PAST WEEK SUMMARY", ""]
    for day in ordered_days:
        day_rows = sorted(by_day.get(day, []), key=lambda r: r["hour_start"])
        lines.append(f"{day.strftime('%A')}:")
        if not day_rows:
            lines.append("* No flight windows")
            lines.append("* Average wind: n/a")
            lines.append("* Gust peak: n/a")
            lines.append("* Average temp: n/a")
            lines.append("* Summary: No data logged")
            lines.append("")
            continue

        timeline_rows = [{"hour_start": r["hour_start"], "status": r["status"]} for r in day_rows]
        windows = build_flight_windows(timeline_rows)
        if windows:
            labels = ", ".join(format_window(start, end) for start, end in windows)
            lines.append(f"* {len(windows)} flight windows ({labels})")
        else:
            lines.append("* No flight windows")

        calc_rows = [r for r in day_rows if r["row_type"] != "ERROR"]
        winds = [r["wind_ms"] for r in calc_rows if r["wind_ms"] is not None]
        gusts = [r["gust_ms"] for r in calc_rows if r["gust_ms"] is not None]
        temps = [r["temp_c"] for r in calc_rows if r["temp_c"] is not None]
        rains = [r["rain_probability"] for r in calc_rows if r["rain_probability"] is not None]

        avg_wind = mean(winds) if winds else None
        gust_peak = max(gusts) if gusts else None
        avg_temp = mean(temps) if temps else None
        rainy_ratio = (sum(1 for r in rains if r >= 70) / len(rains)) if rains else None

        lines.append(f"* Average wind: {avg_wind:.1f}m/s" if avg_wind is not None else "* Average wind: n/a")
        lines.append(f"* Gust peak: {gust_peak:.0f}m/s" if gust_peak is not None else "* Gust peak: n/a")
        lines.append(f"* Average temp: {round(avg_temp):.0f} C" if avg_temp is not None else "* Average temp: n/a")
        lines.append(f"* Summary: {_day_summary_sentence(avg_wind, rainy_ratio, avg_temp)}")
        lines.append("")

    return "\n".join(lines).strip()

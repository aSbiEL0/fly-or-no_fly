from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

from fpv_board.main import evaluate, HourlyPoint

TZ = ZoneInfo("Europe/London")


def _status_from_daily(day: dict[str, Any], cfg: dict[str, Any], date_value: datetime) -> str:
    critical_keys = [
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
        "precipitation_probability_max",
        "temperature_2m_min",
        "cloudcover_max",
    ]
    missing = sum(1 for k in critical_keys if day.get(k) is None)
    if missing >= 3:
        return "NOPE"

    point = HourlyPoint(
        timestamp=date_value,
        wind_ms=float(day.get("wind_speed_10m_max") or 0.0),
        gust_ms=float(day.get("wind_gusts_10m_max") or 0.0),
        rain_probability=float(day.get("precipitation_probability_max") or 0.0),
        temp_c=float(day.get("temperature_2m_min") if day.get("temperature_2m_min") is not None else 99.0),
        cloud_cover=float(day.get("cloudcover_max") or 0.0),
    )
    evaluated = evaluate([point], cfg)
    return str(evaluated["status"])


def fetch_weekly_forecast(cfg: dict[str, Any], now: datetime) -> str:
    loc = cfg["location"]
    tz_name = "Europe/London"
    base = now.astimezone(TZ)
    saturday = (base + timedelta(days=(5 - base.weekday()) % 7)).date()
    end_date = saturday + timedelta(days=6)

    params = {
        "latitude": float(loc["latitude"]),
        "longitude": float(loc["longitude"]),
        "timezone": tz_name,
        "start_date": saturday.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "wind_speed_10m_max,wind_gusts_10m_max,precipitation_probability_max,temperature_2m_min,cloudcover_max",
        "wind_speed_unit": "ms",
        "temperature_unit": "celsius",
    }

    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    daily = payload.get("daily", {})
    times = daily.get("time", [])

    lines = ["NEXT 7 DAYS FORECAST", ""]
    for idx, dt_str in enumerate(times[:7]):
        date_value = datetime.fromisoformat(dt_str)
        day = {
            "wind_speed_10m_max": _index_or_none(daily.get("wind_speed_10m_max", []), idx),
            "wind_gusts_10m_max": _index_or_none(daily.get("wind_gusts_10m_max", []), idx),
            "precipitation_probability_max": _index_or_none(daily.get("precipitation_probability_max", []), idx),
            "temperature_2m_min": _index_or_none(daily.get("temperature_2m_min", []), idx),
            "cloudcover_max": _index_or_none(daily.get("cloudcover_max", []), idx),
        }
        status = _status_from_daily(day, cfg, date_value)
        lines.append(f"{date_value.strftime('%A')}: {status}")
    return "\n".join(lines)


def _index_or_none(values: list[Any], idx: int) -> Any:
    return values[idx] if idx < len(values) else None

from datetime import datetime

from fpv_board.reporting.weekly_forecast import _status_from_daily


def test_daily_forecast_status_derivation():
    cfg = {
        "thresholds": {
            "marginal_multiplier": 1.25,
            "sustained_fly_max": 18,
            "gust_fly_max": 25,
            "gust_spread_fly_max": 8,
            "rain_probability_fly_max": 85,
            "temperature_min_c": 2,
            "cloud_cover_warn": 100,
        },
        "forecast": {"trend_window_hours": 6},
    }
    day = {
        "wind_speed_10m_max": 2,
        "wind_gusts_10m_max": 3,
        "precipitation_probability_max": 5,
        "temperature_2m_min": 12,
        "cloudcover_max": 20,
    }
    assert _status_from_daily(day, cfg, datetime(2026, 1, 10)) == "GREAT"

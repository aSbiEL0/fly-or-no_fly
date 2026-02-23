from datetime import datetime

from fpv_board.main import HourlyPoint, evaluate


def _cfg(window_aggregation: str):
    return {
        "thresholds": {
            "marginal_multiplier": 1.5,
            "nope_multiplier": 1.8,
            "sustained_fly_max": 18,
            "gust_fly_max": 28,
            "gust_spread_fly_max": 12,
            "rain_probability_fly_max": 85,
            "temperature_min_c": 2,
            "cloud_cover_warn": 100,
        },
        "forecast": {"trend_window_hours": 6, "window_aggregation": window_aggregation},
    }


def test_single_severe_spike_is_risky_not_nope():
    points = [
        HourlyPoint(datetime(2026, 1, 1, 12), wind_ms=3.0, gust_ms=12.0, rain_probability=20, cloud_cover=20, temp_c=10),
        HourlyPoint(datetime(2026, 1, 1, 13), wind_ms=3.0, gust_ms=4.0, rain_probability=20, cloud_cover=20, temp_c=10),
    ]

    worst_result = evaluate(points, _cfg("worst"))

    assert worst_result["status"] == "RISKY"


def test_multiple_severe_metrics_still_nope():
    points = [
        HourlyPoint(datetime(2026, 1, 1, 12), wind_ms=20.0, gust_ms=23.0, rain_probability=20, cloud_cover=20, temp_c=10),
        HourlyPoint(datetime(2026, 1, 1, 13), wind_ms=20.0, gust_ms=23.0, rain_probability=20, cloud_cover=20, temp_c=10),
    ]

    result = evaluate(points, _cfg("worst"))

    assert result["status"] == "NOPE"


def test_average_window_aggregation_softens_spikes_to_ok():
    points = [
        HourlyPoint(datetime(2026, 1, 1, 12), wind_ms=3.1, gust_ms=8.9, rain_probability=20, cloud_cover=20, temp_c=10),
        HourlyPoint(datetime(2026, 1, 1, 13), wind_ms=3.0, gust_ms=4.0, rain_probability=20, cloud_cover=20, temp_c=10),
    ]

    average_result = evaluate(points, _cfg("average"))

    assert average_result["status"] in {"GREAT", "OK"}

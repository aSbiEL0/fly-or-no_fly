from datetime import datetime

from fpv_board.reporting.windowing import build_flight_windows, format_window


def test_window_grouping_and_formatting():
    rows = [
        {"hour_start": datetime(2026, 1, 5, 14), "status": "OK"},
        {"hour_start": datetime(2026, 1, 5, 15), "status": "RISKY"},
        {"hour_start": datetime(2026, 1, 5, 16), "status": "NOPE"},
        {"hour_start": datetime(2026, 1, 5, 17), "status": "GREAT"},
    ]
    windows = build_flight_windows(rows)
    assert len(windows) == 2
    assert format_window(*windows[0]) == "2pm-4pm"
    assert format_window(*windows[1]) == "5pm-6pm"

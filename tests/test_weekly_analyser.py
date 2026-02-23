import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fpv_board.reporting.weekly_analyser import build_past_week_summary


def test_averages_include_nope_exclude_error(tmp_path: Path):
    p = tmp_path / "status_log.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ts_local","hour_start_local","row_type","status","wind_ms","gust_ms","spread_ms","rain_probability","temp_c","cloud_cover","is_daylight","reason","score","trend"
        ])
        writer.writerow(["2026-01-10 10:05:00","2026-01-10 10:00:00","HOURLY","NOPE","4","10","6","80","8","90","1","x","2","No change forecasted"])
        writer.writerow(["2026-01-10 11:05:00","2026-01-10 11:00:00","HOURLY","OK","6","13","7","20","10","50","1","x","1","No change forecasted"])
        writer.writerow(["2026-01-10 12:05:00","2026-01-10 12:00:00","ERROR","ERROR","","","","","","","1","API_FAIL","",""])

    now = datetime(2026, 1, 10, 16, tzinfo=ZoneInfo("Europe/London"))
    text = build_past_week_summary(p, now)
    assert "Average wind: 5.0m/s" in text
    assert "Gust peak: 13m/s" in text
    assert "Average temp: 9 C" in text

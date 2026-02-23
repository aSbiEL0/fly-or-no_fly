from pathlib import Path

from fpv_board.logging.csv_logger import StatusCsvLogger


def test_idempotency_by_hour(tmp_path: Path):
    logger = StatusCsvLogger(tmp_path / "status_log.csv", tmp_path / "index.json")
    row = {
        "ts_local": "2026-01-10 11:05:00",
        "hour_start_local": "2026-01-10 11:00:00",
        "row_type": "HOURLY",
        "status": "OK",
        "is_daylight": 1,
        "reason": "x",
        "score": 1,
        "trend": "No change forecasted",
    }
    assert logger.append_if_new_hour(row) is True
    assert logger.append_if_new_hour(row) is False

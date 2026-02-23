from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

CSV_COLUMNS = [
    "ts_local",
    "hour_start_local",
    "row_type",
    "status",
    "wind_ms",
    "gust_ms",
    "spread_ms",
    "rain_probability",
    "temp_c",
    "cloud_cover",
    "is_daylight",
    "reason",
    "score",
    "trend",
]


class StatusCsvLogger:
    def __init__(self, csv_path: Path, index_path: Path) -> None:
        self.csv_path = csv_path
        self.index_path = index_path

    def _load_index(self) -> set[str]:
        if not self.index_path.exists():
            return set()
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            return set(payload.get("hours", []))
        except (OSError, json.JSONDecodeError):
            return set()

    def _save_index(self, hours: set[str]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps({"hours": sorted(hours)}, indent=2), encoding="utf-8")

    def _scan_existing_hour(self, hour_start_local: str) -> bool:
        if not self.csv_path.exists():
            return False
        try:
            with self.csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row.get("hour_start_local") == hour_start_local:
                        return True
        except OSError:
            return False
        return False

    def append_if_new_hour(self, row: dict[str, Any]) -> bool:
        hour_start_local = str(row["hour_start_local"])
        idx = self._load_index()
        if hour_start_local in idx:
            return False
        if self._scan_existing_hour(hour_start_local):
            idx.add(hour_start_local)
            self._save_index(idx)
            return False

        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self.csv_path.exists()
        with self.csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in CSV_COLUMNS})
        idx.add(hour_start_local)
        self._save_index(idx)
        return True

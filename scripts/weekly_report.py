#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fpv_board.main import load_config
from fpv_board.notify.smtp_email import SmtpEmailClient, load_dotenv
from fpv_board.reporting.weekly_analyser import build_past_week_summary
from fpv_board.reporting.weekly_forecast import fetch_weekly_forecast
from fpv_board.state.state_store import StateStore

TZ = ZoneInfo("Europe/London")
SUBJECT = "Drone Dashboard Weekly Update & Forecast"


def _allowed_retry_slots(now: datetime) -> bool:
    now = now.astimezone(TZ)
    return (
        (now.weekday() == 4 and now.hour in {16, 17, 18})
        or (now.weekday() == 5 and now.hour in {16, 17, 18})
    )


def build_body(summary: str, forecast: str, include_fyi: bool) -> str:
    parts: list[str] = []
    if include_fyi:
        parts.append("FYI: last week’s report email failed to send due to an SMTP outage.")
        parts.append("")
    parts.extend([summary, "", forecast])
    return "\n".join(parts).strip()


def run(config_path: Path, dotenv_path: Path, force: bool = False) -> int:
    cfg = load_config(config_path)
    root = config_path.resolve().parent.parent
    data_dir = root / "data"
    state_store = StateStore(data_dir / "state.json")
    state = state_store.load()

    now = datetime.now(TZ)
    if not force and not _allowed_retry_slots(now):
        logging.info("Skipping run outside retry windows")
        return 0

    summary = build_past_week_summary(data_dir / "status_log.csv", now)
    try:
        forecast = fetch_weekly_forecast(cfg, now)
    except Exception as exc:  # noqa: BLE001
        forecast = "NEXT 7 DAYS FORECAST\n\nForecast unavailable this run due to API error."
        logging.warning("Forecast API failed: %s", exc)

    body = build_body(summary, forecast, include_fyi=bool(state.get("weekly_email_failed")))

    load_dotenv(dotenv_path)
    client = SmtpEmailClient()

    try:
        client.send(SUBJECT, body)
        state["weekly_email_failed"] = False
        state["weekly_last_sent"] = now.isoformat()
        state_store.save(state)
        logging.info("Weekly email sent")
        return 0
    except Exception as exc:  # noqa: BLE001
        state["weekly_email_failed"] = True
        state["weekly_last_error"] = str(exc)
        state_store.save(state)
        logging.exception("Weekly email send failed")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly FPV report email sender")
    parser.add_argument("--config", default="/opt/fpv-board/fpv_board/config.json")
    parser.add_argument("--dotenv", default="/opt/fpv-board/.env")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(Path(args.config), Path(args.dotenv), args.force))

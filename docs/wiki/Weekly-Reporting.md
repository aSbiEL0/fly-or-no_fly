# Weekly Reporting and Alerts

## Data pipeline
- Hourly updater writes daylight rows to `data/status_log.csv`.
- Rows are idempotent per `hour_start_local` and indexed by `data/index.json`.
- API failures during daylight append `ERROR` rows.

## Weekly report timing
- `weekly-report.timer` runs Friday and Saturday at 16:00, 17:00, 18:00 (Europe/London host time).
- The script self-handles retries and clears failure state after success.

## Email content
- Subject: `Drone Dashboard Weekly Update & Forecast`
- Sender display: `Pi Drone Dash`
- Receiver: from `EMAIL_TO`
- Includes past week summary from CSV and one weekly Open-Meteo daily-forecast API call.

## Escalation warnings
- Consecutive daylight API failures tracked in `data/state.json`.
- Warning emails sent at counts: 6, 18, 30, 42.
- Subject prefix: `[WARNING]`.

## Yearly reset
- `yearly-log-reset.timer` triggers Jan 1 at 00:05.
- Deletes `status_log.csv` and `index.json`.

## State file keys
- `weekly_email_failed`
- `weekly_last_sent`
- `weekly_last_error`
- `api_failure.consecutive_daylight_failures`
- `api_failure.last_warning_count`

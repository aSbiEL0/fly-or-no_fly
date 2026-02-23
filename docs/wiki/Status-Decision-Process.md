# Status Decision Process (Comprehensive)

This document records, in detail, how the flight board computes a status (`GREAT`, `OK`, `RISKY`, `NOPE`) from weather forecast data.

## 1) End-to-end flow

The runtime decision path is:

1. Fetch Open-Meteo forecast data (`hourly` + `daily`).
2. Parse hourly points into typed values (`HourlyPoint`).
3. Select an evaluation window (`now` to `now + forecast.hours_ahead`) with optional daylight filtering.
4. Evaluate risk from selected points.
5. Convert numeric score to status.
6. Render and show status.

Core implementation lives in `fpv_board/main.py`.

## 2) Forecast point selection

### 2.1 Time window

`select_eval_points(...)` takes all parsed hourly points and keeps only points in:

- `[now, now + hours_ahead]`

`hours_ahead` comes from `forecast.hours_ahead` in config.

### 2.2 Daylight filter

If `forecast.daylight_only` is enabled:

- and there is **no** active daylight window for `now`, selection returns an empty list.
- otherwise points are further filtered to sunrise/sunset for the current daylight window.

The daylight window comes from `next_daylight_window(...)`, which returns the current day window only when `sunrise <= now <= sunset`.

## 3) Empty selection behavior (night/no forecast window)

If no points remain after filtering, `evaluate(...)` immediately returns:

- `status = NOPE`
- `reason = "Night / No daylight forecast"`
- `score = 3`

This path bypasses metric scoring.

## 4) Aggregation mode: `average` vs `worst`

After selection, `evaluate(...)` builds a `summary` over the window based on `forecast.window_aggregation`:

- `average`: arithmetic mean for wind, gust, spread, rain, temp, cloud.
- `worst` (fallback/default behavior):
  - max wind
  - max gust
  - max gust spread (`gust - wind`)
  - max rain probability
  - **min** temperature
  - max cloud cover

This summary object is then used for all risk checks.

## 5) Thresholds and units

### 5.1 Unit conversion

Wind-related limits in config are expressed in mph and converted to m/s at evaluation time via:

- `mph_to_ms(v) = v * 0.44704`

Applied to:

- `sustained_fly_max`
- `gust_fly_max`
- `gust_spread_fly_max`

### 5.2 Key threshold knobs

From `thresholds`:

- `marginal_multiplier` controls non-severe caution band scaling fallback.
- `nope_multiplier` controls severe band threshold used for level 3 checks.
  - if missing, defaults to `marginal_multiplier * 1.25`.
- `rain_probability_fly_max`, `temperature_min_c`, `cloud_cover_warn` are used directly.

Cloud scoring is skipped if `cloud_cover_warn >= 100`.

## 6) Per-metric risk level model

Each metric is converted to an integer level by `_metric_level(...)`.

### 6.1 Higher-is-worse metrics

For wind/gust/spread/rain/cloud:

- level 3 (severe): `actual > threshold * nope_multiplier`
- level 2 (high): `actual > threshold`
- level 1 (rising): `actual > threshold * 0.85`
- level 0: otherwise

### 6.2 Lower-is-worse metric (temperature)

For temperature:

- level 2 (cold): `actual < temperature_min_c`
- level 1 (cool): `actual < temperature_min_c + 2`
- level 0: otherwise

Note: temperature currently does not produce level 3 in this model.

## 7) Combining metric levels into one score

After computing each metric level:

- `score = max(metric_levels)`
- `severe_count = count(level >= 3)`
- `risky_count = count(level >= 2)`

Humanization rule:

- If there is exactly one severe metric (`severe_count == 1`) and fewer than two risky metrics (`risky_count < 2`), a provisional `score == 3` is downgraded to `score = 2`.
- Intent: one isolated spike should usually read `RISKY`, not `NOPE`.

## 8) Score to status mapping

`status_from_score(score)` maps as:

- `score <= 0` -> `GREAT`
- `score == 1` -> `OK`
- `score == 2` -> `RISKY`
- `score >= 3` -> `NOPE`

## 9) Reason text selection

Default reason is `"conditions stable"`.

Then evaluator picks the first metric at or above a target level:

- target level is `max(score, 1)`

Reason vocabulary:

- level 3: `"<metric> very high"`
- level 2: `"<metric> high"` (or `"cold"` for temperature)
- level 1: `"<metric> rising"` (or `"cool"` for temperature)

Night/no-daylight path uses the fixed reason `"Night / No daylight forecast"`.

## 10) Trend string (orthogonal to status)

`build_trend(...)` computes a separate trend message; it does not directly affect status.

- It compares an "early" slice vs "later" slice of the selected points using a simple weighted risk proxy.
- Outputs:
  - `Worsening after HH:MM`
  - `Conditions improving later`
  - `No change forecasted`

## 11) Weekly report path

Weekly report status computation (`fpv_board/reporting/weekly_forecast.py`) reuses `evaluate(...)` by building synthetic points.

Special-case behavior:

- if at least 3 key daily fields are missing, daily status is forced to `NOPE`.
- otherwise a synthetic hourly point is evaluated through the same status logic described above.

## 12) Display orientation and status rendering notes

Display rendering supports `display.rotation_degrees` (e.g., `180`) and rotates both normal and night-image output.

Status and reason are still computed before render; rotation does not affect decision logic.

## 13) Operational defaults currently configured

Current config defaults relevant to decisioning:

- `forecast.hours_ahead = 1`
- `forecast.window_aggregation = "average"`
- `forecast.daylight_only = true`
- `thresholds.marginal_multiplier = 1.5`
- `thresholds.nope_multiplier = 1.8`
- `thresholds.sustained_fly_max = 18 mph`
- `thresholds.gust_fly_max = 28 mph`
- `thresholds.gust_spread_fly_max = 12 mph`
- `thresholds.rain_probability_fly_max = 85`
- `thresholds.temperature_min_c = 2`

These defaults bias outcomes toward short local sessions and reduce single-spike overreaction.

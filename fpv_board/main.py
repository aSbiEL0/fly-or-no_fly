#!/usr/bin/env python3
"""FPV Flight Board for Raspberry Pi + Waveshare e-paper."""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from functools import lru_cache
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

MS_PER_MPH = 0.44704
DISPLAY_STATE_VERSION = 2
STATUS_ICON_FILES = {
    "GREAT": "great.png",
    "OK": "ok.png",
    "RISKY": "risky.png",
    "NOPE": "nope.png",
}
NIGHT_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")


@dataclass
class HourlyPoint:
    timestamp: datetime
    wind_ms: float
    gust_ms: float
    rain_probability: float
    cloud_cover: float
    temp_c: float


class WeatherClient:
    def __init__(self, timeout_seconds: int, retry_attempts: int, retry_backoff_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self.session = requests.Session()

    def fetch(self, latitude: float, longitude: float, timezone: str) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "forecast_days": 2,
            "hourly": "windspeed_10m,windgusts_10m,winddirection_10m,precipitation_probability,temperature_2m,cloud_cover",
            "daily": "sunrise,sunset",
            "wind_speed_unit": "ms",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
        }
        url = "https://api.open-meteo.com/v1/forecast"

        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout_seconds)
                response.raise_for_status()
                data = response.json()
                self._validate_payload(data)
                return data
            except (requests.RequestException, ValueError, KeyError) as exc:
                last_error = exc
                logging.warning("Weather request attempt %s/%s failed: %s", attempt, self.retry_attempts, exc)
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)
        raise RuntimeError(f"Unable to fetch weather after retries: {last_error}")

    @staticmethod
    def _validate_payload(data: dict[str, Any]) -> None:
        hourly = data["hourly"]
        required_hourly = [
            "time",
            "windspeed_10m",
            "windgusts_10m",
            "winddirection_10m",
            "precipitation_probability",
            "temperature_2m",
            "cloud_cover",
        ]
        for key in required_hourly:
            if key not in hourly:
                raise KeyError(f"Missing hourly field: {key}")
        for key in ("sunrise", "sunset"):
            if key not in data["daily"]:
                raise KeyError(f"Missing daily field: {key}")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=800_000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.addHandler(logging.StreamHandler(sys.stdout))
    root.setLevel(logging.INFO)


def parse_hourly(data: dict[str, Any]) -> tuple[list[HourlyPoint], list[datetime], list[datetime]]:
    hourly = data["hourly"]
    timestamps = [datetime.fromisoformat(t) for t in hourly["time"]]
    points = [
        HourlyPoint(
            timestamp=timestamps[i],
            wind_ms=float(hourly["windspeed_10m"][i]),
            gust_ms=float(hourly["windgusts_10m"][i]),
            rain_probability=float(hourly["precipitation_probability"][i]),
            cloud_cover=float(hourly["cloud_cover"][i]),
            temp_c=float(hourly["temperature_2m"][i]),
        )
        for i in range(len(timestamps))
    ]
    sunrise = [datetime.fromisoformat(t) for t in data["daily"]["sunrise"]]
    sunset = [datetime.fromisoformat(t) for t in data["daily"]["sunset"]]
    return points, sunrise, sunset


def next_daylight_window(now: datetime, sunrise: list[datetime], sunset: list[datetime]) -> tuple[datetime, datetime] | None:
    for rise, set_ in zip(sunrise, sunset):
        if now <= set_:
            return rise, set_
    return None


def select_eval_points(
    points: list[HourlyPoint],
    now: datetime,
    daylight_window: tuple[datetime, datetime] | None,
    daylight_only: bool,
    hours_ahead: int,
) -> list[HourlyPoint]:
    end = now.timestamp() + (hours_ahead * 3600)
    selected = [p for p in points if now <= p.timestamp and p.timestamp.timestamp() <= end]
    if daylight_only and daylight_window:
        rise, set_ = daylight_window
        selected = [p for p in selected if rise <= p.timestamp <= set_]
    return selected


def mph_to_ms(v: float) -> float:
    return v * MS_PER_MPH


def status_from_score(score: int) -> str:
    if score <= 0:
        return "GREAT"
    if score == 1:
        return "OK"
    if score == 2:
        return "RISKY"
    return "NOPE"


def evaluate(points: list[HourlyPoint], cfg: dict[str, Any]) -> dict[str, Any]:
    thresholds = cfg["thresholds"]
    mult = float(thresholds.get("marginal_multiplier", 1.25))

    sustained_fly = mph_to_ms(float(thresholds["sustained_fly_max"]))
    gust_fly = mph_to_ms(float(thresholds["gust_fly_max"]))
    spread_fly = mph_to_ms(float(thresholds["gust_spread_fly_max"]))
    rain_fly = float(thresholds["rain_probability_fly_max"])
    temp_min = float(thresholds.get("temperature_min_c", -99))
    cloud_warn = float(thresholds.get("cloud_cover_warn", 100))

    if not points:
        return {
            "status": "NOPE",
            "reason": "Night / No daylight forecast",
            "worst": {},
            "trend": "No daylight forecast window",
            "score": 3,
        }

    worst = {
        "wind_ms": max(p.wind_ms for p in points),
        "gust_ms": max(p.gust_ms for p in points),
        "spread_ms": max((p.gust_ms - p.wind_ms) for p in points),
        "rain": max(p.rain_probability for p in points),
        "temp_min": min(p.temp_c for p in points),
        "cloud": max(p.cloud_cover for p in points),
    }

    checks: list[tuple[str, float, float, bool]] = [
        ("wind", worst["wind_ms"], sustained_fly, True),
        ("gusts", worst["gust_ms"], gust_fly, True),
        ("spread", worst["spread_ms"], spread_fly, True),
        ("rain", worst["rain"], rain_fly, True),
        ("temperature", worst["temp_min"], temp_min, False),
        ("cloud", worst["cloud"], cloud_warn, True),
    ]

    score = 0
    reasons: list[str] = []
    for metric, actual, threshold, higher_is_worse in checks:
        if metric == "cloud" and threshold >= 100:
            continue
        if higher_is_worse:
            if actual > threshold * mult:
                score = max(score, 3)
                reasons.append(f"{metric} high")
            elif actual > threshold:
                score = max(score, 2)
                reasons.append(f"{metric} borderline")
            elif actual > threshold * 0.85:
                score = max(score, 1)
        else:
            if actual < threshold:
                score = max(score, 2)
                reasons.append("cold")
            elif actual < threshold + 2:
                score = max(score, 1)

    trend = build_trend(points, cfg["forecast"]["trend_window_hours"])
    reason = reasons[0] if reasons else "conditions stable"
    return {"status": status_from_score(score), "reason": reason, "worst": worst, "trend": trend, "score": score}


def build_trend(points: list[HourlyPoint], window_hours: int) -> str:
    if len(points) < 2:
        return "No change forecasted"
    early = points[: min(window_hours, len(points))]
    later = points[min(window_hours, len(points)) :]
    if not later:
        return "No change forecasted"

    early_risk = sum((p.wind_ms + p.gust_ms * 0.7 + p.rain_probability * 0.06) for p in early) / len(early)
    later_risk = sum((p.wind_ms + p.gust_ms * 0.7 + p.rain_probability * 0.06) for p in later) / len(later)
    delta = later_risk - early_risk

    if delta > 1.2:
        when = later[0].timestamp.strftime("%H:%M")
        return f"Worsening after {when}"
    if delta < -1.2:
        return "Conditions improving later"
    return "No change forecasted"


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        logging.warning("Font not found at %s, using default PIL font", path)
        return ImageFont.load_default()



@lru_cache(maxsize=16)
def load_status_icon(status: str, diameter: int) -> Image.Image:
    icon_name = STATUS_ICON_FILES.get(status)
    if not icon_name:
        raise ValueError(f"Unknown status icon: {status}")

    icon_path = Path(__file__).resolve().parent / "assets" / "icons" / icon_name
    icon = Image.open(icon_path).convert("L").resize((diameter, diameter), Image.Resampling.LANCZOS)
    return icon


def draw_status_icon(canvas: Image.Image, status: str, center: tuple[int, int], radius: int) -> None:
    diameter = radius * 2
    icon = load_status_icon(status, diameter)
    cx, cy = center
    x = cx - radius
    y = cy - radius

    # Create a mask from dark pixels so only icon strokes are pasted as black.
    mask = icon.point(lambda p: 255 if p < 180 else 0, mode="1")
    canvas.paste(0, (x, y), mask)


def draw_colored_segments(
    draw_black: ImageDraw.ImageDraw,
    draw_red: ImageDraw.ImageDraw,
    y: int,
    segments: list[tuple[str, bool]],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    width: int,
) -> None:
    text_widths = [draw_black.textbbox((0, 0), text, font=font)[2] for text, _ in segments]
    x = max(8, (width - sum(text_widths)) // 2)
    for (text, is_red), seg_width in zip(segments, text_widths):
        target = draw_red if is_red else draw_black
        target.text((x, y), text, font=font, fill=0)
        x += seg_width


def is_worsening_trend(trend_text: str) -> bool:
    return trend_text.startswith("Worsening")


def _night_seed_key(now: datetime) -> str:
    # Keep the same image throughout the full overnight period.
    seed_date = now.date() if now.hour >= 12 else (now.date() - timedelta(days=1))
    return seed_date.isoformat()


def pick_night_image(now: datetime, cfg: dict[str, Any]) -> Path | None:
    image_dir_raw = cfg["display"].get("night_images_dir")
    if not image_dir_raw:
        return None

    image_dir = Path(str(image_dir_raw)).expanduser()
    if not image_dir.is_dir():
        logging.warning("Night image directory not found: %s", image_dir)
        return None

    candidates = sorted(
        p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in NIGHT_IMAGE_EXTENSIONS
    )
    if not candidates:
        logging.warning("No night images found in %s", image_dir)
        return None

    rng = random.Random(_night_seed_key(now))
    return candidates[rng.randrange(len(candidates))]


def render_night_image(path: Path, width: int, height: int) -> tuple[Image.Image, Image.Image]:
    source = Image.open(path).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
    black = Image.new("1", (width, height), 255)
    red = Image.new("1", (width, height), 255)

    black_pixels = black.load()
    red_pixels = red.load()
    source_pixels = source.load()
    for y in range(height):
        for x in range(width):
            r, g, b = source_pixels[x, y]
            brightness = (r + g + b) / 3
            if brightness < 110:
                black_pixels[x, y] = 0
            elif r > 140 and r > g * 1.15 and r > b * 1.15:
                red_pixels[x, y] = 0
    return black, red
        

def render_image(result: dict[str, Any], now: datetime, cfg: dict[str, Any]) -> tuple[Image.Image, Image.Image]:
    width = int(cfg["display"]["width"])
    height = int(cfg["display"]["height"])

    if result.get("status") == "NOPE" and result.get("reason") == "Night / No daylight forecast":
        night_image = pick_night_image(now, cfg)
        if night_image:
            return render_night_image(night_image, width, height)

    black = Image.new("1", (width, height), 255)
    red = Image.new("1", (width, height), 255)

    draw_b = ImageDraw.Draw(black)
    draw_r = ImageDraw.Draw(red)

    status_font = load_font(cfg["display"]["font_bold"], 56)
    metrics_font = load_font(cfg["display"]["font_bold"], 13)
    trend_font = load_font(cfg["display"]["font_bold"], 18)

    status = result["status"]
    status_draw = draw_r if (status == "NOPE" and cfg["display"].get("use_red_for_nope", True)) else draw_b

    icon_radius = 35
    icon_center_x = width - 8 - icon_radius
    icon_center_y = 42
    icon_left_edge = icon_center_x - icon_radius
    status_width = draw_b.textbbox((0, 0), status, font=status_font)[2]
    status_max_right = icon_left_edge - 12
    status_x = max(10, (status_max_right - status_width) // 2)

    status_draw.text((status_x, 8), status, font=status_font, fill=0)
    draw_status_icon(black, status, center=(icon_center_x, icon_center_y), radius=icon_radius)

    w = result.get("worst", {})
    wind_ms = float(w.get("wind_ms", 0.0))
    gust_ms = float(w.get("gust_ms", 0.0))
    rain = int(round(float(w.get("rain", 0.0))))
    temp_c = float(w.get("temp_min", 0.0))

    wind_red = wind_ms > 5.0
    gust_red = gust_ms >= 7.5
    rain_red = rain >= 90
    temp_red = temp_c <= 0.0

    draw_b.line((8, 90, width - 8, 90), fill=0, width=1)
    draw_b.line((8, 118, width - 8, 118), fill=0, width=1)

    metric_segments = [
        (f"Wind {wind_ms:0.1f} m/s", wind_red),
        (" | ", False),
        (f"Gust {gust_ms:0.1f}", gust_red),
        (" | ", False),
        (f"Rain {rain}%", rain_red),
        (" | ", False),
        (f"{temp_c:0.0f}°C", temp_red),
    ]
    draw_colored_segments(draw_b, draw_r, 99, metric_segments, metrics_font, width)

    trend_text = result["trend"]
    trend_color = draw_r if is_worsening_trend(trend_text) else draw_b
    trend_width = draw_b.textbbox((0, 0), trend_text, font=trend_font)[2]
    trend_x = max(8, (width - trend_width) // 2)
    trend_color.text((trend_x, 136), trend_text, font=trend_font, fill=0)
    return black, red


def rounded(value: float, step: float) -> float:
    if step <= 0:
        return value
    return round(value / step) * step


def build_display_state(result: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    tol = cfg["update"]["change_tolerance"]
    w = result.get("worst", {})
    return {
        "version": DISPLAY_STATE_VERSION,
        "status": result["status"],
        "reason": result["reason"],
        "trend": result["trend"],
        "wind": rounded(float(w.get("wind_ms", 0.0)), float(tol["wind_ms"])),
        "gust": rounded(float(w.get("gust_ms", 0.0)), float(tol["gust_ms"])),
        "rain": rounded(float(w.get("rain", 0.0)), float(tol["rain_pct"])),
        "temp": rounded(float(w.get("temp_min", 0.0)), float(tol["temp_c"])),
        "cloud": rounded(float(w.get("cloud", 0.0)), float(tol["cloud_pct"])),
    }


def load_previous_state(cache_file: Path) -> dict[str, Any] | None:
    if not cache_file.exists():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_state(cache_file: Path, state: dict[str, Any]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def states_equal(a: dict[str, Any] | None, b: dict[str, Any]) -> bool:
    return a == b


def show_on_epaper(black: Image.Image, red: Image.Image, model_path: str) -> None:
    mod_name, attr_name = model_path.rsplit(".", 1)
    module = __import__(mod_name, fromlist=[attr_name])
    epd_factory = getattr(module, attr_name)
    epd = epd_factory() if callable(epd_factory) else getattr(epd_factory, "EPD")()

    epd.init()
    epd.Clear()
    epd.display(epd.getbuffer(black), epd.getbuffer(red))
    epd.sleep()


def apply_preview_status(result: dict[str, Any], preview_status: str | None) -> dict[str, Any]:
    if not preview_status:
        return result
    preview_result = dict(result)
    preview_result["status"] = preview_status
    preview_result["reason"] = f"Preview mode: forced {preview_status}"
    preview_result["trend"] = "Preview render"
    return preview_result


def run(config_path: Path, dry_run: bool, preview_status: str | None, force_refresh: bool) -> int:
    cfg = load_config(config_path)
    setup_logging(Path(cfg["state"]["log_file"]))

    weather_client = WeatherClient(
        timeout_seconds=int(cfg["update"]["request_timeout_seconds"]),
        retry_attempts=int(cfg["update"]["retry_attempts"]),
        retry_backoff_seconds=float(cfg["update"]["retry_backoff_seconds"]),
    )

    loc = cfg["location"]
    now = datetime.now()
    raw = weather_client.fetch(float(loc["latitude"]), float(loc["longitude"]), str(loc["timezone"]))
    points, sunrise, sunset = parse_hourly(raw)

    daylight_window = next_daylight_window(now, sunrise, sunset)
    selected = select_eval_points(
        points,
        now,
        daylight_window,
        bool(cfg["forecast"].get("daylight_only", True)),
        int(cfg["forecast"]["hours_ahead"]),
    )

    result = evaluate(selected, cfg)
    result = apply_preview_status(result, preview_status)
    display_state = build_display_state(result, cfg)

    cache_file = Path(cfg["state"]["cache_file"])
    previous_state = load_previous_state(cache_file)
    changed = force_refresh or bool(preview_status) or (not states_equal(previous_state, display_state))

    black, red = render_image(result, now, cfg)

    if dry_run:
        print(json.dumps({"display_state": display_state, "changed": changed, "result": result}, indent=2, default=str))
        logging.info("Dry-run mode: display update skipped")
    else:
        if changed:
            show_on_epaper(black, red, str(cfg["display"]["model"]))
            logging.info("Display updated: %s (%s)", result["status"], result["reason"])
        else:
            logging.info("No meaningful change; skipped refresh")

    if not dry_run:
        save_state(cache_file, display_state)
    else:
        logging.info("Dry-run mode: state cache write skipped")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FPV Flight Board updater")
    parser.add_argument("--config", default="/opt/fpv-board/fpv_board/config.json", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Print computed output without touching display")
    parser.add_argument(
        "--preview-status",
        choices=["GREAT", "OK", "RISKY", "NOPE"],
        help="Force a rendered status so you can preview alternate board images immediately",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Refresh display even when change detection says nothing meaningful changed",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        raise SystemExit(run(Path(args.config), args.dry_run, args.preview_status, args.force_refresh))
    except Exception as exc:  # deliberate top-level guard for service reliability
        logging.exception("Fatal error: %s", exc)
        raise

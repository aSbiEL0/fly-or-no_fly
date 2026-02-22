#!/usr/bin/env python3
"""Clear the e-paper display and safely shut down the Raspberry Pi."""
from __future__ import annotations

import argparse
import logging
import subprocess
from pathlib import Path

from fpv_board.main import load_config, setup_logging


DEFAULT_CONFIG_PATH = Path("/opt/fpv-board/fpv_board/config.json")


def clear_display(model_path: str) -> None:
    mod_name, attr_name = model_path.rsplit(".", 1)
    module = __import__(mod_name, fromlist=[attr_name])
    epd_factory = getattr(module, attr_name)
    epd = epd_factory() if callable(epd_factory) else getattr(epd_factory, "EPD")()

    epd.init()
    epd.Clear()
    epd.sleep()


def shutdown_pi() -> None:
    subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clear the e-paper display and shut down the Pi")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to fpv_board config JSON")
    parser.add_argument("--dry-run", action="store_true", help="Skip hardware clear and shutdown command")
    parser.add_argument(
        "--clear-only",
        action="store_true",
        help="Clear display and exit without issuing shutdown",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(Path(args.config))
    setup_logging(Path(cfg["state"]["log_file"]))

    model_path = str(cfg["display"]["model"])

    if args.dry_run:
        logging.info("Dry-run: would clear display using model %s", model_path)
        if args.clear_only:
            logging.info("Dry-run: clear-only mode enabled; no shutdown command")
        else:
            logging.info("Dry-run: would run 'sudo shutdown -h now'")
        return 0

    clear_display(model_path)
    logging.info("Display cleared and put to sleep")

    if args.clear_only:
        logging.info("Clear-only mode enabled; skipping shutdown")
        return 0

    logging.info("Issuing system shutdown")
    shutdown_pi()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

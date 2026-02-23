#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def run(root: Path) -> int:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "status_log.csv").unlink(missing_ok=True)
    (data_dir / "index.json").unlink(missing_ok=True)

    state_file = data_dir / "state.json"
    state: dict = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    state["last_yearly_reset"] = "done"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset FPV yearly logs")
    parser.add_argument("--root", default="/opt/fpv-board")
    args = parser.parse_args()
    raise SystemExit(run(Path(args.root)))

# FPV Board Operations & Git-Based Updates

This document is for users running `/opt/fpv-board` as a **git checkout** on the Pi.

## Recommended update flow (after each merge to `main`)

Run on the Pi:

```bash
cd /opt/fpv-board
./scripts/update_pi.sh
```

If you occasionally make local edits directly on the Pi, use:

```bash
cd /opt/fpv-board
./scripts/update_pi.sh --auto-stash
```

The updater script will:

- verify `/opt/fpv-board` is a git repository,
- fetch and fast-forward from `origin/main`,
- reinstall Python requirements,
- reload and restart board timers.

## Manual fallback (git-only)

If needed, run the equivalent manual commands:

```bash
cd /opt/fpv-board
git fetch origin
git checkout main
git pull --ff-only origin main
. .venv/bin/activate
pip install -r requirements.txt
sudo systemctl daemon-reload
sudo systemctl restart fpv-board.timer weekly-report.timer yearly-log-reset.timer
```

## Related docs

- Setup/install reference: [`docs/README_SETUP.md`](README_SETUP.md)
- Weekly reporting details: [`docs/wiki/Weekly-Reporting.md`](wiki/Weekly-Reporting.md)
- Decision-process reference: [`docs/wiki/Status-Decision-Process.md`](wiki/Status-Decision-Process.md)

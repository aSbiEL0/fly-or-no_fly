#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/opt/fpv-board"
BRANCH="main"
AUTO_STASH=0

usage() {
  cat <<'EOF'
Usage: update_pi.sh [--root <path>] [--branch <name>] [--auto-stash]

Updates the deployed FPV board checkout and restarts timers.

Options:
  --root <path>     Deployment root (default: /opt/fpv-board)
  --branch <name>   Branch to pull (default: main)
  --auto-stash      Stash local tracked/untracked changes before pulling
  -h, --help        Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      ROOT_DIR="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --auto-stash)
      AUTO_STASH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$ROOT_DIR/.git" ]]; then
  echo "Error: $ROOT_DIR is not a git checkout. Use README Option B (rsync) or clone repo first." >&2
  exit 1
fi

cd "$ROOT_DIR"

STASHED=0
if [[ -n "$(git status --porcelain)" ]]; then
  if [[ "$AUTO_STASH" -eq 1 ]]; then
    git stash push --include-untracked --message "auto-stash before update_pi.sh"
    STASHED=1
  else
    echo "Working tree has local changes." >&2
    echo "Commit/stash them first, or rerun with --auto-stash." >&2
    exit 1
  fi
fi

git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

"$ROOT_DIR/.venv/bin/pip" install -r requirements.txt

sudo systemctl daemon-reload
sudo systemctl restart fpv-board.timer weekly-report.timer yearly-log-reset.timer

if [[ "$STASHED" -eq 1 ]]; then
  echo "Update complete. Local changes were stashed. Reapply with: git stash pop"
else
  echo "Update complete."
fi

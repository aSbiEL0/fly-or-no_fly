# Raspberry Pi FPV Flight Board


## Hardware

- **Raspberry Pi**: Zero 2 W running Raspberry Pi OS Lite (Trixie) – other models with a 40‑pin header should also work.
- **Display**: Waveshare 2.15″ e‑Paper HAT+ (B), red/black/white tri‑colour (296×160).
- **Storage**: microSD card (8 GB or larger).
- **Power**: 5 V micro‑USB supply or power bank.
- **Optional**: case or stand, soldered GPIO header.
## Install

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git rsync \
  libopenjp2-7 libtiff6 libjpeg62-turbo fonts-dejavu-core python3-lgpio
sudo raspi-config nonint do_spi 0
sudo reboot
```

```bash
sudo mkdir -p /opt/fpv-board
sudo chown -R pi:pi /opt/fpv-board
rsync -av --delete ./ /opt/fpv-board/
cd /opt/fpv-board
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Install Waveshare library:

```bash
cd /opt/fpv-board
[ -d waveshare-lib ] || [ -d e-Paper ] || git clone https://github.com/waveshare/e-Paper.git waveshare-lib
```

## Configure

1. Edit `/opt/fpv-board/fpv_board/config.json`.
2. Copy email template and fill SMTP app password:

```bash
cp /opt/fpv-board/.env.example /opt/fpv-board/.env
nano /opt/fpv-board/.env
```

## systemd setup

```bash
sudo cp /opt/fpv-board/systemd/fpv-board.service /etc/systemd/system/
sudo cp /opt/fpv-board/systemd/fpv-board.timer /etc/systemd/system/
sudo cp /opt/fpv-board/systemd/weekly-report.service /etc/systemd/system/
sudo cp /opt/fpv-board/systemd/weekly-report.timer /etc/systemd/system/
sudo cp /opt/fpv-board/systemd/yearly-log-reset.service /etc/systemd/system/
sudo cp /opt/fpv-board/systemd/yearly-log-reset.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fpv-board.timer weekly-report.timer yearly-log-reset.timer
```

## Manual run

```bash
cd /opt/fpv-board
. .venv/bin/activate
python -m fpv_board.main --config /opt/fpv-board/fpv_board/config.json --dry-run
python /opt/fpv-board/scripts/weekly_report.py --config /opt/fpv-board/fpv_board/config.json --dotenv /opt/fpv-board/.env --force
```

## Update the Pi after each merge (no manual file copying)

Use one of these repeatable workflows.

### Fastest day-to-day command (recommended)

Run the included updater script on the Pi:

```bash
cd /opt/fpv-board
./scripts/update_pi.sh
```

If you sometimes make local edits on the Pi, use:

```bash
cd /opt/fpv-board
./scripts/update_pi.sh --auto-stash
```

The script will:

- verify `/opt/fpv-board` is a git checkout,
- fetch + fast-forward pull from `origin/main`,
- reinstall Python requirements,
- reload and restart board timers.

### Option A: Pi pulls directly from GitHub (manual commands)

One-time setup on the Pi (if `/opt/fpv-board` is not already a git clone):

```bash
sudo rm -rf /opt/fpv-board
sudo git clone <YOUR_REPO_URL> /opt/fpv-board
sudo chown -R pi:pi /opt/fpv-board
cd /opt/fpv-board
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install -r requirements.txt
```

After each merge to `main`, update with:

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

### Option B: push from your laptop to the Pi with one command

If you prefer to keep the Pi as a deployed copy instead of a git checkout:

```bash
rsync -av --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'data' \
  --exclude '.env' \
  ./ pi@<PI_HOST>:/opt/fpv-board/
ssh pi@<PI_HOST> 'cd /opt/fpv-board && . .venv/bin/activate && pip install -r requirements.txt && sudo systemctl daemon-reload && sudo systemctl restart fpv-board.timer weekly-report.timer yearly-log-reset.timer'
```

This gives you a reliable, "single update step" after each merge.

## Documentation

- Detailed operational documentation is in `docs/wiki/Weekly-Reporting.md` (ready to publish to GitHub Wiki).
- Full status decision reference is in `docs/wiki/Status-Decision-Process.md` (comprehensive scoring and status flow record).

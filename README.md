# Raspberry Pi FPV Flight Board

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

## Documentation

Detailed operational documentation is in `docs/wiki/Weekly-Reporting.md` (ready to publish to GitHub Wiki).

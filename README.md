# Raspberry Pi FPV Flight Board (Waveshare 2.15" tri-colour)

This project fetches Open-Meteo forecast data, evaluates **daylight-only** flying conditions for a DJI Neo profile, then renders a compact status board to a Waveshare `2.15inch e-Paper HAT+` display (`296x160`).

## Folder structure
- `fpv_board/main.py` - complete updater application (config load, API client, scoring, drawing, caching).
- `fpv_board/config.json` - editable runtime config (location, units, thresholds, update tolerances).
- `requirements.txt` - Python dependencies (`requests`, `Pillow`).
- `systemd/fpv-board.service` - one-shot unit that runs updater as user `pi`.
- `systemd/fpv-board.timer` - hourly schedule trigger.

## Install (Raspberry Pi OS Trixie/Bookworm, Python 3.11+)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git libopenjp2-7 libtiff6 libjpeg62-turbo
sudo raspi-config nonint do_spi 0
sudo reboot
```

After reboot, reconnect and continue:

```bash
ls /dev/spidev0.0 /dev/spidev0.1
```

Create install directory and virtual environment:

```bash
sudo mkdir -p /opt/fpv-board
sudo chown -R pi:pi /opt/fpv-board
rsync -av --delete ./ /opt/fpv-board/
cd /opt/fpv-board
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Install Waveshare Python e-Paper library:

```bash
cd /opt/fpv-board
git clone https://github.com/waveshare/e-Paper.git waveshare-lib
pip install RPi.GPIO spidev gpiozero
export PYTHONPATH="/opt/fpv-board/waveshare-lib/RaspberryPi_JetsonNano/python/lib:${PYTHONPATH}"
```

To make `PYTHONPATH` persistent for systemd, add to service file:

```ini
Environment=PYTHONPATH=/opt/fpv-board/waveshare-lib/RaspberryPi_JetsonNano/python/lib
```

## Wiring
Using default 40-pin HAT mapping (SPI + BCM control):
- MOSI: GPIO10 (pin 19)
- SCLK: GPIO11 (pin 23)
- CS: GPIO8 (pin 24)
- DC: GPIO25 (pin 22)
- RST: GPIO17 (pin 11)
- BUSY: GPIO24 (pin 18)
- 3.3V and GND from header

## Configure
Edit `/opt/fpv-board/fpv_board/config.json`:
- `location` for saved site.
- `thresholds` for risk logic (configured in mph internally converted to m/s).
- `forecast.daylight_only = true` to only evaluate sunrise/sunset window.
- `update.change_tolerance` controls anti-ghosting redraw threshold.

## Run manually
Dry-run (no display write):

```bash
cd /opt/fpv-board
. .venv/bin/activate
python -m fpv_board.main --config /opt/fpv-board/fpv_board/config.json --dry-run
```

Live update:

```bash
python -m fpv_board.main --config /opt/fpv-board/fpv_board/config.json
```

Preview alternate board renders immediately (without waiting for weather/condition changes):

```bash
python -m fpv_board.main --config /opt/fpv-board/fpv_board/config.json --preview-status NOPE --force-refresh
```

You can use `--preview-status` with `GREAT`, `OK`, `MARGINAL`, or `NOPE` to test each visual state.

## systemd setup

```bash
sudo cp /opt/fpv-board/systemd/fpv-board.service /etc/systemd/system/
sudo cp /opt/fpv-board/systemd/fpv-board.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fpv-board.timer
sudo systemctl start fpv-board.service
```

Check logs:

```bash
journalctl -u fpv-board.service -n 100 --no-pager
```

## Quick test checklist
1. `python -m fpv_board.main --dry-run` returns JSON with `status`, `reason`, and `changed`.
2. First live run updates display; second live run skips refresh if no meaningful changes.
3. At night, status returns `NOPE` with `Night / No daylight forecast`.
4. Timer runs hourly: `systemctl list-timers | grep fpv-board`.

## Common fixes
- **SPI not enabled**: run `sudo raspi-config nonint do_spi 0` and reboot.
- **Wrong pins / BUSY stuck**: verify HAT seated correctly and BUSY maps to GPIO24.
- **Font missing**: defaults to PIL font automatically; adjust `font_*` paths in config if needed.
- **Import error for Waveshare module**: confirm `PYTHONPATH` includes Waveshare `python/lib` directory.

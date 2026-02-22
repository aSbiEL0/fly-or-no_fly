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
sudo apt install -y python3 python3-venv python3-pip git rsync \
  libopenjp2-7 libtiff6 libjpeg62-turbo fonts-dejavu-core \
  python3-lgpio
sudo raspi-config nonint do_spi 0
sudo reboot
```

After reboot, reconnect and continue:

```bash
ls /dev/spidev0.0 /dev/spidev0.1
# If either file is missing, SPI is not enabled correctly.
```

Create install directory and virtual environment:

```bash
sudo mkdir -p /opt/fpv-board
sudo chown -R pi:pi /opt/fpv-board
rsync -av --delete ./ /opt/fpv-board/
cd /opt/fpv-board
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Verify lgpio comes from apt/system packages inside this venv
python - <<'PY'
import lgpio
print("lgpio import OK:", lgpio.__file__)
PY
```

Install Waveshare Python e-Paper library:

```bash
cd /opt/fpv-board
# Clone only if the folder is not already present in your checkout
[ -d waveshare-lib ] || git clone https://github.com/waveshare/e-Paper.git waveshare-lib

# Required in any interactive shell before running fpv_board.main manually
export PYTHONPATH="/opt/fpv-board/waveshare-lib/RaspberryPi_JetsonNano/python/lib:${PYTHONPATH}"

# Quick verification: should print a module path, not an import error
python - <<'PY2'
import waveshare_epd
print("waveshare_epd import OK:", waveshare_epd.__file__)
PY2
```

To make `PYTHONPATH` persistent for systemd, add to service file:

```ini
Environment=PYTHONPATH=/opt/fpv-board/waveshare-lib/RaspberryPi_JetsonNano/python/lib
Environment=GPIOZERO_PIN_FACTORY=lgpio
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
- `display.night_images_dir` (optional) points to a directory of night images (`.png/.jpg/...`); one image is randomly picked per night and held until morning.

## Run manually
Dry-run (no display write):

```bash
cd /opt/fpv-board
. .venv/bin/activate
python -m fpv_board.main --config /opt/fpv-board/fpv_board/config.json --dry-run
```

Live update:

```bash
# If this is a new shell, re-export PYTHONPATH first
export PYTHONPATH="/opt/fpv-board/waveshare-lib/RaspberryPi_JetsonNano/python/lib:${PYTHONPATH}"
python -m fpv_board.main --config /opt/fpv-board/fpv_board/config.json
```

Preview alternate board renders immediately (without waiting for weather/condition changes):

```bash
python -m fpv_board.main --config /opt/fpv-board/fpv_board/config.json --preview-status NOPE --force-refresh
```

You can use `--preview-status` with `GREAT`, `OK`, `RISKY`, or `NOPE` to test each visual state.


Clear the display and shut down safely:

```bash
python -m fpv_board.shutdown --config /opt/fpv-board/fpv_board/config.json
```

Use `--clear-only` to clear the panel without powering down, or `--dry-run` to verify behavior without touching hardware.

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
3. At night, status returns `NOPE` with `Night / No daylight forecast` and, if `display.night_images_dir` contains images, one random image is shown for the whole night.
4. Timer runs hourly: `systemctl list-timers | grep fpv-board`.

## Common fixes
- **SPI not enabled**: run `sudo raspi-config nonint do_spi 0` and reboot.
- **Do not run `pip install lgpio`**: this project uses the Raspberry Pi OS package `python3-lgpio`; pip builds often fail and are unnecessary here.
- **Wrong pins / BUSY stuck**: verify HAT seated correctly and BUSY maps to GPIO24.
- **Font missing**: defaults to PIL font automatically; adjust `font_*` paths in config if needed.
- **Import error for Waveshare module**: confirm `PYTHONPATH` includes Waveshare `python/lib` directory in the current shell, then run `python -c "import waveshare_epd; print(waveshare_epd.__file__)"`.
- **`No module named lgpio` in venv**: recreate venv with `python3 -m venv --system-site-packages .venv` so apt package `python3-lgpio` is visible. Also remove pip-installed swig wrappers if present (`pip uninstall -y swig`), because they can shadow `/usr/bin/swig` during builds.
- **`Failed to add edge detection`**: ensure no duplicate process is already using GPIO, then set `GPIOZERO_PIN_FACTORY=lgpio` (in shell or systemd service) and rerun.

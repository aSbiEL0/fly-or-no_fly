# Raspberry Pi FPV Flight Board

If you were looking for the split README sections, they are now separated into dedicated docs:

- **Setup & Installation**: [`docs/README_SETUP.md`](docs/README_SETUP.md)
- **Operations & Updates**: [`docs/README_OPERATIONS.md`](docs/README_OPERATIONS.md)
- **Maintainer local file sync (repair workflow)**: [`docs/LOCAL_PI_FILE_SYNC.md`](docs/LOCAL_PI_FILE_SYNC.md)
- **Weekly report details**: [`docs/wiki/Weekly-Reporting.md`](docs/wiki/Weekly-Reporting.md)
- **Status decision reference**: [`docs/wiki/Status-Decision-Process.md`](docs/wiki/Status-Decision-Process.md)

## Quick start

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git rsync \
  libopenjp2-7 libtiff6 libjpeg62-turbo fonts-dejavu-core python3-lgpio
```

Then follow the full setup guide in [`docs/README_SETUP.md`](docs/README_SETUP.md).

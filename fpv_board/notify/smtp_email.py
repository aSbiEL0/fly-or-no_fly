from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


class SmtpEmailClient:
    def __init__(self, host: str = "smtp.gmail.com", port: int = 587) -> None:
        self.host = host
        self.port = port

    def send(self, subject: str, body: str) -> None:
        user = os.environ.get("SMTP_USER", "")
        password = os.environ.get("SMTP_APP_PASSWORD", "")
        email_to = os.environ.get("EMAIL_TO", "")
        from_name = os.environ.get("EMAIL_FROM_NAME", "Pi Drone Dash")
        if not user or not password or not email_to:
            raise RuntimeError("Missing SMTP_USER / SMTP_APP_PASSWORD / EMAIL_TO environment variables")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{user}>"
        msg["To"] = email_to
        msg.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)

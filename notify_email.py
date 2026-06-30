"""Send operator notifications: Gmail -> iCloud via SMTP App Password."""
from __future__ import annotations

import mimetypes
import os
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable


def load_env():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _attachment_paths(attachments: Iterable[str] | None) -> list[Path]:
    paths: list[Path] = []
    for raw_path in attachments or []:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(str(path))
        paths.append(path)
    return paths


def _attachment_part(path: Path) -> MIMEBase:
    content_type, encoding = mimetypes.guess_type(str(path))
    if content_type is None or encoding is not None:
        content_type = "application/octet-stream"
    maintype, subtype = content_type.split("/", 1)
    part = MIMEBase(maintype, subtype)
    part.set_payload(path.read_bytes())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=path.name)
    return part


def _build_message(subject: str, body: str, sender: str, mail_to: str, attachments: list[Path]):
    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))
        for path in attachments:
            msg.attach(_attachment_part(path))
    else:
        msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = mail_to
    return msg


def send_email(subject, body, mail_to=None, attachments=None):
    load_env()
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    mail_to = (mail_to or os.environ.get("EMAIL_TO", "abdul487417@icloud.com")).strip()

    if not gmail_user or not gmail_pass:
        raise RuntimeError(
            "Missing GMAIL_USER or GMAIL_APP_PASSWORD in c:\\Users\\abdul\\.jules\\.env"
        )

    attachment_paths = _attachment_paths(attachments)
    msg = _build_message(subject, body, gmail_user, mail_to, attachment_paths)

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_use_ssl = os.environ.get("SMTP_USE_SSL", "1").strip().lower() in {"1", "true", "yes"}

    if smtp_use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, [mail_to], msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, [mail_to], msg.as_string())

    return {
        "from": gmail_user,
        "to": mail_to,
        "subject": subject,
        "attachments": [str(path) for path in attachment_paths],
    }


if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "Jules Bridge update"
    body = sys.argv[2] if len(sys.argv) > 2 else "Test message from Jules bridge."
    attachments = sys.argv[3:]
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        body = sys.stdin.read()
        attachments = []
    result = send_email(subject, body, attachments=attachments)
    print(
        f"Sent: {result['from']} -> {result['to']}: "
        f"{result['subject']} ({len(result['attachments'])} attachments)"
    )

"""Send operator notifications: Gmail -> iCloud via SMTP App Password."""
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path


def load_env():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def send_email(subject, body):
    load_env()
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    mail_to = os.environ.get("EMAIL_TO", "abdul487417@icloud.com").strip()

    if not gmail_user or not gmail_pass:
        raise RuntimeError(
            "Missing GMAIL_USER or GMAIL_APP_PASSWORD in c:\\Users\\abdul\\.jules\\.env"
        )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = mail_to

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(gmail_user, gmail_pass)
        smtp.sendmail(gmail_user, [mail_to], msg.as_string())

    return {"from": gmail_user, "to": mail_to, "subject": subject}


if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "Jules Bridge update"
    body = sys.argv[2] if len(sys.argv) > 2 else "Test message from Jules bridge."
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        body = sys.stdin.read()
    result = send_email(subject, body)
    print(f"Sent: {result['from']} -> {result['to']}: {result['subject']}")

"""Send operator notifications: Gmail -> iCloud via SMTP App Password."""
import os
import smtplib
import sys
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


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


def send_email(subject, body, mail_to=None, attachments=None):
    load_env()
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    mail_to = (mail_to or os.environ.get("EMAIL_TO", "abdul487417@icloud.com")).strip()

    if not gmail_user or not gmail_pass:
        raise RuntimeError(
            "Missing GMAIL_USER or GMAIL_APP_PASSWORD in c:\\Users\\abdul\\.jules\\.env"
        )

    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))
        for path_str in attachments:
            path = Path(path_str)
            if not path.is_file():
                continue

            ctype, encoding = mimetypes.guess_type(str(path))
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            with open(path, 'rb') as f:
                if maintype == 'image':
                    img = MIMEImage(f.read(), _subtype=subtype)
                    img.add_header('Content-Disposition', 'attachment', filename=path.name)
                    msg.attach(img)
                else:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename=path.name)
                    msg.attach(part)
    else:
        msg = MIMEText(body, "plain", "utf-8")

    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = mail_to

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

    return {"from": gmail_user, "to": mail_to, "subject": subject, "attachments": attachments or []}


if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "Jules Bridge update"
    body = sys.argv[2] if len(sys.argv) > 2 else "Test message from Jules bridge."
    attachments = sys.argv[3:] if len(sys.argv) > 3 else None

    if len(sys.argv) == 1 and not sys.stdin.isatty():
        body = sys.stdin.read()

    result = send_email(subject, body, attachments=attachments)
    print(f"Sent: {result['from']} -> {result['to']}: {result['subject']} with {len(result['attachments'])} attachments")

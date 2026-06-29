import sys
import notify_email as email_service
from notify_email import load_env

def send_alert():
    try:
        load_env()
        subject = "[JULES-UPDATE] Context Bleed Corrected - Focus on Box Boodle AI"
        with open("jules_inbox/JULES_RESPONSE.md", "r") as f:
            body = f.read()
        print(f"Sending email with subject: {subject}")
        print(f"Body: {body[:100]}...")
        # notify_email uses str for to_email, not list
        email_service.send_email(subject, body, "abdul@boodle.ai")
        print("Email dispatched successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    send_alert()

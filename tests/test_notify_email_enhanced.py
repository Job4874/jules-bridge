import os
import tempfile
import unittest
from unittest.mock import patch

import notify_email


class TestNotifyEmailAttachments(unittest.TestCase):
    def _env(self):
        return {
            "GMAIL_USER": "sender@example.test",
            "GMAIL_APP_PASSWORD": "app-password",
            "EMAIL_TO": "operator@example.test",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_PORT": "465",
            "SMTP_USE_SSL": "1",
        }

    @patch("notify_email.smtplib.SMTP_SSL")
    @patch("notify_email.load_env")
    def test_send_email_attaches_existing_file(self, _mock_load_env, mock_smtp_ssl):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as handle:
            handle.write(b"hello screenshot evidence")
            attachment = handle.name

        try:
            with patch.dict(os.environ, self._env(), clear=True):
                result = notify_email.send_email(
                    "Status",
                    "Body",
                    attachments=[attachment],
                )

            smtp = mock_smtp_ssl.return_value.__enter__.return_value
            smtp.login.assert_called_once_with("sender@example.test", "app-password")
            smtp.sendmail.assert_called_once()
            message = smtp.sendmail.call_args.args[2]

            self.assertEqual(result["attachments"], [attachment])
            self.assertIn("Content-Type: multipart/mixed", message)
            self.assertIn(os.path.basename(attachment), message)
            self.assertIn("aGVsbG8gc2NyZWVuc2hvdCBldmlkZW5jZQ==", message)
        finally:
            os.unlink(attachment)

    @patch("notify_email.smtplib.SMTP_SSL")
    @patch("notify_email.load_env")
    def test_send_email_rejects_missing_attachment_before_smtp(self, _mock_load_env, mock_smtp_ssl):
        missing = os.path.join(tempfile.gettempdir(), "missing-jules-attachment.png")
        if os.path.exists(missing):
            os.unlink(missing)

        with patch.dict(os.environ, self._env(), clear=True):
            with self.assertRaises(FileNotFoundError):
                notify_email.send_email("Status", "Body", attachments=[missing])

        mock_smtp_ssl.assert_not_called()


if __name__ == "__main__":
    unittest.main()

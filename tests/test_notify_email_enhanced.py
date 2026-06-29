import unittest
from unittest.mock import patch, MagicMock
import notify_email
import os
import base64

class TestNotifyEmail(unittest.TestCase):
    @patch('smtplib.SMTP_SSL')
    @patch('notify_email.load_env')
    @patch('os.environ.get')
    def test_send_email_with_attachments(self, mock_env_get, mock_load_env, mock_smtp_ssl):
        # Setup mocks
        mock_env_get.side_effect = lambda k, d=None: {
            'GMAIL_USER': 'test@gmail.com',
            'GMAIL_APP_PASSWORD': 'password',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '465',
            'SMTP_USE_SSL': '1'
        }.get(k, d)

        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp

        # Create a dummy attachment
        test_file = 'test_attachment_unit.txt'
        with open(test_file, 'w') as f:
            f.write('hello world')

        try:
            result = notify_email.send_email(
                subject='Test Subject',
                body='Test Body',
                mail_to='recipient@example.com',
                attachments=[test_file]
            )

            self.assertEqual(result['subject'], 'Test Subject')
            self.assertEqual(len(result['attachments']), 1)

            # Verify SMTP calls
            mock_smtp.login.assert_called_with('test@gmail.com', 'password')
            self.assertTrue(mock_smtp.sendmail.called)

            # Verify message structure
            args, kwargs = mock_smtp.sendmail.call_args
            msg_string = args[2]
            self.assertIn('Content-Type: multipart/mixed', msg_string)
            self.assertIn(test_file, msg_string)
            self.assertIn(base64.b64encode(b'hello world').decode(), msg_string)

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == '__main__':
    unittest.main()

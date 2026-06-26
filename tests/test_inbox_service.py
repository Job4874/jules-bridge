"""Unit tests for modules/inbox_service.py.

Tests at the module interface level — no Flask or HTTP involved.
"""

import os
import tempfile
import unittest


class TestInboxRead(unittest.TestCase):
    def setUp(self):
        from modules import inbox_service
        self.svc = inbox_service

    def test_read_returns_content(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "OPERATOR_RESPONSE.md")
            with open(path, "w") as f:
                f.write("hello from operator")
            message, status = self.svc.inbox_read(file="OPERATOR_RESPONSE.md", inbox_dir=d)
            self.assertEqual(status, 200)
            self.assertEqual(message["content"], "hello from operator")
            self.assertEqual(message["file"], "OPERATOR_RESPONSE.md")

    def test_read_missing_returns_404(self):
        with tempfile.TemporaryDirectory() as d:
            message, status = self.svc.inbox_read(file="MISSING.md", inbox_dir=d)
            self.assertEqual(status, 404)
            self.assertIn("not found", message["error"])
            self.assertIn("inbox_files", message)

    def test_read_default_filename(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "OPERATOR_RESPONSE.md")
            with open(path, "w") as f:
                f.write("default")
            message, status = self.svc.inbox_read(file=None, inbox_dir=d)
            self.assertEqual(status, 200)
            self.assertEqual(message["content"], "default")

    def test_read_lists_available_on_404(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "OTHER.md"), "w") as f:
                f.write("x")
            message, status = self.svc.inbox_read(file="MISSING.md", inbox_dir=d)
            self.assertEqual(status, 404)
            self.assertIn("OTHER.md", message["inbox_files"])

    def test_read_path_traversal_safe_basename(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "safe.md"), "w") as f:
                f.write("safe")
            # Attempt path traversal via ../../etc/passwd
            message, status = self.svc.inbox_read(
                file="../../etc/passwd", inbox_dir=d
            )
            # Should be 404 — safe because we only read basename
            self.assertEqual(status, 404)


class TestInboxWrite(unittest.TestCase):
    def setUp(self):
        from modules import inbox_service
        self.svc = inbox_service

    def test_write_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.svc.inbox_write("Jules was here", file="JULES_RESPONSE.md", inbox_dir=d)
            self.assertEqual(result["status"], "success")
            path = os.path.join(d, "JULES_RESPONSE.md")
            self.assertTrue(os.path.exists(path))
            with open(path, "r") as f:
                self.assertEqual(f.read(), "Jules was here")

    def test_write_default_filename(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.svc.inbox_write("content", file=None, inbox_dir=d)
            self.assertEqual(result["file"], "JULES_RESPONSE.md")

    def test_write_empty_content(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.svc.inbox_write("", file="out.md", inbox_dir=d)
            self.assertEqual(result["status"], "success")

    def test_write_creates_inbox_dir(self):
        with tempfile.TemporaryDirectory() as base:
            d = os.path.join(base, "new_inbox")
            result = self.svc.inbox_write("hi", inbox_dir=d)
            self.assertTrue(os.path.isdir(d))


if __name__ == "__main__":
    unittest.main()

"""Unit tests for modules/academic_workflow.py."""

import tempfile
import unittest
from pathlib import Path

from modules.academic_workflow import AcademicWorkflowConnector


class TestAcademicWorkflow(unittest.TestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.connector = AcademicWorkflowConnector(acc_dir=Path(self.tmp_dir.name))

    def tearDown(self):  # pylint: disable=invalid-name
        try:
            self.tmp_dir.cleanup()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def test_validate_blank_submission_rejected(self):
        payload = {"content": "", "file_path": ""}
        res = self.connector.validate_submission_safety(payload)
        self.assertFalse(res["safe"])
        self.assertIn("blank submission", res["reason"])

    def test_validate_unanswered_fields_rejected(self):
        payload = {"content": "Answer 1", "unanswered_fields": ["Question 2"]}
        res = self.connector.validate_submission_safety(payload)
        self.assertFalse(res["safe"])
        self.assertIn("unanswered fields", res["reason"])

    def test_validate_valid_submission_checkpoint(self):
        payload = {"content": "Complete essay content", "unanswered_fields": []}
        res = self.connector.validate_submission_safety(payload)
        self.assertTrue(res["safe"])
        self.assertTrue(res["checkpoint_required"])

    def test_record_attempt(self):
        rec = self.connector.record_attempt("CS101_Quiz1", {"score": 100})
        self.assertTrue(rec.exists())


if __name__ == "__main__":
    unittest.main()

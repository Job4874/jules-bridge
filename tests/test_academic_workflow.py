"""Unit tests for modules/academic_workflow.py.

Tests course_id isolation enforcement, submission safety, and attempt recording.
"""

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

    # ----- helpers -----
    def _create_evidence(self, folder_name: str) -> Path:
        """Create a fake evidence directory with a PROOF file."""
        evidence_dir = Path(self.tmp_dir.name) / "evidence" / folder_name
        evidence_dir.mkdir(parents=True, exist_ok=True)
        proof = evidence_dir / "PROOF-test.md"
        proof.write_text("# Test proof", encoding="utf-8")
        return proof

    # ===== Course ID Isolation Tests =====

    def test_discover_requires_course_id(self):
        """Calling discover_assignments without course_id MUST return empty list."""
        self._create_evidence("acc-CS101-quiz1")
        result = self.connector.discover_assignments(course_id=None)
        self.assertEqual(result, [])

    def test_wrong_course_isolation(self):
        """Querying CS101 must NOT return MATH200 evidence."""
        self._create_evidence("acc-CS101-quiz1")
        self._create_evidence("acc-MATH200-hw3")

        cs101 = self.connector.discover_assignments(course_id="CS101")
        math200 = self.connector.discover_assignments(course_id="MATH200")

        cs101_ids = [a["assignment_id"] for a in cs101]
        math200_ids = [a["assignment_id"] for a in math200]

        self.assertIn("acc-CS101-quiz1", cs101_ids)
        self.assertNotIn("acc-MATH200-hw3", cs101_ids)
        self.assertIn("acc-MATH200-hw3", math200_ids)
        self.assertNotIn("acc-CS101-quiz1", math200_ids)

    def test_substring_no_false_match(self):
        """CS10 must NOT match CS101 evidence (exact token matching)."""
        self._create_evidence("acc-CS101-quiz1")
        self._create_evidence("acc-CS10-quiz2")

        cs10 = self.connector.discover_assignments(course_id="CS10")
        cs10_ids = [a["assignment_id"] for a in cs10]

        self.assertIn("acc-CS10-quiz2", cs10_ids)
        self.assertNotIn("acc-CS101-quiz1", cs10_ids,
                         "CS10 must NOT match CS101 — substring false match detected")

    def test_submission_requires_course_id(self):
        """Submission without course_id MUST be rejected as unsafe."""
        payload = {"content": "Complete essay content", "unanswered_fields": []}
        res = self.connector.validate_submission_safety(payload)
        self.assertFalse(res["safe"])
        self.assertIn("course_id", res["reason"])

    # ===== Original Safety Tests (updated for course_id requirement) =====

    def test_validate_blank_submission_rejected(self):
        """Blank content with valid course_id is still rejected."""
        payload = {"course_id": "CS101", "content": "", "file_path": ""}
        res = self.connector.validate_submission_safety(payload)
        self.assertFalse(res["safe"])
        self.assertIn("blank submission", res["reason"])

    def test_validate_unanswered_fields_rejected(self):
        """Unanswered fields with valid course_id are still rejected."""
        payload = {"course_id": "CS101", "content": "Answer 1", "unanswered_fields": ["Question 2"]}
        res = self.connector.validate_submission_safety(payload)
        self.assertFalse(res["safe"])
        self.assertIn("unanswered fields", res["reason"])

    def test_validate_valid_submission_checkpoint(self):
        """Complete submission with valid course_id passes safety and requires checkpoint."""
        payload = {"course_id": "CS101", "content": "Complete essay content", "unanswered_fields": []}
        res = self.connector.validate_submission_safety(payload)
        self.assertTrue(res["safe"])
        self.assertTrue(res["checkpoint_required"])
        self.assertEqual(res["course_id"], "CS101")

    def test_record_attempt(self):
        """Attempt records are persisted to disk."""
        rec = self.connector.record_attempt("CS101_Quiz1", {"score": 100})
        self.assertTrue(rec.exists())

    def test_discover_with_valid_course_id(self):
        """Discover returns matching evidence when course_id is provided."""
        self._create_evidence("acc-CS101-quiz1")
        result = self.connector.discover_assignments(course_id="CS101")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["course_id"], "CS101")

    def test_course_match_case_insensitive(self):
        """Course matching should be case-insensitive."""
        self._create_evidence("acc-cs101-quiz1")
        result = self.connector.discover_assignments(course_id="CS101")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()

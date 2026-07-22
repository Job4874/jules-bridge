"""Academic Command Center Workflow Connector for UnifiedOperator.

Manages assignment discovery, submission safety validation, unanswered field checks,
attempt record logging, and single review/submit checkpointing.

SAFETY INVARIANT: course_id is REQUIRED for all discovery and submission operations.
Without explicit course isolation, the academic operator must not touch any course data.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
_ACC_DIR = Path.home() / ".academic-command-center"


class AcademicWorkflowConnector:
    """Manages academic course discovery, submission validation, and checkpointed reviews.

    All operations require an explicit course_id to prevent cross-course contamination.
    """

    def __init__(self, acc_dir: Path = _ACC_DIR) -> None:
        self.acc_dir = acc_dir
        self.acc_dir.mkdir(parents=True, exist_ok=True)

    def discover_assignments(self, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover assignments and due dates from local ACC state.

        Args:
            course_id: Required. The exact course identifier to filter by.
                       Returns empty list if None — the operator must always
                       specify which course to query.

        Returns:
            List of assignment dicts for the specified course only.
            Empty list if course_id is None or no matching evidence exists.
        """
        if course_id is None:
            return []

        evidence_dir = self.acc_dir / "evidence"
        assignments: List[Dict[str, Any]] = []
        if evidence_dir.exists():
            for p in evidence_dir.glob("**/PROOF*.md"):
                if self._course_matches(p.parent.name, course_id):
                    assignments.append({
                        "assignment_id": p.parent.name,
                        "proof_path": str(p),
                        "modified_time": p.stat().st_mtime,
                        "course_id": course_id,
                    })
        return sorted(assignments, key=lambda a: a["modified_time"], reverse=True)

    @staticmethod
    def _course_matches(directory_name: str, course_id: str) -> bool:
        """Check if a directory name matches a course_id using exact segment matching.

        Splits the directory name on common delimiters (hyphen, underscore, space, dot)
        and checks whether the full course_id appears as an exact token. This prevents
        substring false matches like "CS1" matching "CS101".

        Examples:
            _course_matches("acc-CS101-quiz1", "CS101")  -> True
            _course_matches("acc-CS101-quiz1", "CS10")   -> False
            _course_matches("acc-CS10-quiz1", "CS10")    -> True
            _course_matches("CS101_final", "CS101")      -> True
        """
        import re  # pylint: disable=import-outside-toplevel
        # Split on common directory-name delimiters
        tokens = re.split(r"[-_ .]+", directory_name)
        normalized_id = course_id.strip().casefold()
        return any(t.casefold() == normalized_id for t in tokens)

    def validate_submission_safety(self, submission_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate submission to prevent accidental blank/incomplete submissions.

        SAFETY: Requires course_id in the payload. Submissions without an explicit
        course_id are rejected to prevent cross-course contamination.
        """
        # Course isolation gate — must be checked first
        course_id = submission_payload.get("course_id")
        if not course_id:
            return {
                "safe": False,
                "reason": "Submission rejected: course_id is required for course isolation safety",
            }

        content = submission_payload.get("content", "")
        file_path = submission_payload.get("file_path", "")
        unanswered_fields = submission_payload.get("unanswered_fields", [])

        if not content and not file_path:
            return {
                "safe": False,
                "reason": "Accidental blank submission detected: no content or file attached",
            }

        if unanswered_fields:
            return {
                "safe": False,
                "reason": f"Incomplete submission: unanswered fields detected ({len(unanswered_fields)})",
                "unanswered_fields": unanswered_fields,
            }

        if file_path and not Path(file_path).exists():
            return {
                "safe": False,
                "reason": f"Attachment file does not exist: {file_path}",
            }

        return {
            "safe": True,
            "course_id": course_id,
            "status": "ready_for_review_checkpoint",
            "checkpoint_required": True,
            "timestamp": time.time(),
        }

    def record_attempt(self, assignment_id: str, attempt_data: Dict[str, Any]) -> Path:
        """Preserve complete attempt record on disk."""
        log_dir = self.acc_dir / "attempts" / assignment_id
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = int(time.time())
        record_file = log_dir / f"attempt_{stamp}.json"
        attempt_data["timestamp_epoch"] = stamp
        record_file.write_text(json.dumps(attempt_data, indent=2), encoding="utf-8")
        return record_file

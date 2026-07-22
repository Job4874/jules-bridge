"""Academic Command Center Workflow Connector for UnifiedOperator.

Manages assignment discovery, submission safety validation, unanswered field checks,
attempt record logging, and single review/submit checkpointing.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
_ACC_DIR = Path.home() / ".academic-command-center"


class AcademicWorkflowConnector:
    """Manages academic course discovery, submission validation, and checkpointed reviews."""

    def __init__(self, acc_dir: Path = _ACC_DIR) -> None:
        self.acc_dir = acc_dir
        self.acc_dir.mkdir(parents=True, exist_ok=True)

    def discover_assignments(self, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover assignments and due dates from local ACC state."""
        evidence_dir = self.acc_dir / "evidence"
        assignments: List[Dict[str, Any]] = []
        if evidence_dir.exists():
            for p in evidence_dir.glob("**/PROOF*.md"):
                if course_id is None or course_id.casefold() in p.parent.name.casefold():
                    assignments.append({
                        "assignment_id": p.parent.name,
                        "proof_path": str(p),
                        "modified_time": p.stat().st_mtime,
                        "course_filter": course_id,
                    })
        return sorted(assignments, key=lambda a: a["modified_time"], reverse=True)

    def validate_submission_safety(self, submission_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate submission to prevent accidental blank/incomplete submissions."""
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

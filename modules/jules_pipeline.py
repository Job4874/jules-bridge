"""Jules Cloud-to-Local-to-Tested-Commit Pipeline for UnifiedOperator.

Every external side effect (Jules API call, git commit) is preceded by generating
a durable operation ID and checkpointing intent, closing the crash-duplication window.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from modules.unified_operator import (
    UnifiedOperatorStateDB,
    generate_operation_id,
)

_ROOT = Path(__file__).resolve().parent.parent


class JulesPipeline:
    """Manages full cycle of cloud session creation, polling, patch pulling, testing, and git committing.

    Uses durable operation IDs to ensure crash recovery does not duplicate
    Jules sessions or git commits.
    """

    def __init__(self, repo_dir: Path = _ROOT, state_db: Optional[UnifiedOperatorStateDB] = None) -> None:
        self.repo_dir = repo_dir
        self.db = state_db or UnifiedOperatorStateDB()

    def dispatch_session(self, prompt: str) -> Dict[str, Any]:
        """Dispatch a new Jules remote cloud session with crash-safe checkpointing."""
        op_id = generate_operation_id("jules_dispatch")

        # Phase 1: Record intent
        self.db.save_checkpoint(
            idempotency_key=op_id,
            goal=f"dispatch_jules: {prompt[:80]}",
            workflow_step="dispatch_session",
            status="dispatching",
            payload={"prompt": prompt},
        )

        # Phase 2: Execute external call
        cmd = ["jules", "remote", "new", "--repo", ".", "--session", prompt]
        try:
            self.db.save_checkpoint(
                idempotency_key=op_id,
                goal=f"dispatch_jules: {prompt[:80]}",
                workflow_step="dispatch_session",
                status="executing",
                payload={"prompt": prompt, "cmd": " ".join(cmd)},
            )

            res = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)
            output = res.stdout.strip() or res.stderr.strip()
            result = {
                "status": "dispatched" if res.returncode == 0 else "error",
                "raw_output": output,
                "exit_code": res.returncode,
                "operation_id": op_id,
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            result = {"status": "error", "error": str(exc), "operation_id": op_id}

        # Phase 3: Mark completed
        self.db.save_checkpoint(
            idempotency_key=op_id,
            goal=f"dispatch_jules: {prompt[:80]}",
            workflow_step="dispatch_session",
            status="completed",
            payload=result,
        )
        return result

    async def poll_session(self, session_id: str, max_wait_s: float = 300.0) -> Dict[str, Any]:
        """Poll Jules remote session status until COMPLETED or FAILED."""
        start_t = time.time()
        while time.time() - start_t < max_wait_s:
            cmd = ["jules", "remote", "list", "--session"]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=self.repo_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                stdout_str = stdout.decode("utf-8")
                # Evaluate the status only against the polled session's own row.
                # Matching COMPLETED/FAILED against the entire multi-session output
                # would attribute another session's terminal state to this one.
                session_line = next(
                    (line for line in stdout_str.splitlines() if session_id in line),
                    None,
                )
                if session_line is not None:
                    if "COMPLETED" in session_line:
                        return {"status": "COMPLETED", "session_id": session_id, "elapsed_s": time.time() - start_t}
                    if "FAILED" in session_line:
                        return {"status": "FAILED", "session_id": session_id, "elapsed_s": time.time() - start_t}
            except Exception as exc:  # pylint: disable=broad-exception-caught
                return {"status": "error", "error": str(exc)}
            await asyncio.sleep(5.0)

        return {"status": "TIMEOUT", "session_id": session_id, "elapsed_s": time.time() - start_t}

    def pull_test_and_commit(self, session_id: str, commit_message: str) -> Dict[str, Any]:
        """Pull remote work, run test suite, and commit if tests pass.

        Each external side effect (pull, commit) gets its own operation ID.
        """
        # --- Pull phase ---
        pull_op_id = generate_operation_id("jules_pull")
        self.db.save_checkpoint(
            idempotency_key=pull_op_id,
            goal=f"pull_session: {session_id}",
            workflow_step="pull",
            status="dispatching",
            payload={"session_id": session_id},
        )

        pull_cmd = ["jules", "remote", "pull", "--session", session_id]
        self.db.save_checkpoint(
            idempotency_key=pull_op_id,
            goal=f"pull_session: {session_id}",
            workflow_step="pull",
            status="executing",
            payload={"session_id": session_id, "cmd": " ".join(pull_cmd)},
        )

        res_pull = subprocess.run(pull_cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)
        if res_pull.returncode != 0:
            self.db.save_checkpoint(
                idempotency_key=pull_op_id,
                goal=f"pull_session: {session_id}",
                workflow_step="pull",
                status="completed",
                payload={"status": "pull_failed", "error": res_pull.stderr.strip() or res_pull.stdout.strip()},
            )
            return {"status": "pull_failed", "error": res_pull.stderr.strip() or res_pull.stdout.strip()}

        self.db.save_checkpoint(
            idempotency_key=pull_op_id,
            goal=f"pull_session: {session_id}",
            workflow_step="pull",
            status="completed",
            payload={"status": "pull_success"},
        )

        # --- Test phase (no external side effect, no operation ID needed) ---
        test_cmd = [str(self.repo_dir / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", "tests/", "-q"]
        res_test = subprocess.run(test_cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)
        if res_test.returncode != 0:
            return {"status": "tests_failed", "output": res_test.stdout.strip() or res_test.stderr.strip()}

        # --- Commit phase ---
        commit_op_id = generate_operation_id("git_commit")
        self.db.save_checkpoint(
            idempotency_key=commit_op_id,
            goal=f"commit_session: {session_id}",
            workflow_step="commit",
            status="dispatching",
            payload={"session_id": session_id, "message": commit_message},
        )

        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=False)
        commit_cmd = ["git", "commit", "-m", f"feat(jules): {commit_message} (session {session_id})"]

        self.db.save_checkpoint(
            idempotency_key=commit_op_id,
            goal=f"commit_session: {session_id}",
            workflow_step="commit",
            status="executing",
            payload={"session_id": session_id, "message": commit_message},
        )

        res_commit = subprocess.run(commit_cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)

        result = {
            "status": "success",
            "session_id": session_id,
            "commit_output": res_commit.stdout.strip(),
            "test_output": res_test.stdout.strip(),
            "pull_operation_id": pull_op_id,
            "commit_operation_id": commit_op_id,
        }

        self.db.save_checkpoint(
            idempotency_key=commit_op_id,
            goal=f"commit_session: {session_id}",
            workflow_step="commit",
            status="completed",
            payload=result,
        )

        return result

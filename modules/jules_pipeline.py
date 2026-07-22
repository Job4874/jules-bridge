"""Jules Cloud-to-Local-to-Tested-Commit Pipeline for UnifiedOperator."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parent.parent


class JulesPipeline:
    """Manages full cycle of cloud session creation, polling, patch pulling, testing, and git committing."""

    def __init__(self, repo_dir: Path = _ROOT) -> None:
        self.repo_dir = repo_dir

    def dispatch_session(self, prompt: str) -> Dict[str, Any]:
        """Dispatch a new Jules remote cloud session."""
        cmd = ["jules", "remote", "new", "--repo", ".", "--session", prompt]
        try:
            res = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)
            output = res.stdout.strip() or res.stderr.strip()
            return {
                "status": "dispatched" if res.returncode == 0 else "error",
                "raw_output": output,
                "exit_code": res.returncode,
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {"status": "error", "error": str(exc)}

    def poll_session(self, session_id: str, max_wait_s: float = 300.0) -> Dict[str, Any]:
        """Poll Jules remote session status until COMPLETED or FAILED."""
        start_t = time.time()
        while time.time() - start_t < max_wait_s:
            cmd = ["jules", "remote", "list", "--session"]
            try:
                res = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)
                if session_id in res.stdout:
                    if "COMPLETED" in res.stdout:
                        return {"status": "COMPLETED", "session_id": session_id, "elapsed_s": time.time() - start_t}
                    if "FAILED" in res.stdout:
                        return {"status": "FAILED", "session_id": session_id, "elapsed_s": time.time() - start_t}
            except Exception as exc:  # pylint: disable=broad-exception-caught
                return {"status": "error", "error": str(exc)}
            time.sleep(5.0)

        return {"status": "TIMEOUT", "session_id": session_id, "elapsed_s": time.time() - start_t}

    def pull_test_and_commit(self, session_id: str, commit_message: str) -> Dict[str, Any]:
        """Pull remote work, run test suite, and commit if tests pass."""
        # Step 1: Pull patch
        pull_cmd = ["jules", "remote", "pull", "--session", session_id]
        res_pull = subprocess.run(pull_cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)
        if res_pull.returncode != 0:
            return {"status": "pull_failed", "error": res_pull.stderr.strip() or res_pull.stdout.strip()}

        # Step 2: Run pytest suite
        test_cmd = [str(self.repo_dir / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", "tests/", "-q"]
        res_test = subprocess.run(test_cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)
        if res_test.returncode != 0:
            return {"status": "tests_failed", "output": res_test.stdout.strip() or res_test.stderr.strip()}

        # Step 3: Commit verified changes
        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=False)
        commit_cmd = ["git", "commit", "-m", f"feat(jules): {commit_message} (session {session_id})"]
        res_commit = subprocess.run(commit_cmd, cwd=self.repo_dir, capture_output=True, text=True, check=False)

        return {
            "status": "success",
            "session_id": session_id,
            "commit_output": res_commit.stdout.strip(),
            "test_output": res_test.stdout.strip(),
        }

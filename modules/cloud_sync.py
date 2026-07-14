"""Cloud sync readiness for the Jules Bridge workspace.

This module hides Git/GitHub status probing behind a compact typed interface so
routes and dashboard clients can show publish readiness without mutating the
repo or leaking secrets.

Public interface:
    get_cloud_sync_status(...) -> CloudSyncStatusResult
    build_cloud_publish_packet(...) -> CloudPublishPacketResult
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_REMOTE_CREDENTIAL_RE = re.compile(r"(https?://)([^/@\s]+@)", re.IGNORECASE)

_cloud_sync_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class CloudSyncStatusResult(dict):
    """Keys: status, state, branch, upstream, ahead, behind, blockers, error."""


class CloudPublishPacketResult(dict):
    """Keys: status, state, status_snapshot, change_families, packet, blockers."""


def get_cloud_sync_status(
    root: str | Path = "",
    *,
    timeout_s: int = 4,
    use_cache: bool = True,
) -> CloudSyncStatusResult:
    """Return a read-only Git/GitHub cloud sync readiness snapshot.

    Args:
        root: Git repository root. Defaults to the bridge repo.
        timeout_s: Per-command timeout in seconds.
        use_cache: Reuse recent status results to protect dashboard polling.

    Returns:
        CloudSyncStatusResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        repo_root = Path(root).expanduser().resolve() if root else _ROOT
        timeout = max(1, min(int(timeout_s), 30))
        cache_ttl = max(1, int(os.environ.get("CLOUD_SYNC_CACHE_TTL_S", "30")))
        cache_key = json.dumps({"root": str(repo_root), "timeout": timeout}, sort_keys=True)
        now_ts = time.time()
        if use_cache and cache_key in _cloud_sync_cache:
            cached_ts, cached = _cloud_sync_cache[cache_key]
            if now_ts - cached_ts < cache_ttl:
                result = CloudSyncStatusResult(copy.deepcopy(cached))
                result["cache_age_s"] = int(now_ts - cached_ts)
                return result

        if not repo_root.exists():
            return _blocked(generated_at, "missing_repo", f"repo root does not exist: {repo_root.name}")

        inside = _git(repo_root, ["rev-parse", "--is-inside-work-tree"], timeout)
        if not _ok_text(inside, "true"):
            return _blocked(generated_at, "not_git_repo", "root is not a Git worktree")

        top = _git(repo_root, ["rev-parse", "--show-toplevel"], timeout)
        if top["ok"] and top["stdout"].strip():
            repo_root = Path(top["stdout"].strip()).resolve()

        branch = _git_stdout(repo_root, ["branch", "--show-current"], timeout) or "detached"
        upstream = _git_stdout(repo_root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], timeout)
        remote_name = _remote_from_upstream(upstream)
        remote_url = _git_stdout(repo_root, ["remote", "get-url", remote_name], timeout) if remote_name else ""
        remote_host = _remote_host(remote_url)
        remote_label = _remote_label(remote_url)
        ahead, behind = _ahead_behind(repo_root, timeout) if upstream else (0, 0)
        dirty = _dirty_summary(repo_root, timeout)
        gh = _github_auth(timeout)
        fetch_age_s = _fetch_head_age_s(repo_root)

        blockers: list[str] = []
        warnings: list[str] = []
        if not upstream:
            blockers.append("no_upstream")
        if not remote_host:
            blockers.append("no_remote")
        if dirty["dirty_count"] > 0:
            blockers.append("dirty_worktree")
        if behind > 0:
            blockers.append("behind_remote")
        if remote_host == "github.com" and not gh["authenticated"]:
            blockers.append("github_auth_required")
        if fetch_age_s is None:
            warnings.append("remote_tracking_not_sampled")
        elif fetch_age_s > 86400:
            warnings.append("remote_tracking_stale")

        publish_ready = not blockers and ahead > 0
        synced = not blockers and ahead == 0 and behind == 0
        if blockers:
            state = "blocked"
        elif publish_ready:
            state = "push_ready"
        elif synced:
            state = "synced"
        else:
            state = "ready"

        result = CloudSyncStatusResult(
            status="ready" if not blockers else "blocked",
            state=state,
            generated_at_utc=generated_at,
            cache_age_s=0,
            repo={
                "name": repo_root.name,
                "branch": branch,
                "upstream": upstream,
                "remote_name": remote_name,
                "remote_host": remote_host,
                "remote_label": remote_label,
            },
            git={
                "ahead": ahead,
                "behind": behind,
                "dirty_count": dirty["dirty_count"],
                "staged_count": dirty["staged_count"],
                "unstaged_count": dirty["unstaged_count"],
                "untracked_count": dirty["untracked_count"],
                "last_commit": _last_commit(repo_root, timeout),
                "fetch_age_s": fetch_age_s,
            },
            github=gh,
            publish_ready=publish_ready,
            synced=synced,
            blockers=blockers,
            warnings=warnings,
            privacy={
                "remote_url_returned": False,
                "secret_values_returned": False,
                "workspace_paths_returned": False,
            },
        )
        if use_cache:
            _cloud_sync_cache[cache_key] = (now_ts, copy.deepcopy(result))
        return result
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return CloudSyncStatusResult(
            status="error",
            state="error",
            generated_at_utc=generated_at,
            cache_age_s=0,
            error=str(exc),
            blockers=["sync_status_error"],
        )


def build_cloud_publish_packet(
    root: str | Path = "",
    *,
    objective: str = "",
    timeout_s: int = 4,
    use_cache: bool = False,
    write_packet: bool = False,
    output_dir: str = "",
) -> CloudPublishPacketResult:
    """Build a read-only publish/sync review packet for the current worktree.

    Args:
        root: Git repository root. Defaults to the bridge repo.
        objective: Operator-facing reason for this publish packet.
        timeout_s: Per-command timeout in seconds.
        use_cache: Reuse the cloud-sync status cache.
        write_packet: Persist markdown/JSON review artifacts under the repo.
        output_dir: Optional repo-local output directory.

    Returns:
        CloudPublishPacketResult. Never stages, commits, fetches, pulls, or pushes.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        repo_root = Path(root).expanduser().resolve() if root else _ROOT
        timeout = max(1, min(int(timeout_s), 30))
        status = get_cloud_sync_status(repo_root, timeout_s=timeout, use_cache=use_cache)
        if status.get("status") == "error":
            return CloudPublishPacketResult(
                status="error",
                state="error",
                generated_at_utc=generated_at,
                blockers=["sync_status_error"],
                warnings=[],
                status_snapshot=status,
                change_families=[],
                change_count=0,
                include_candidate_count=0,
                exclude_candidate_count=0,
                commands=[],
                packet="",
                artifacts={"packet_written": False, "packet_path": "", "state_path": ""},
            )

        top = _git(repo_root, ["rev-parse", "--show-toplevel"], timeout)
        if top["ok"] and top["stdout"].strip():
            repo_root = Path(top["stdout"].strip()).resolve()

        planned_packet_path: Path | None = None
        planned_state_path: Path | None = None
        planned_artifact_error: dict[str, Any] = {}
        if write_packet:
            planned_packet_path, planned_state_path, planned_artifact_error = _plan_publish_artifacts(
                repo_root,
                output_dir,
            )

        entries = _dirty_entries(repo_root, timeout)
        planned_entries = _planned_publish_artifact_entries(
            repo_root,
            timeout,
            entries,
            planned_packet_path,
            planned_state_path,
        )
        if planned_entries:
            entries = [*entries, *planned_entries]
            status = CloudSyncStatusResult(copy.deepcopy(status))
            git_status = status.setdefault("git", {})
            git_status["dirty_count"] = int(git_status.get("dirty_count", 0)) + len(planned_entries)
            git_status["untracked_count"] = int(git_status.get("untracked_count", 0)) + sum(
                1 for entry in planned_entries if not entry.get("tracked")
            )
            git_status["unstaged_count"] = int(git_status.get("unstaged_count", 0)) + sum(
                1 for entry in planned_entries if entry.get("tracked")
            )
            blockers = list(status.get("blockers", []))
            if "dirty_worktree" not in blockers:
                blockers.append("dirty_worktree")
            status["blockers"] = blockers
            status["status"] = "blocked"
            status["state"] = "blocked"
            status["publish_ready"] = False
            status["synced"] = False
        families = _change_families(entries)
        include_candidates = [row["path"] for row in entries if row.get("publish_candidate")]
        exclude_candidates = [row["path"] for row in entries if not row.get("publish_candidate")]
        commands = _publish_commands(status, include_candidates)
        blockers = list(status.get("blockers", []))
        warnings = list(dict.fromkeys(status.get("warnings", [])))
        if exclude_candidates and "generated_or_noisy_files_present" not in warnings:
            warnings.append("generated_or_noisy_files_present")
        status["warnings"] = warnings

        if blockers:
            state = "blocked"
        elif status.get("publish_ready"):
            state = "push_ready"
        elif status.get("synced"):
            state = "synced"
        else:
            state = "ready"

        packet = _render_publish_packet(
            generated_at=generated_at,
            objective=objective,
            status=status,
            state=state,
            families=families,
            include_candidates=include_candidates,
            exclude_candidates=exclude_candidates,
            commands=commands,
        )
        artifacts = {"packet_written": False, "packet_path": "", "state_path": ""}
        result = CloudPublishPacketResult(
            status="ready" if state in ("ready", "push_ready", "synced") else "blocked",
            state=state,
            generated_at_utc=generated_at,
            objective=objective,
            status_snapshot=status,
            change_families=families,
            change_count=len(entries),
            include_candidate_count=len(include_candidates),
            exclude_candidate_count=len(exclude_candidates),
            blockers=blockers,
            warnings=warnings,
            commands=commands,
            packet=packet,
            artifacts=artifacts,
            privacy={
                "remote_url_returned": False,
                "secret_values_returned": False,
                "workspace_paths_returned": False,
            },
        )
        if write_packet:
            artifacts = _write_publish_packet(
                result,
                repo_root,
                output_dir,
                packet_path=planned_packet_path,
                state_path=planned_state_path,
                planned_error=planned_artifact_error,
            )
            result["artifacts"] = artifacts
        return result
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return CloudPublishPacketResult(
            status="error",
            state="error",
            generated_at_utc=generated_at,
            error=str(exc),
            blockers=["publish_packet_error"],
            warnings=[],
            change_families=[],
            change_count=0,
            include_candidate_count=0,
            exclude_candidate_count=0,
            commands=[],
            packet="",
            artifacts={"packet_written": False, "packet_path": "", "state_path": ""},
        )


def _blocked(generated_at: str, blocker: str, error: str) -> CloudSyncStatusResult:
    return CloudSyncStatusResult(
        status="blocked",
        state="blocked",
        generated_at_utc=generated_at,
        cache_age_s=0,
        error=error,
        repo={},
        git={},
        github={"installed": bool(shutil.which("gh")), "authenticated": False, "account": ""},
        publish_ready=False,
        synced=False,
        blockers=[blocker],
        warnings=[],
        privacy={
            "remote_url_returned": False,
            "secret_values_returned": False,
            "workspace_paths_returned": False,
        },
    )


def _git(root: Path, args: list[str], timeout_s: int) -> dict[str, Any]:
    return _run(["git", *args], root, timeout_s)


def _run(argv: list[str], cwd: Path, timeout_s: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": stdout[:12000],
            "stderr": stderr[:4000],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": (exc.stdout or "")[:12000] if isinstance(exc.stdout, str) else "",
            "stderr": "timeout",
            "timed_out": True,
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {"ok": False, "exit_code": None, "stdout": "", "stderr": str(exc), "timed_out": False}


def _git_stdout(root: Path, args: list[str], timeout_s: int) -> str:
    result = _git(root, args, timeout_s)
    return result["stdout"].strip() if result["ok"] else ""


def _ok_text(result: dict[str, Any], expected: str) -> bool:
    return bool(result.get("ok") and result.get("stdout", "").strip().lower() == expected)


def _remote_from_upstream(upstream: str) -> str:
    if not upstream or "/" not in upstream:
        return ""
    return upstream.split("/", 1)[0]


def _remote_host(remote_url: str) -> str:
    text = _redact_remote(remote_url)
    if not text:
        return ""
    if "github.com" in text:
        return "github.com"
    if "://" in text:
        host = text.split("://", 1)[1].split("/", 1)[0]
        return host.lower()
    if ":" in text:
        host = text.split(":", 1)[0]
        return host.replace("git@", "").lower()
    return "configured"


def _remote_label(remote_url: str) -> str:
    text = _redact_remote(remote_url)
    if not text:
        return ""
    normalized = text.rstrip("/")
    repo_name = normalized.rsplit("/", 1)[-1].replace(".git", "")
    return f"{_remote_host(text)}/{repo_name}" if repo_name else _remote_host(text)


def _redact_remote(remote_url: str) -> str:
    return _REMOTE_CREDENTIAL_RE.sub(r"\1", remote_url or "").strip()


def _ahead_behind(root: Path, timeout_s: int) -> tuple[int, int]:
    output = _git_stdout(root, ["rev-list", "--left-right", "--count", "@{u}...HEAD"], timeout_s)
    parts = output.split()
    if len(parts) != 2:
        return 0, 0
    try:
        behind = int(parts[0])
        ahead = int(parts[1])
        return ahead, behind
    except ValueError:
        return 0, 0


def _dirty_summary(root: Path, timeout_s: int) -> dict[str, int]:
    lines = _status_lines(root, timeout_s)
    staged = 0
    unstaged = 0
    untracked = 0
    for line in lines:
        if line.startswith("??"):
            untracked += 1
            continue
        index = line[0] if line else " "
        worktree = line[1] if len(line) > 1 else " "
        if index != " ":
            staged += 1
        if worktree != " ":
            unstaged += 1
    return {
        "dirty_count": len(lines),
        "staged_count": staged,
        "unstaged_count": unstaged,
        "untracked_count": untracked,
    }


def _status_lines(root: Path, timeout_s: int) -> list[str]:
    result = _git(root, ["status", "--porcelain=v1", "-uall"], timeout_s)
    output = result["stdout"] if result["ok"] else ""
    return [line for line in output.splitlines() if line.strip()]


def _dirty_entries(root: Path, timeout_s: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in _status_lines(root, timeout_s):
        status_code = line[:2]
        path_text = line[3:] if len(line) > 3 else ""
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        family = _change_family(path_text)
        publish_candidate = family not in ("generated_noise",)
        entries.append({
            "status": status_code.strip() or "modified",
            "path": path_text,
            "family": family,
            "tracked": not line.startswith("??"),
            "publish_candidate": publish_candidate,
        })
    return entries


def _change_families(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_labels = {
        "bridge_routes": "Bridge routes",
        "backend_modules": "Backend modules",
        "dashboard_ui": "Dashboard UI",
        "tests": "Tests",
        "context_docs": "Context and memory",
        "evidence_packets": "Evidence packets",
        "config": "Config surface",
        "generated_noise": "Generated or noisy files",
        "other": "Other",
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(entry["family"], []).append(entry)

    rows: list[dict[str, Any]] = []
    for family, items in grouped.items():
        rows.append({
            "family": family,
            "label": family_labels.get(family, family.replace("_", " ").title()),
            "count": len(items),
            "publish_candidate_count": sum(1 for item in items if item.get("publish_candidate")),
            "tracked_count": sum(1 for item in items if item.get("tracked")),
            "untracked_count": sum(1 for item in items if not item.get("tracked")),
            "sample_paths": [item["path"] for item in items[:8]],
        })
    order = {
        "bridge_routes": 0,
        "backend_modules": 1,
        "dashboard_ui": 2,
        "tests": 3,
        "context_docs": 4,
        "config": 5,
        "evidence_packets": 6,
        "generated_noise": 7,
        "other": 8,
    }
    return sorted(rows, key=lambda row: (order.get(row["family"], 99), row["family"]))


def _change_family(path_text: str) -> str:
    path = (path_text or "").replace("\\", "/")
    lower = path.lower()
    name = lower.rsplit("/", 1)[-1]
    if path in ("bridge.py", "modules/__init__.py") or lower.startswith("modules/jules_"):
        return "bridge_routes"
    if lower.startswith("modules/"):
        return "backend_modules"
    if lower.startswith("dashboard-ui/"):
        return "dashboard_ui"
    if lower.startswith("tests/"):
        return "tests"
    if (
        lower.startswith("context/")
        or lower.startswith("memory/")
        or lower in ("ubiquitous_language.md", "implementation_plan.md")
    ):
        return "context_docs"
    if (
        name.startswith("bridge.log")
        or lower.startswith(".codex/")
        or lower.startswith("scratch/screenshots/")
        or name.startswith("__tmp")
    ):
        return "generated_noise"
    if lower.startswith("jules_inbox/"):
        return "evidence_packets"
    if lower in (".env.example", "package.json", "package-lock.json") or lower.endswith(".toml"):
        return "config"
    return "other"


def _publish_commands(status: dict[str, Any], include_candidates: list[str]) -> list[dict[str, str]]:
    branch = status.get("repo", {}).get("branch", "master") if isinstance(status.get("repo"), dict) else "master"
    remote_name = status.get("repo", {}).get("remote_name", "origin") if isinstance(status.get("repo"), dict) else "origin"
    commands: list[dict[str, str]] = [
        {"label": "Review", "command": "git status --short"},
        {"label": "Verify", "command": "python -m pytest tests/ -q"},
        {"label": "Dashboard lint", "command": "npm run lint", "cwd": "dashboard-ui"},
        {"label": "Dashboard build", "command": "npm run build", "cwd": "dashboard-ui"},
    ]
    if include_candidates:
        commands.insert(1, {
            "label": "Stage reviewed candidates",
            "command": f"git add -- {' '.join(_quote_git_path(path) for path in include_candidates)}",
        })
        commands.insert(2, {
            "label": "Commit",
            "command": 'git commit -m "feat: strengthen Jules Google bridge dashboard"',
        })
    if status.get("publish_ready") or include_candidates:
        commands.append({
            "label": "Push after commit",
            "command": f"git push {remote_name or 'origin'} {branch or 'master'}",
        })
    return commands


def _quote_git_path(path_text: str) -> str:
    return f'"{str(path_text).replace(chr(34), chr(92) + chr(34))}"'


def _render_publish_packet(
    *,
    generated_at: str,
    objective: str,
    status: dict[str, Any],
    state: str,
    families: list[dict[str, Any]],
    include_candidates: list[str],
    exclude_candidates: list[str],
    commands: list[dict[str, str]],
) -> str:
    repo = status.get("repo", {}) if isinstance(status, dict) else {}
    git = status.get("git", {}) if isinstance(status, dict) else {}
    blockers = status.get("blockers", []) if isinstance(status, dict) else []
    warnings = status.get("warnings", []) if isinstance(status, dict) else []
    lines = [
        "# Cloud Publish Packet",
        "",
        f"- generated_at_utc: {generated_at}",
        f"- objective: {objective or 'Review and publish the current Jules Bridge dashboard/model bridge work.'}",
        f"- state: {state}",
        f"- branch: {repo.get('branch', '')}",
        f"- upstream: {repo.get('upstream', '')}",
        f"- ahead_behind: {git.get('ahead', 0)} / {git.get('behind', 0)}",
        f"- dirty_count: {git.get('dirty_count', 0)}",
        f"- blockers: {', '.join(blockers) if blockers else 'none'}",
        f"- warnings: {', '.join(warnings) if warnings else 'none'}",
        "",
        "## Change Families",
    ]
    if families:
        for row in families:
            lines.append(
                f"- {row['label']}: {row['count']} files "
                f"({row['publish_candidate_count']} publish candidates)"
            )
            for sample in row.get("sample_paths", [])[:5]:
                lines.append(f"  - {sample}")
    else:
        lines.append("- No dirty files detected.")

    lines.extend([
        "",
        "## Publish Candidates",
        f"- include: {len(include_candidates)}",
        f"- exclude_or_review_separately: {len(exclude_candidates)}",
        "",
        "## Review Commands",
    ])
    for row in commands:
        cwd = f" (cwd: {row['cwd']})" if row.get("cwd") else ""
        lines.append(f"- {row['label']}{cwd}: `{row['command']}`")
    lines.extend([
        "",
        "## Safety",
        "- This packet did not run git add, git commit, git fetch, git pull, or git push.",
        "- Generated/noisy files should be reviewed separately before staging.",
    ])
    return "\n".join(lines).strip() + "\n"


def _plan_publish_artifacts(
    repo_root: Path,
    output_dir: str,
) -> tuple[Path | None, Path | None, dict[str, Any]]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    directory = Path(output_dir).expanduser() if output_dir else repo_root / "jules_inbox" / "cloud_sync"
    if not directory.is_absolute():
        directory = repo_root / directory
    directory = directory.resolve()
    try:
        directory.relative_to(repo_root.resolve())
    except ValueError:
        return None, None, {
            "packet_written": False,
            "packet_path": "",
            "state_path": "",
            "error": "output_dir must stay inside the repository",
        }
    return directory / f"CLOUD_PUBLISH_PACKET_{timestamp}.md", directory / "CLOUD_PUBLISH_STATE.json", {}


def _planned_publish_artifact_entries(
    repo_root: Path,
    timeout_s: int,
    existing_entries: list[dict[str, Any]],
    packet_path: Path | None,
    state_path: Path | None,
) -> list[dict[str, Any]]:
    existing_paths = {str(row.get("path", "")).replace("\\", "/") for row in existing_entries}
    planned_entries: list[dict[str, Any]] = []
    for path in (state_path, packet_path):
        if path is None:
            continue
        path_text = path.relative_to(repo_root.resolve()).as_posix()
        if path_text in existing_paths:
            continue
        family = _change_family(path_text)
        tracked = _git(repo_root, ["ls-files", "--error-unmatch", "--", path_text], timeout_s)["ok"]
        planned_entries.append({
            "status": "modified" if tracked else "untracked",
            "path": path_text,
            "family": family,
            "tracked": tracked,
            "publish_candidate": family not in ("generated_noise",),
        })
        existing_paths.add(path_text)
    return planned_entries


def _write_publish_packet(
    result: CloudPublishPacketResult,
    repo_root: Path,
    output_dir: str,
    *,
    packet_path: Path | None = None,
    state_path: Path | None = None,
    planned_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if planned_error:
        return planned_error
    if packet_path is None or state_path is None:
        packet_path, state_path, planned_error = _plan_publish_artifacts(repo_root, output_dir)
        if planned_error:
            return planned_error
    directory = packet_path.parent
    directory.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(str(result.get("packet", "")), encoding="utf-8")
    packet_label = packet_path.relative_to(repo_root.resolve()).as_posix()
    state_label = state_path.relative_to(repo_root.resolve()).as_posix()
    artifacts = {
        "packet_written": True,
        "packet_path": packet_label,
        "state_path": state_label,
    }
    state_payload = dict(result)
    state_payload["artifacts"] = artifacts
    state_path.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
    return artifacts


def _github_auth(timeout_s: int) -> dict[str, Any]:
    if not shutil.which("gh"):
        return {"installed": False, "authenticated": False, "account": "", "status": "missing"}
    result = _run(["gh", "auth", "status"], _ROOT, timeout_s)
    text = "\n".join([result.get("stdout", ""), result.get("stderr", "")])
    authenticated = result.get("ok", False) and "Logged in to github.com account" in text
    account = ""
    match = re.search(r"Logged in to github\.com account ([^\s]+)", text)
    if match:
        account = match.group(1)
    return {
        "installed": True,
        "authenticated": bool(authenticated),
        "account": account,
        "status": "authenticated" if authenticated else "auth_required",
    }


def _fetch_head_age_s(root: Path) -> int | None:
    fetch_head = root / ".git" / "FETCH_HEAD"
    try:
        if not fetch_head.exists():
            return None
        return max(0, int(time.time() - fetch_head.stat().st_mtime))
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _last_commit(root: Path, timeout_s: int) -> dict[str, str]:
    output = _git_stdout(root, ["log", "-1", "--format=%h%x00%cI"], timeout_s)
    if "\x00" not in output:
        return {"short_sha": "", "committed_at": ""}
    short_sha, committed_at = output.split("\x00", 1)
    return {"short_sha": short_sha.strip(), "committed_at": committed_at.strip()}

"""Bounded local codebase analysis for bridge agents.

Builds a compact, secret-safe snapshot of the current repository so local and
remote agents can reason about the codebase without raw filesystem scraping.

Public interface:
    analyze_codebase(root_path, max_files, include_files) -> CodebaseAnalysisResult
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CodebaseAnalysisResult(dict):
    """Keys: ok, status, summary, routes, modules, tests, integrations, findings."""


_ROOT = Path(__file__).parent.parent
_MAX_FILE_BYTES = 700_000
_MAX_RETURNED_FILES = 300
_SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
_SOURCE_EXTENSIONS = {
    ".cmd",
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
_ENV_FILES = (".env", ".env.example", ".env.local", ".env.development")
_SECRET_KEY_RE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL|AUTH)", re.IGNORECASE)
_ROUTE_RE = re.compile(
    r"@app\.route\(\s*[\"']([^\"']+)[\"'](?:\s*,\s*methods=\[([^\]]*)\])?",
    re.MULTILINE,
)
_METHOD_RE = re.compile(r"[\"']([A-Z]+)[\"']")


def analyze_codebase(
    root_path: str | os.PathLike[str] | None = None,
    *,
    max_files: int = 2500,
    include_files: bool = False,
) -> CodebaseAnalysisResult:
    """Analyze a local repo with bounded, secret-safe output. Never raises."""
    try:
        root = Path(root_path or _ROOT).expanduser().resolve()
        max_files = max(50, min(int(max_files), 10_000))
        if not root.exists() or not root.is_dir():
            return CodebaseAnalysisResult(
                ok=False,
                status="error",
                error="root_path must be an existing directory",
                root={"name": root.name or str(root), "path_ref": _path_ref(root)},
            )

        rows, walk_meta = _walk_source_files(root, max_files)
        language_rows = _language_rows(rows)
        directory_rows = _directory_rows(rows)
        route_rows = _route_rows(root)
        module_summary = _module_summary(root)
        test_summary = _test_summary(root, module_summary)
        frontend = _frontend_summary(root)
        dependencies = _dependency_summary(root)
        environment = _environment_summary(root)
        integrations = _integration_rows(root, route_rows)
        findings = _findings(root, rows, route_rows, module_summary, test_summary, frontend, integrations)

        summary = {
            "file_count": len(rows),
            "source_file_count": sum(1 for row in rows if row["extension"] in _SOURCE_EXTENSIONS),
            "directory_count": walk_meta["directory_count"],
            "analyzed_bytes": sum(row["bytes"] for row in rows),
            "line_count": sum(row["lines"] for row in rows),
            "route_count": len(route_rows),
            "module_count": module_summary["count"],
            "test_count": test_summary["count"],
            "frontend_dependency_count": frontend["dependency_count"],
            "env_key_count": environment["env_key_count"],
            "integration_ready_count": sum(1 for row in integrations if row["ready"]),
            "truncated": walk_meta["truncated"],
        }

        result = CodebaseAnalysisResult(
            ok=True,
            status="ready",
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            root={
                "name": root.name,
                "path_ref": _path_ref(root),
                "default_bridge_root": root == _ROOT.resolve(),
            },
            limits={
                "max_files": max_files,
                "max_file_bytes": _MAX_FILE_BYTES,
                "include_files": bool(include_files),
            },
            summary=summary,
            languages=language_rows,
            top_directories=directory_rows,
            routes={"count": len(route_rows), "items": route_rows[:80], "truncated": len(route_rows) > 80},
            modules=module_summary,
            tests=test_summary,
            frontend=frontend,
            dependencies=dependencies,
            environment=environment,
            integrations=integrations,
            findings=findings,
            handoff={
                "route": "POST /codebase/analyze",
                "payload": {"max_files": min(max_files, 2500), "include_files": False},
                "purpose": "Bounded local repo snapshot for VM/Jules without raw secrets or bulk file dumps.",
            },
        )
        if include_files:
            result["files"] = rows[:_MAX_RETURNED_FILES]
            result["files_truncated"] = len(rows) > _MAX_RETURNED_FILES
        return result
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return CodebaseAnalysisResult(
            ok=False,
            status="error",
            error=str(exc),
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
        )


def _walk_source_files(root: Path, max_files: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    directory_count = 0
    truncated = False
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in sorted(dirnames, key=str.lower)
            if name not in _SKIP_DIRS and not name.endswith(".egg-info")
        ]
        directory_count += len(dirnames)
        current_path = Path(current)
        for filename in sorted(filenames, key=str.lower):
            path = current_path / filename
            rel = _rel_path(root, path)
            if _should_skip_file(path, rel):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size > _MAX_FILE_BYTES:
                continue
            rows.append(_file_row(root, path, stat.st_size))
            if len(rows) >= max_files:
                truncated = True
                return rows, {"directory_count": directory_count, "truncated": truncated}
    return rows, {"directory_count": directory_count, "truncated": truncated}


def _should_skip_file(path: Path, rel: str) -> bool:
    if path.suffix.lower() not in _SOURCE_EXTENSIONS and path.name not in _ENV_FILES:
        return True
    parts = set(Path(rel).parts)
    return bool(parts.intersection(_SKIP_DIRS))


def _file_row(root: Path, path: Path, size: int) -> dict[str, Any]:
    rel = _rel_path(root, path)
    return {
        "path": rel,
        "kind": _file_kind(rel),
        "extension": path.suffix.lower() or path.name,
        "bytes": size,
        "lines": _line_count(path),
    }


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except Exception:  # pylint: disable=broad-exception-caught
        return 0


def _file_kind(rel: str) -> str:
    parts = Path(rel).parts
    if not parts:
        return "other"
    if parts[0] == "modules":
        return "backend_module"
    if parts[0] == "tests":
        return "test"
    if parts[0] == "dashboard-ui":
        return "frontend"
    if parts[0] == "context":
        return "context"
    if parts[0] in ("doc", "docs", "memory") or rel.endswith(".md"):
        return "docs"
    if parts[0] in ("scripts", "vm_scripts"):
        return "automation"
    if parts[0] == "jules_inbox":
        return "agent_state"
    return "root"


def _route_rows(root: Path) -> list[dict[str, Any]]:
    bridge_path = root / "bridge.py"
    try:
        text = bridge_path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # pylint: disable=broad-exception-caught
        return []
    rows = []
    for match in _ROUTE_RE.finditer(text):
        methods_raw = match.group(2) or ""
        methods = _METHOD_RE.findall(methods_raw) or ["GET"]
        rows.append({"path": match.group(1), "methods": sorted(set(methods))})
    rows.sort(key=lambda row: (row["path"], ",".join(row["methods"])))
    return rows


def _module_summary(root: Path) -> dict[str, Any]:
    modules_dir = root / "modules"
    module_files = sorted(modules_dir.glob("*.py")) if modules_dir.exists() else []
    public_modules = [path.stem for path in module_files if path.name != "__init__.py"]
    large_modules = [
        {"name": path.stem, "lines": _line_count(path)}
        for path in module_files
        if _line_count(path) > 500
    ]
    return {
        "count": len(public_modules),
        "public_modules": public_modules[:80],
        "large_modules": sorted(large_modules, key=lambda row: row["lines"], reverse=True)[:10],
    }


def _test_summary(root: Path, module_summary: dict[str, Any]) -> dict[str, Any]:
    tests_dir = root / "tests"
    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
    test_stems = {path.stem.removeprefix("test_") for path in test_files}
    modules = set(module_summary.get("public_modules", []))
    covered = sorted(modules.intersection(test_stems))
    return {
        "count": len(test_files),
        "covered_module_count": len(covered),
        "coverage_ratio": round(len(covered) / max(len(modules), 1), 3),
        "sample_tests": [path.name for path in test_files[:20]],
    }


def _frontend_summary(root: Path) -> dict[str, Any]:
    package_path = root / "dashboard-ui" / "package.json"
    data = _read_json(package_path)
    dependencies = {}
    dev_dependencies = {}
    scripts = {}
    if isinstance(data, dict):
        dependencies = data.get("dependencies", {}) if isinstance(data.get("dependencies"), dict) else {}
        dev_dependencies = data.get("devDependencies", {}) if isinstance(data.get("devDependencies"), dict) else {}
        scripts = data.get("scripts", {}) if isinstance(data.get("scripts"), dict) else {}
    return {
        "present": package_path.exists(),
        "package_name": str(data.get("name", "")) if isinstance(data, dict) else "",
        "dependency_count": len(dependencies) + len(dev_dependencies),
        "dependencies": sorted(dependencies.keys())[:30],
        "dev_dependencies": sorted(dev_dependencies.keys())[:30],
        "scripts": scripts,
        "app_entry_present": (root / "dashboard-ui" / "src" / "App.jsx").exists(),
    }


def _dependency_summary(root: Path) -> dict[str, Any]:
    requirements = []
    requirements_path = root / "requirements.txt"
    try:
        requirements = [
            line.strip()
            for line in requirements_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    except Exception:  # pylint: disable=broad-exception-caught
        requirements = []
    return {
        "python_requirement_count": len(requirements),
        "python_requirements": requirements[:40],
        "node_package_lock": (root / "dashboard-ui" / "package-lock.json").exists(),
    }


def _environment_summary(root: Path) -> dict[str, Any]:
    keys = []
    secret_key_count = 0
    for env_name in _ENV_FILES:
        env_path = root / env_name
        if not env_path.exists():
            continue
        try:
            with env_path.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "=" not in line or line.lstrip().startswith("#"):
                        continue
                    key = line.partition("=")[0].strip()
                    if not key:
                        continue
                    keys.append(key)
                    if _SECRET_KEY_RE.search(key):
                        secret_key_count += 1
        except Exception:  # pylint: disable=broad-exception-caught
            continue
    safe_keys = sorted(set(keys))
    return {
        "env_key_count": len(safe_keys),
        "env_keys_present": safe_keys,
        "secret_key_name_count": secret_key_count,
        "values_redacted": True,
    }


def _integration_rows(root: Path, routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    route_paths = {row["path"] for row in routes}
    checks = [
        ("vm_worker_chat", "VM/Jules chat worker", "/chat" in route_paths and (root / "modules" / "vm_relay.py").exists()),
        ("vm_callback_append", "VM callback inbox append", "/inbox/append" in route_paths and (root / "modules" / "inbox_service.py").exists()),
        ("gemini_cli", "Gemini CLI bridge", (root / "modules" / "gemini_cli.py").exists()),
        ("antigravity_cli", "Antigravity CLI bridge", (root / "modules" / "antigravity_cli.py").exists()),
        ("alliance_switchboard", "Jules/Gemini alliance switchboard", (root / "modules" / "alliance_switchboard.py").exists()),
        ("dashboard_ui", "React dashboard UI", (root / "dashboard-ui" / "src" / "App.jsx").exists()),
        ("codebase_analyzer", "Bounded local codebase analyzer", "/codebase/analyze" in route_paths),
    ]
    return [
        {"id": item_id, "label": label, "ready": bool(ready), "tone": "success" if ready else "warn"}
        for item_id, label, ready in checks
    ]


def _findings(
    root: Path,
    rows: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    modules: dict[str, Any],
    tests: dict[str, Any],
    frontend: dict[str, Any],
    integrations: list[dict[str, Any]],
) -> list[dict[str, str]]:
    ready = {row["id"]: row["ready"] for row in integrations}
    findings: list[dict[str, str]] = []
    if ready.get("vm_worker_chat") and ready.get("codebase_analyzer"):
        findings.append({
            "tone": "success",
            "title": "VM worker has a bounded local analysis handoff",
            "detail": "Use POST /codebase/analyze before asking Jules to reason about this Windows repo.",
        })
    elif ready.get("vm_worker_chat"):
        findings.append({
            "tone": "warn",
            "title": "VM worker can chat but lacks a local repo snapshot route",
            "detail": "Remote Jules cannot infer this Windows tree without a bounded bridge snapshot.",
        })
    if ready.get("gemini_cli") and ready.get("antigravity_cli") and ready.get("alliance_switchboard"):
        findings.append({
            "tone": "success",
            "title": "Google-side model modules are present",
            "detail": "Gemini CLI, Antigravity CLI, and the alliance switchboard all exist as module surfaces.",
        })
    if routes:
        findings.append({
            "tone": "info",
            "title": "Bridge is route-rich; keep logic in modules",
            "detail": f"{len(routes)} Flask routes detected, with {modules['count']} backend modules available.",
        })
    large_ui = next((row for row in rows if row["path"] == "dashboard-ui/src/App.jsx"), None)
    if large_ui and large_ui["lines"] > 800:
        findings.append({
            "tone": "warn",
            "title": "Dashboard UI is becoming a large single component file",
            "detail": "Future UI expansion should split stable panels after the current cockpit stabilizes.",
        })
    if tests.get("count", 0) > 0:
        findings.append({
            "tone": "success",
            "title": "Backend has a substantial test harness",
            "detail": f"{tests['count']} test files detected; module coverage ratio is {tests['coverage_ratio']}.",
        })
    if frontend.get("present"):
        findings.append({
            "tone": "info",
            "title": "Dashboard build surface is isolated",
            "detail": f"{frontend['package_name'] or 'dashboard-ui'} owns React/Vite dependencies under dashboard-ui.",
        })
    if (root / ".env").exists():
        findings.append({
            "tone": "info",
            "title": "Environment values are intentionally redacted",
            "detail": "The analyzer reports env key names and counts only, never secret values.",
        })
    return findings[:12]


def _language_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    bytes_by_ext: Counter[str] = Counter()
    lines_by_ext: Counter[str] = Counter()
    for row in rows:
        ext = row["extension"]
        counts[ext] += 1
        bytes_by_ext[ext] += row["bytes"]
        lines_by_ext[ext] += row["lines"]
    return [
        {"extension": ext, "files": counts[ext], "bytes": bytes_by_ext[ext], "lines": lines_by_ext[ext]}
        for ext in sorted(counts, key=lambda key: (-counts[key], key))[:30]
    ]


def _directory_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        first = Path(row["path"]).parts[0] if Path(row["path"]).parts else "."
        counts[first] += 1
    return [
        {"name": name, "files": count}
        for name, count in counts.most_common(20)
    ]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _rel_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _path_ref(path: Path) -> str:
    digest = hashlib.sha256(str(path).lower().encode("utf-8")).hexdigest()[:12]
    return f"path:{path.name or 'root'}:{digest}"

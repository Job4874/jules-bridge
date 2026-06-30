"""Repository context guard for no-slop multi-repo orchestration.

Scans bounded local roots for Git repositories, extracts provenance signals,
and reports collisions that can make Jules/Codex sessions mix projects, ports,
nodes, or local dependencies.

Public interface:
    build_repo_context_guard() -> RepoContextGuardResult
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, TypedDict


_ROOT = Path(__file__).parent.parent
_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "bin",
    "build",
    "dist",
    "node_modules",
    "obj",
    "out",
    "target",
    "venv",
}
_ENV_FILES = (".env", ".env.local", ".env.development", ".env.example")
_DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)
_SECRET_KEY_RE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL|AUTH)", re.IGNORECASE)
_NODE_KEY_RE = re.compile(r"(NODE|WORKER|VM|SERVER|HOST|IP)", re.IGNORECASE)
_PORT_KEY_RE = re.compile(r"PORT", re.IGNORECASE)
_LOCALHOST_PORT_RE = re.compile(r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d{2,5})", re.IGNORECASE)
_FLAG_PORT_RE = re.compile(r"(?:--port|-p|PORT)\s*[=: ]\s*(\d{2,5})", re.IGNORECASE)
_URL_CREDENTIAL_RE = re.compile(r"(https?://)([^/@\s]+@)", re.IGNORECASE)


class RepoContextGuardResult(TypedDict, total=False):
    status: str
    generated_at_utc: str
    roots_scanned: list[str]
    roots_missing: list[str]
    summary: dict[str, Any]
    repos: list[dict[str, Any]]
    collisions: list[dict[str, Any]]
    guardrails: list[str]
    cache_age_s: int
    error: str | None


_repo_context_guard_cache: dict[str, tuple[float, RepoContextGuardResult]] = {}


def build_repo_context_guard(
    roots: Iterable[str | Path] | None = None,
    *,
    max_depth: int = 4,
    max_repos: int = 100,
    include_repos: bool = True,
    use_cache: bool = True,
) -> RepoContextGuardResult:
    """Build a bounded repo inventory and collision report. Never raises."""

    try:
        max_depth = max(0, min(int(max_depth), 12))
        max_repos = max(1, min(int(max_repos), 500))
        root_paths = _resolve_roots(roots)
        cache_key = json.dumps(
            {
                "roots": [str(path) for path in root_paths],
                "max_depth": max_depth,
                "max_repos": max_repos,
                "include_repos": include_repos,
            },
            sort_keys=True,
        )
        ttl_s = max(1, int(os.environ.get("REPO_CONTEXT_GUARD_CACHE_TTL_S", "120")))
        now_ts = time.time()
        if use_cache and cache_key in _repo_context_guard_cache:
            cached_ts, cached = _repo_context_guard_cache[cache_key]
            if now_ts - cached_ts < ttl_s:
                result = _copy_result(cached)
                result["cache_age_s"] = int(now_ts - cached_ts)
                return result

        repo_paths, roots_scanned, roots_missing, truncated = _discover_repos(
            root_paths,
            max_depth=max_depth,
            max_repos=max_repos,
        )
        repos = [_inspect_repo(path) for path in repo_paths]
        collisions = _detect_collisions(repos)
        severity_counts = _severity_counts(collisions)

        summary = {
            "repo_count": len(repos),
            "collision_count": len(collisions),
            "collision_severity_counts": severity_counts,
            "roots_scanned_count": len(roots_scanned),
            "roots_missing_count": len(roots_missing),
            "scan_truncated": truncated,
            "sample_repos": [repo["name"] for repo in repos[:8]],
        }
        result: RepoContextGuardResult = {
            "status": "partial" if roots_missing or truncated else "ready",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "roots_scanned": roots_scanned,
            "roots_missing": roots_missing,
            "summary": summary,
            "collisions": collisions,
            "guardrails": [
                "Label work by repo path_ref and remote before dispatching Jules workers.",
                "Do not reuse claimed ports or server nodes across repos unless explicitly requested.",
                "Treat file/link/workspace dependencies across repo roots as coupling that needs review.",
                "Report env key names and readiness only; never return secret values.",
            ],
            "cache_age_s": 0,
            "error": None,
        }
        if include_repos:
            result["repos"] = repos

        if use_cache:
            _repo_context_guard_cache[cache_key] = (now_ts, _copy_result(result))
        return result
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "status": "error",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "roots_scanned": [],
            "roots_missing": [],
            "summary": {
                "repo_count": 0,
                "collision_count": 0,
                "collision_severity_counts": {},
                "roots_scanned_count": 0,
                "roots_missing_count": 0,
                "scan_truncated": False,
                "sample_repos": [],
            },
            "collisions": [],
            "guardrails": [],
            "cache_age_s": 0,
            "error": str(exc),
        }


def _copy_result(result: RepoContextGuardResult) -> RepoContextGuardResult:
    return json.loads(json.dumps(result))


def _resolve_roots(roots: Iterable[str | Path] | None) -> list[Path]:
    raw_roots: list[str | Path]
    if roots is not None:
        raw_roots = list(roots)
    else:
        env_roots = os.environ.get("JULES_REPO_GUARD_ROOTS", "")
        if env_roots.strip():
            raw_roots = [part for part in env_roots.split(";") if part.strip()]
        else:
            home = Path.home()
            raw_roots = [
                _ROOT,
                Path("C:/aotp/projects"),
                home / "Downloads" / "All-project-files-End-folders-Plus-Project-context.worktrees",
                home / "Downloads" / "all-of-the-projects" / "projects",
                home / "OneDrive" / "Documents",
                home / "Documents" / "Codex",
            ]

    resolved: list[Path] = []
    seen: set[str] = set()
    for raw in raw_roots:
        try:
            path = Path(raw).expanduser().resolve()
        except Exception:  # pylint: disable=broad-exception-caught
            path = Path(raw)
        key = str(path).lower()
        if key not in seen:
            resolved.append(path)
            seen.add(key)
    return resolved


def _discover_repos(
    roots: Iterable[Path],
    *,
    max_depth: int,
    max_repos: int,
) -> tuple[list[Path], list[str], list[str], bool]:
    repos: list[Path] = []
    roots_scanned: list[str] = []
    roots_missing: list[str] = []
    seen: set[str] = set()
    truncated = False

    for root in roots:
        if not root.exists():
            roots_missing.append(str(root))
            continue
        roots_scanned.append(str(root))
        queue: deque[tuple[Path, int]] = deque([(root, 0)])
        while queue:
            current, depth = queue.popleft()
            git_marker = current / ".git"
            if git_marker.exists():
                key = str(current).lower()
                if key not in seen:
                    repos.append(current)
                    seen.add(key)
                    if len(repos) >= max_repos:
                        truncated = True
                        return repos, roots_scanned, roots_missing, truncated
                continue
            if depth >= max_depth:
                continue
            for child in _iter_child_dirs(current):
                queue.append((child, depth + 1))

    repos.sort(key=lambda path: str(path).lower())
    return repos, roots_scanned, roots_missing, truncated


def _iter_child_dirs(path: Path) -> list[Path]:
    try:
        children = []
        for child in path.iterdir():
            if child.is_dir() and child.name not in _SKIP_DIRS:
                children.append(child)
        return sorted(children, key=lambda item: item.name.lower())
    except Exception:  # pylint: disable=broad-exception-caught
        return []


def _inspect_repo(path: Path) -> dict[str, Any]:
    git_dir = _git_dir(path)
    package = _package_info(path)
    env = _env_info(path)
    branch = _branch_name(git_dir)
    remote_url = _remote_url(git_dir)
    row = {
        "id": _stable_id(path),
        "name": path.name,
        "path": str(path),
        "path_ref": f"repo:{path.name}:{_stable_id(path)}",
        "branch": branch,
        "remote_url": _redact_url(remote_url),
        "package_name": package.get("package_name", ""),
        "package_manager": package.get("package_manager", ""),
        "dependency_count": package.get("dependency_count", 0),
        "dependency_versions": package.get("dependency_versions", {}),
        "local_dependencies": package.get("local_dependencies", []),
        "ports": _dedupe_rows([*package.get("ports", []), *env.get("ports", [])], ("port", "source")),
        "env_keys_present": env.get("env_keys_present", []),
        "node_refs": _dedupe_rows(env.get("node_refs", []), ("value", "source")),
    }
    return row


def _git_dir(repo_path: Path) -> Path:
    marker = repo_path / ".git"
    try:
        if marker.is_dir():
            return marker
        text = marker.read_text(encoding="utf-8", errors="replace").strip()
        if text.lower().startswith("gitdir:"):
            raw = text.split(":", 1)[1].strip()
            path = Path(raw)
            if not path.is_absolute():
                path = repo_path / path
            return path.resolve()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return marker


def _git_config_path(git_dir: Path) -> Path:
    direct = git_dir / "config"
    if direct.exists():
        return direct
    try:
        common_raw = (git_dir / "commondir").read_text(encoding="utf-8", errors="replace").strip()
        common = Path(common_raw)
        if not common.is_absolute():
            common = git_dir / common
        common_config = common.resolve() / "config"
        if common_config.exists():
            return common_config
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return direct


def _remote_url(git_dir: Path) -> str:
    config_path = _git_config_path(git_dir)
    if not config_path.exists():
        return ""
    parser = configparser.ConfigParser(strict=False)
    try:
        parser.read_string(config_path.read_text(encoding="utf-8", errors="replace"))
        if parser.has_section('remote "origin"') and parser.has_option('remote "origin"', "url"):
            return parser.get('remote "origin"', "url")
        for section in parser.sections():
            if section.startswith("remote ") and parser.has_option(section, "url"):
                return parser.get(section, "url")
    except Exception:  # pylint: disable=broad-exception-caught
        return ""
    return ""


def _branch_name(git_dir: Path) -> str:
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
        if head.startswith("ref:"):
            return head.rsplit("/", 1)[-1]
        if head:
            return head[:12]
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return "unknown"


def _package_info(repo_path: Path) -> dict[str, Any]:
    package_path = repo_path / "package.json"
    if not package_path.exists():
        return {
            "package_name": "",
            "package_manager": "",
            "dependency_count": 0,
            "dependency_versions": {},
            "local_dependencies": [],
            "ports": [],
        }

    try:
        data = json.loads(package_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # pylint: disable=broad-exception-caught
        return {
            "package_name": "",
            "package_manager": "npm",
            "dependency_count": 0,
            "dependency_versions": {},
            "local_dependencies": [],
            "ports": [],
        }

    dependency_versions: dict[str, str] = {}
    local_dependencies: list[dict[str, Any]] = []
    for field in _DEPENDENCY_FIELDS:
        deps = data.get(field, {})
        if not isinstance(deps, dict):
            continue
        for name, version in deps.items():
            version_text = str(version)
            dependency_versions[name] = version_text
            local_dep = _local_dependency(repo_path, field, name, version_text)
            if local_dep:
                local_dependencies.append(local_dep)

    ports: list[dict[str, Any]] = []
    scripts = data.get("scripts", {})
    if isinstance(scripts, dict):
        for script_name, script_value in scripts.items():
            ports.extend(_ports_from_text(str(script_value), f"package:scripts.{script_name}"))

    return {
        "package_name": str(data.get("name", "")),
        "package_manager": _package_manager(repo_path),
        "dependency_count": len(dependency_versions),
        "dependency_versions": dependency_versions,
        "local_dependencies": local_dependencies,
        "ports": _dedupe_rows(ports, ("port", "source")),
    }


def _local_dependency(repo_path: Path, field: str, name: str, version: str) -> dict[str, Any] | None:
    prefixes = ("file:", "link:")
    if version.startswith(prefixes):
        raw_target = version.split(":", 1)[1]
    elif version.startswith("workspace:"):
        raw_target = version.split(":", 1)[1]
        if raw_target in ("*", "^", "~", ""):
            return {"name": name, "field": field, "specifier": version, "target_path": ""}
    else:
        return None

    target_path = Path(raw_target)
    if not target_path.is_absolute():
        target_path = repo_path / target_path
    try:
        target = str(target_path.resolve())
    except Exception:  # pylint: disable=broad-exception-caught
        target = str(target_path)
    return {"name": name, "field": field, "specifier": version, "target_path": target}


def _package_manager(repo_path: Path) -> str:
    if (repo_path / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo_path / "yarn.lock").exists():
        return "yarn"
    if (repo_path / "package-lock.json").exists():
        return "npm"
    if (repo_path / "package.json").exists():
        return "npm"
    return ""


def _env_info(repo_path: Path) -> dict[str, Any]:
    keys: list[str] = []
    ports: list[dict[str, Any]] = []
    node_refs: list[dict[str, Any]] = []
    for name in _ENV_FILES:
        path = repo_path / name
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not key:
                    continue
                keys.append(key)
                source = f"{name}:{key}"
                secret = _is_secret_key(key)
                if not secret:
                    ports.extend(
                        _ports_from_text(value, source, allow_bare_number=bool(_PORT_KEY_RE.search(key)))
                    )
                    if _NODE_KEY_RE.search(key) and value:
                        node_refs.append({"value": _safe_value(value), "source": source})
        except Exception:  # pylint: disable=broad-exception-caught
            continue

    return {
        "env_keys_present": sorted(set(keys)),
        "ports": _dedupe_rows(ports, ("port", "source")),
        "node_refs": _dedupe_rows(node_refs, ("value", "source")),
    }


def _ports_from_text(text: str, source: str, *, allow_bare_number: bool = False) -> list[dict[str, Any]]:
    ports: list[dict[str, Any]] = []
    for pattern in (_LOCALHOST_PORT_RE, _FLAG_PORT_RE):
        for match in pattern.finditer(text):
            port = _valid_port(match.group(1))
            if port:
                ports.append({"port": port, "source": source})
    if allow_bare_number and text.strip().isdigit():
        port = _valid_port(text.strip())
        if port:
            ports.append({"port": port, "source": source})
    return _dedupe_rows(ports, ("port", "source"))


def _valid_port(value: str) -> int | None:
    try:
        port = int(value)
    except ValueError:
        return None
    if 1 <= port <= 65535:
        return port
    return None


def _detect_collisions(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collisions: list[dict[str, Any]] = []
    collisions.extend(_group_collisions(repos, "remote_url", "remote_duplicate", "warning"))
    collisions.extend(_group_collisions(repos, "name", "repo_name_duplicate", "info"))
    collisions.extend(_group_collisions(repos, "package_name", "package_name_duplicate", "info"))

    port_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for repo in repos:
        for port in repo.get("ports", []):
            port_map[port["port"]].append(repo)
    for port, rows in sorted(port_map.items()):
        unique = _unique_repos(rows)
        if len(unique) > 1:
            collisions.append(_collision("port_collision", "warning", str(port), unique))

    node_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for repo in repos:
        for node in repo.get("node_refs", []):
            if node.get("value"):
                node_map[str(node["value"]).lower()].append(repo)
    for node, rows in sorted(node_map.items()):
        unique = _unique_repos(rows)
        if len(unique) > 1:
            collisions.append(_collision("node_ref_collision", "warning", node, unique))

    collisions.extend(_local_dependency_collisions(repos))
    collisions.extend(_dependency_version_drift(repos))
    collisions.sort(key=lambda item: (_severity_rank(item["severity"]), item["type"], item["key"]))
    return collisions[:100]


def _group_collisions(
    repos: list[dict[str, Any]],
    field: str,
    collision_type: str,
    severity: str,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for repo in repos:
        value = str(repo.get(field, "")).strip()
        if value:
            groups[value.lower()].append(repo)
    return [
        _collision(collision_type, severity, key, rows)
        for key, rows in sorted(groups.items())
        if len(rows) > 1
    ]


def _local_dependency_collisions(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collisions: list[dict[str, Any]] = []
    for repo in repos:
        repo_path = Path(repo["path"])
        for dep in repo.get("local_dependencies", []):
            target_raw = dep.get("target_path", "")
            if not target_raw:
                collisions.append({
                    "type": "workspace_dependency",
                    "severity": "info",
                    "key": dep.get("name", ""),
                    "repo_refs": [repo["path_ref"]],
                    "repo_names": [repo["name"]],
                    "detail": f"{dep.get('name')} uses {dep.get('specifier')}",
                })
                continue
            target = Path(target_raw)
            for other in repos:
                if other is repo:
                    continue
                other_path = Path(other["path"])
                if _is_inside(target, other_path):
                    collisions.append({
                        "type": "local_dependency_cross_project",
                        "severity": "warning",
                        "key": dep.get("name", ""),
                        "repo_refs": [repo["path_ref"], other["path_ref"]],
                        "repo_names": [repo["name"], other["name"]],
                        "detail": (
                            f"{repo['name']} depends on {dep.get('name')} from "
                            f"{other['path_ref']} via {dep.get('specifier')}"
                        ),
                    })
                    break
            if _is_inside(target, repo_path):
                continue
    return collisions


def _dependency_version_drift(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dep_map: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for repo in repos:
        for name, version in repo.get("dependency_versions", {}).items():
            if name.startswith("@types/"):
                continue
            dep_map[name][version].append(repo)

    collisions: list[dict[str, Any]] = []
    for name, version_map in dep_map.items():
        if len(version_map) <= 1:
            continue
        rows = _unique_repos([repo for repos_for_version in version_map.values() for repo in repos_for_version])
        if len(rows) <= 1:
            continue
        detail_versions = ", ".join(sorted(version_map.keys())[:5])
        collisions.append(
            _collision(
                "dependency_version_drift",
                "info",
                name,
                rows,
                detail=f"versions: {detail_versions}",
            )
        )
    return collisions[:25]


def _collision(
    collision_type: str,
    severity: str,
    key: str,
    rows: list[dict[str, Any]],
    *,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "type": collision_type,
        "severity": severity,
        "key": key,
        "repo_refs": [row["path_ref"] for row in rows],
        "repo_names": [row["name"] for row in rows],
        "detail": detail or f"{len(rows)} repos share {key}",
    }


def _unique_repos(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        key = row["path_ref"]
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique


def _severity_counts(collisions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for collision in collisions:
        severity = collision.get("severity", "info")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "warning": 1, "info": 2}.get(severity, 3)


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _stable_id(path: Path) -> str:
    return hashlib.sha256(str(path).lower().encode("utf-8")).hexdigest()[:12]


def _redact_url(url: str) -> str:
    if not url:
        return ""
    return _URL_CREDENTIAL_RE.sub(r"\1***@", url)


def _safe_value(value: str) -> str:
    return _URL_CREDENTIAL_RE.sub(r"\1***@", value.strip())


def _is_secret_key(key: str) -> bool:
    return bool(_SECRET_KEY_RE.search(key))


def _dedupe_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        marker = tuple(row.get(key) for key in keys)
        if marker not in seen:
            result.append(row)
            seen.add(marker)
    return result

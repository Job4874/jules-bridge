"""Agent Knowledge Context checkpoint module.

AKC turns source material such as transcripts, project context, and notes into
a compact, source-backed checkpoint that agents can load before daily work.

Public interface:
    build_akc_context(source_paths, checkpoint_path) -> AKCContext
    load_akc_checkpoint(checkpoint_path) -> AKCCheckpoint
    check_akc_readiness(checkpoint_path, required_rules) -> AKCReadiness
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class AKCContext(dict):
    """Keys: status, sources, operating_rules, checkpoint_markdown."""


class AKCCheckpoint(dict):
    """Keys: exists, checkpoint_path, content, char_count."""


class AKCReadiness(dict):
    """Keys: status, ready, gates, required_rules, present_rules."""


# ---------------------------------------------------------------------------
# Rule catalog
# ---------------------------------------------------------------------------

_DEFAULT_REQUIRED_RULES = (
    "context_system",
    "grill_alignment",
    "tdd_feedback",
    "evidence_gates",
    "deep_modules",
    "ralph_loop",
    "hrm_reasoning",
    "smart_zone",
    "google_drive_cloud",
)

_STATUS_RE = re.compile(r"^- status:\s*([^\s]+)\s*$", re.MULTILINE)
_RULE_KEY_RE = re.compile(r"^- `([^`]+)`:", re.MULTILINE)

_RULES = [
    {
        "key": "context_system",
        "keywords": ("context file", "context files", "project context", "agent.md", "agents.md"),
        "summary": (
            "Load compact, source-backed project context before implementation "
            "and keep progress trackers current."
        ),
    },
    {
        "key": "grill_alignment",
        "keywords": ("grill", "shared design concept", "shared understanding", "design concept"),
        "summary": (
            "Use a grill/alignment pass before PRDs, tickets, or coding on "
            "non-trivial work."
        ),
    },
    {
        "key": "tdd_feedback",
        "keywords": ("tdd", "test-driven", "test driven", "feedback loop", "feedback loops"),
        "summary": (
            "Use TDD and short feedback loops: write the test first, make it "
            "pass, then refactor."
        ),
    },
    {
        "key": "evidence_gates",
        "keywords": ("evidence", "prove", "sha-256", "sha256", "verification", "verified"),
        "summary": (
            "Treat tests, hashes, screenshots, and runtime output as required "
            "evidence before trusting completion claims."
        ),
    },
    {
        "key": "deep_modules",
        "keywords": ("deep module", "deep modules", "simple interface", "simple interfaces"),
        "summary": (
            "Prefer deep modules with simple interfaces and test at the module "
            "boundary."
        ),
    },
    {
        "key": "ralph_loop",
        "keywords": ("ralph", "one ticket", "ticket", "loop"),
        "summary": (
            "Drive autonomous work through one focused ticket at a time, with "
            "tests and evidence before the next loop."
        ),
    },
    {
        "key": "hrm_reasoning",
        "keywords": ("hrm", "high-level", "low-level", "planner", "worker", "halting"),
        "summary": (
            "Separate high-level planning from low-level execution and use "
            "budgeted halting checks."
        ),
    },
    {
        "key": "smart_zone",
        "keywords": ("smart zone", "dumb zone", "context window", "clear the context", "compact"),
        "summary": (
            "Keep tasks inside the model smart zone; checkpoint durable context "
            "instead of bloating one session."
        ),
    },
    {
        "key": "google_drive_cloud",
        "keywords": ("google drive", "google cloud", "cloud", "storage"),
        "summary": (
            "Use Google Drive or Google Cloud as external storage only with "
            "explicit source inventory and verified integration state."
        ),
    },
]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _path_ref(path: str) -> str:
    """Return a stable redacted reference for a local path."""
    normalized = os.path.abspath(path).lower()
    digest = hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()
    return f"path-ref:{digest[:12]}"


def _read_source(path: str) -> dict:
    """Read one source file and return a redacted inventory row."""
    ref = _path_ref(path)
    name = os.path.basename(path) or "source"
    try:
        raw_bytes = Path(path).read_bytes()
        text = raw_bytes.decode("utf-8", errors="replace")
        return {
            "name": name,
            "path_ref": ref,
            "readable": True,
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "byte_count": len(raw_bytes),
            "line_count": len(text.splitlines()),
            "char_count": len(text),
            "error": "",
            "_text": text,
        }
    except OSError as exc:
        return {
            "name": name,
            "path_ref": ref,
            "readable": False,
            "sha256": "",
            "byte_count": 0,
            "line_count": 0,
            "char_count": 0,
            "error": f"{exc.__class__.__name__}: unreadable source",
            "_text": "",
        }


def _extract_rules(source_rows: Iterable[dict]) -> List[dict]:
    """Extract operating rules by matching the curated rule catalog."""
    combined = "\n".join(row.get("_text", "") for row in source_rows).lower()
    rules = []
    for rule in _RULES:
        matches = [keyword for keyword in rule["keywords"] if keyword in combined]
        if matches:
            rules.append({
                "key": rule["key"],
                "summary": rule["summary"],
                "matched_terms": matches[:5],
            })
    return rules


def _status(readable_count: int, missing_count: int, rule_count: int) -> str:
    """Return checkpoint status from evidence strength."""
    if readable_count == 0:
        return "blocked"
    if missing_count > 0:
        return "partial"
    if rule_count >= 5:
        return "ready"
    return "partial"


def _public_sources(source_rows: Iterable[dict]) -> List[dict]:
    """Strip raw text from source rows before returning or writing."""
    public = []
    for row in source_rows:
        public.append({
            "name": row["name"],
            "path_ref": row["path_ref"],
            "readable": row["readable"],
            "sha256": row["sha256"],
            "byte_count": row["byte_count"],
            "line_count": row["line_count"],
            "char_count": row["char_count"],
            "error": row["error"],
        })
    return public


def _render_checkpoint(
    status: str,
    source_rows: List[dict],
    operating_rules: List[dict],
) -> str:
    """Render source inventory and rules to markdown."""
    now = datetime.now(timezone.utc).isoformat()
    public_sources = _public_sources(source_rows)
    lines = [
        "# AKC Context Checkpoint",
        "",
        f"- generated_at_utc: {now}",
        f"- status: {status}",
        f"- source_count: {len(public_sources)}",
        f"- readable_count: {sum(1 for row in public_sources if row['readable'])}",
        f"- missing_count: {sum(1 for row in public_sources if not row['readable'])}",
        f"- operating_rule_count: {len(operating_rules)}",
        "",
        "## Source Inventory",
        "",
        "| name | path_ref | readable | sha256 | lines | bytes |",
        "|---|---|---:|---|---:|---:|",
    ]
    for row in public_sources:
        sha = row["sha256"][:16] if row["sha256"] else ""
        lines.append(
            f"| {row['name']} | {row['path_ref']} | {row['readable']} | "
            f"{sha} | {row['line_count']} | {row['byte_count']} |"
        )

    lines.extend([
        "",
        "## Operating Rules",
        "",
    ])
    for rule in operating_rules:
        terms = ", ".join(rule["matched_terms"])
        lines.append(f"- `{rule['key']}`: {rule['summary']} Matched: {terms}.")

    lines.extend([
        "",
        "## Daily Loop",
        "",
        "1. Load this checkpoint and the core context files.",
        "2. Grill for alignment before non-trivial planning.",
        "3. Convert aligned work into one focused ticket.",
        "4. Use TDD at the module boundary.",
        "5. Record evidence before review or completion claims.",
        "",
    ])
    return "\n".join(lines)


def _write_checkpoint(path: str, markdown: str) -> None:
    """Write checkpoint markdown to disk."""
    checkpoint = Path(path)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(markdown, encoding="utf-8")


def _checkpoint_status(content: str) -> str:
    """Parse the checkpoint status line from rendered markdown."""
    match = _STATUS_RE.search(content)
    if not match:
        return "unknown"
    return match.group(1).strip().lower()


def _checkpoint_rule_keys(content: str) -> List[str]:
    """Parse operating rule keys from rendered checkpoint markdown."""
    keys = []
    seen = set()
    for match in _RULE_KEY_RE.finditer(content):
        key = match.group(1).strip()
        if key and key not in seen:
            keys.append(key)
            seen.add(key)
    return keys


def _gate(name: str, passed: bool, detail: str) -> dict:
    """Return a readiness gate row."""
    return {"name": name, "passed": passed, "detail": detail}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def build_akc_context(
    source_paths: Optional[Iterable[str]] = None,
    checkpoint_path: Optional[str] = None,
) -> AKCContext:
    """Build an AKC checkpoint from source files.

    Args:
        source_paths: Iterable of source file paths. Paths are read locally but
            never returned verbatim; API output uses path-ref masking.
        checkpoint_path: Optional markdown file to write. If omitted, no file is
            written.

    Returns:
        AKCContext with source inventory, extracted operating rules, and
        rendered checkpoint markdown.

    Never raises for missing or unreadable sources; they are inventoried.
    """
    paths = list(source_paths or [])
    source_rows = [_read_source(path) for path in paths]
    rules = _extract_rules(source_rows)
    readable_count = sum(1 for row in source_rows if row["readable"])
    missing_count = sum(1 for row in source_rows if not row["readable"])
    status = _status(readable_count, missing_count, len(rules))
    markdown = _render_checkpoint(status, source_rows, rules)

    checkpoint_ref = ""
    if checkpoint_path:
        try:
            _write_checkpoint(checkpoint_path, markdown)
            checkpoint_ref = _path_ref(checkpoint_path)
        except OSError:
            status = "partial" if readable_count else "blocked"

    return AKCContext({
        "status": status,
        "source_count": len(source_rows),
        "readable_count": readable_count,
        "missing_count": missing_count,
        "sources": _public_sources(source_rows),
        "operating_rules": rules,
        "checkpoint_path": checkpoint_ref,
        "checkpoint_markdown": markdown,
    })


def load_akc_checkpoint(checkpoint_path: Optional[str] = None) -> AKCCheckpoint:
    """Load an AKC checkpoint markdown file.

    Args:
        checkpoint_path: Markdown path to load.

    Returns:
        AKCCheckpoint with redacted path reference and content if present.

    Never raises for a missing checkpoint.
    """
    path = checkpoint_path or os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "context",
        "08_akc_context_checkpoint.md",
    )
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
        return AKCCheckpoint({
            "exists": True,
            "checkpoint_path": _path_ref(path),
            "content": content,
            "char_count": len(content),
        })
    except OSError:
        return AKCCheckpoint({
            "exists": False,
            "checkpoint_path": _path_ref(path),
            "content": "",
            "char_count": 0,
        })


def check_akc_readiness(
    checkpoint_path: Optional[str] = None,
    required_rules: Optional[Iterable[str]] = None,
) -> AKCReadiness:
    """Check whether the AKC checkpoint is ready for session start.

    Args:
        checkpoint_path: Optional markdown checkpoint path to verify.
        required_rules: Optional operating rule keys that must be present.

    Returns:
        AKCReadiness with gate results, parsed checkpoint status, and missing
        required rule keys.

    Never raises; a missing checkpoint returns blocked readiness.
    """
    checkpoint = load_akc_checkpoint(checkpoint_path=checkpoint_path)
    rules_required = list(required_rules or _DEFAULT_REQUIRED_RULES)
    present_rules = _checkpoint_rule_keys(checkpoint["content"])
    present_set = set(present_rules)
    missing_rules = [rule for rule in rules_required if rule not in present_set]
    checkpoint_status = _checkpoint_status(checkpoint["content"])

    exists = bool(checkpoint["exists"])
    status_ready = checkpoint_status == "ready"
    rules_ready = not missing_rules
    ready = exists and status_ready and rules_ready

    if ready:
        status = "ready"
    elif not exists or checkpoint_status == "blocked":
        status = "blocked"
    else:
        status = "partial"

    gates = [
        _gate(
            "checkpoint_exists",
            exists,
            "present" if exists else "checkpoint file is missing",
        ),
        _gate(
            "checkpoint_ready",
            exists and status_ready,
            f"status={checkpoint_status}",
        ),
        _gate(
            "required_rules_present",
            rules_ready,
            "all present" if rules_ready else "missing: " + ", ".join(missing_rules),
        ),
    ]

    return AKCReadiness({
        "status": status,
        "ready": ready,
        "checkpoint_exists": exists,
        "checkpoint_status": checkpoint_status,
        "checkpoint_path": checkpoint["checkpoint_path"],
        "char_count": checkpoint["char_count"],
        "required_rules": rules_required,
        "present_rules": present_rules,
        "missing_required_rules": missing_rules,
        "gates": gates,
    })

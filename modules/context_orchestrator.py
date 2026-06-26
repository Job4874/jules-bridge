"""Context sub-agent planning.

This module turns large source material into budgeted context capsules and
role-specific sub-agent packets. It keeps the main conversation small while
preserving enough head/tail evidence and source fingerprints for follow-up
retrieval.

Public interface:
    build_context_subagents(...) -> ContextSubagentPlan
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class ContextSource(dict):
    """A source inventory row with redacted path metadata."""


class ContextCapsule(dict):
    """A smart-truncated source capsule."""


class ContextSubagent(dict):
    """A role-specific sub-agent packet."""


class ContextSubagentPlan(dict):
    """A complete context-handling plan."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "jules_inbox" / "context_subagents"
_DEFAULT_HEAD_CHARS = 800
_DEFAULT_TAIL_CHARS = 800
_DEFAULT_PACKET_CHARS = 12000
_MIN_EXCERPT_CHARS = 80
_DEFAULT_ROLES = (
    {
        "id": "context_cartographer",
        "title": "Context Cartographer",
        "mission": "Inventory source shape, durable rules, risks, and retrieval needs.",
        "deliverables": (
            "source inventory",
            "operating rules",
            "missing or risky source notes",
        ),
    },
    {
        "id": "memory_curator",
        "title": "Memory Curator",
        "mission": "Separate what belongs in active context from what should survive as memory.",
        "deliverables": (
            "memory candidates",
            "discardable middle sections",
            "follow-up retrieval keys",
        ),
    },
    {
        "id": "implementation_planner",
        "title": "Implementation Planner",
        "mission": "Convert the context into narrow module, route, and test work.",
        "deliverables": (
            "module boundary",
            "route contract",
            "test plan",
        ),
    },
    {
        "id": "verification_agent",
        "title": "Verification Agent",
        "mission": "Define evidence gates, long-session evals, and completion criteria.",
        "deliverables": (
            "verification commands",
            "context quality checks",
            "completion evidence",
        ),
    },
)
_SIGNALS = (
    ("context_engineering", ("context engineering", "context management", "context window")),
    ("smart_truncation", ("smart truncation", "head", "tail", "truncate")),
    ("memory_store", ("memory store", "long-term memory", "memory decides")),
    ("subagents", ("sub agents", "subagents", "sub-agent", "delegate")),
    ("long_session_evals", ("long session", "11th", "eval")),
    ("tdd", ("tdd", "test-driven", "test driven")),
    ("evidence", ("evidence", "sha-256", "sha256", "verification")),
    ("hrm", ("hrm", "high-level", "low-level", "halting")),
)
_LOCAL_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s`'\"|<>\]]+")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def build_context_subagents(
    content: str = "",
    source_paths: Iterable[str] | None = None,
    task: str = "",
    roles: Iterable[str] | None = None,
    head_chars: int = _DEFAULT_HEAD_CHARS,
    tail_chars: int = _DEFAULT_TAIL_CHARS,
    max_packet_chars: int = _DEFAULT_PACKET_CHARS,
    write_packets: bool = False,
    output_dir: str = "",
) -> ContextSubagentPlan:
    """Build budgeted context capsules and sub-agent packets.

    Args:
        content: Optional inline source material.
        source_paths: Optional file paths to read. Paths are hashed in public
            output and are not rendered into packet text.
        task: Operator goal for the context sub-agents.
        roles: Optional role ids from the default role catalog.
        head_chars: Characters to keep from each source head.
        tail_chars: Characters to keep from each source tail.
        max_packet_chars: Per-packet character budget.
        write_packets: If true, write markdown packets and an index.
        output_dir: Destination directory. Defaults to jules_inbox/context_subagents.

    Returns:
        ContextSubagentPlan. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        source_rows = _load_sources(content=content, source_paths=source_paths)
        readable_rows = [row for row in source_rows if row.get("readable")]
        missing_count = sum(1 for row in source_rows if not row.get("readable"))
        if not source_rows:
            return ContextSubagentPlan(
                error="content or source_paths is required",
                generated_at_utc=generated_at,
                status="blocked",
                source_count=len(source_rows),
                readable_count=0,
                missing_count=missing_count,
                sources=_public_sources(source_rows),
                capsules=[],
                subagents=[],
                packet_files=[],
                plan_markdown="",
            )
        if not readable_rows:
            return ContextSubagentPlan(
                error="no readable source content",
                generated_at_utc=generated_at,
                status="blocked",
                source_count=len(source_rows),
                readable_count=0,
                missing_count=missing_count,
                sources=_public_sources(source_rows),
                capsules=[],
                subagents=[],
                packet_files=[],
                plan_markdown="",
            )

        head = max(_MIN_EXCERPT_CHARS, int(head_chars or _DEFAULT_HEAD_CHARS))
        tail = max(_MIN_EXCERPT_CHARS, int(tail_chars or _DEFAULT_TAIL_CHARS))
        packet_budget = max(1000, int(max_packet_chars or _DEFAULT_PACKET_CHARS))
        selected_roles = _select_roles(roles)
        capsules = [
            _capsule_for_source(row, head_chars=head, tail_chars=tail)
            for row in readable_rows
        ]
        metrics = _context_metrics(capsules)
        subagents = [
            _subagent_for_role(
                role=role,
                task=task,
                capsules=capsules,
                metrics=metrics,
                max_packet_chars=packet_budget,
            )
            for role in selected_roles
        ]
        status = "partial" if missing_count else "ready"
        output = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
        packet_files: list[str] = []
        if write_packets:
            packet_files = _write_packets(
                subagents=subagents,
                output_dir=output,
                generated_at=generated_at,
                task=task,
                metrics=metrics,
            )
        plan_markdown = _plan_markdown(
            generated_at=generated_at,
            status=status,
            task=task,
            sources=_public_sources(source_rows),
            metrics=metrics,
            subagents=subagents,
            packet_files=packet_files,
        )
        return ContextSubagentPlan(
            generated_at_utc=generated_at,
            status=status,
            task=task,
            source_count=len(source_rows),
            readable_count=len(readable_rows),
            missing_count=missing_count,
            context_strategy="smart_truncation_head_tail_memory_store",
            head_chars=head,
            tail_chars=tail,
            max_packet_chars=packet_budget,
            sources=_public_sources(source_rows),
            capsules=capsules,
            context_metrics=metrics,
            subagents=subagents,
            write_packets=write_packets,
            output_dir=str(output),
            packet_files=packet_files,
            plan_markdown=plan_markdown,
            note=(
                "Packets are offline context-handling briefs. They do not launch "
                "remote Jules sessions."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return ContextSubagentPlan(
            error=str(exc),
            generated_at_utc=generated_at,
            status="error",
            source_count=0,
            readable_count=0,
            missing_count=0,
            sources=[],
            capsules=[],
            subagents=[],
            packet_files=[],
            plan_markdown="",
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_sources(content: str, source_paths: Iterable[str] | None) -> list[dict]:
    rows: list[dict] = []
    if content:
        raw = content.encode("utf-8", errors="replace")
        rows.append({
            "name": "inline-content",
            "path_ref": "inline",
            "readable": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw),
            "line_count": len(content.splitlines()),
            "char_count": len(content),
            "error": "",
            "_text": content,
        })
    for path in source_paths or []:
        rows.append(_read_source(path))
    return rows


def _read_source(path: str) -> dict:
    source = Path(path)
    try:
        raw = source.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        return {
            "name": source.name or "source",
            "path_ref": _path_ref(path),
            "readable": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw),
            "line_count": len(text.splitlines()),
            "char_count": len(text),
            "error": "",
            "_text": text,
        }
    except OSError as exc:
        return {
            "name": source.name or "source",
            "path_ref": _path_ref(path),
            "readable": False,
            "sha256": "",
            "byte_count": 0,
            "line_count": 0,
            "char_count": 0,
            "error": f"{exc.__class__.__name__}: unreadable source",
            "_text": "",
        }


def _path_ref(path: str) -> str:
    normalized = str(Path(path).absolute()).lower()
    digest = hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()
    return f"path-ref:{digest[:12]}"


def _public_sources(rows: Iterable[dict]) -> list[ContextSource]:
    public = []
    for row in rows:
        public.append(ContextSource({
            "name": row.get("name", ""),
            "path_ref": row.get("path_ref", ""),
            "readable": bool(row.get("readable")),
            "sha256": row.get("sha256", ""),
            "byte_count": int(row.get("byte_count") or 0),
            "line_count": int(row.get("line_count") or 0),
            "char_count": int(row.get("char_count") or 0),
            "error": row.get("error", ""),
        }))
    return public


def _capsule_for_source(row: dict, head_chars: int, tail_chars: int) -> ContextCapsule:
    text = row.get("_text", "") or ""
    char_count = len(text)
    if char_count <= head_chars + tail_chars:
        head = text
        tail = ""
        middle = ""
    else:
        head = text[:head_chars]
        tail = text[-tail_chars:]
        middle = text[head_chars:-tail_chars]
    redacted_head = _redact_local_paths(head)
    redacted_tail = _redact_local_paths(tail)
    signals = _extract_signals(text)
    return ContextCapsule({
        "name": row.get("name", ""),
        "path_ref": row.get("path_ref", ""),
        "sha256": row.get("sha256", ""),
        "char_count": char_count,
        "line_count": int(row.get("line_count") or 0),
        "head": redacted_head,
        "tail": redacted_tail,
        "head_char_count": len(redacted_head),
        "tail_char_count": len(redacted_tail),
        "omitted_middle_char_count": len(middle),
        "omitted_middle_sha256": _sha256_text(middle) if middle else "",
        "signals": signals,
        "retrieval_hint": (
            "Use the source sha256/path_ref to retrieve omitted middle content "
            "only when needed."
        ),
    })


def _extract_signals(text: str) -> list[str]:
    lower = (text or "").lower()
    signals = []
    for key, terms in _SIGNALS:
        if any(term in lower for term in terms):
            signals.append(key)
    return signals


def _redact_local_paths(text: str) -> str:
    return _LOCAL_PATH_RE.sub("path-redacted", text or "")


def _context_metrics(capsules: Iterable[ContextCapsule]) -> dict:
    rows = list(capsules)
    total_chars = sum(int(row.get("char_count") or 0) for row in rows)
    prompt_chars = sum(
        int(row.get("head_char_count") or 0) + int(row.get("tail_char_count") or 0)
        for row in rows
    )
    omitted_chars = sum(int(row.get("omitted_middle_char_count") or 0) for row in rows)
    compression_ratio = round(prompt_chars / total_chars, 4) if total_chars else 0
    signal_counts: dict[str, int] = {}
    for row in rows:
        for signal in row.get("signals", []):
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
    return {
        "source_count": len(rows),
        "total_source_chars": total_chars,
        "active_prompt_chars": prompt_chars,
        "omitted_middle_chars": omitted_chars,
        "compression_ratio": compression_ratio,
        "signal_counts": signal_counts,
    }


def _select_roles(roles: Iterable[str] | None) -> list[dict]:
    by_id = {role["id"]: role for role in _DEFAULT_ROLES}
    requested = [str(role).strip() for role in roles or [] if str(role).strip()]
    if not requested:
        return [dict(role) for role in _DEFAULT_ROLES]
    selected = []
    seen = set()
    for role_id in requested:
        if role_id in by_id and role_id not in seen:
            selected.append(dict(by_id[role_id]))
            seen.add(role_id)
    return selected or [dict(role) for role in _DEFAULT_ROLES]


def _subagent_for_role(
    role: dict,
    task: str,
    capsules: list[ContextCapsule],
    metrics: dict,
    max_packet_chars: int,
) -> ContextSubagent:
    excerpt_chars = min(_DEFAULT_HEAD_CHARS, _DEFAULT_TAIL_CHARS)
    packet = _packet_text(role, task, capsules, metrics, excerpt_chars)
    while len(packet) > max_packet_chars and excerpt_chars > _MIN_EXCERPT_CHARS:
        excerpt_chars = max(_MIN_EXCERPT_CHARS, excerpt_chars // 2)
        packet = _packet_text(role, task, capsules, metrics, excerpt_chars)
    if len(packet) > max_packet_chars:
        packet = _packet_text(role, task, capsules, metrics, 0)
    return ContextSubagent({
        "id": f"CA-{role['id']}",
        "role_id": role["id"],
        "title": role["title"],
        "mission": role["mission"],
        "deliverables": list(role["deliverables"]),
        "context_refs": [capsule.get("path_ref", "") for capsule in capsules],
        "packet_text": packet,
        "packet_char_count": len(packet),
        "within_budget": len(packet) <= max_packet_chars,
        "max_packet_chars": max_packet_chars,
    })


def _packet_text(
    role: dict,
    task: str,
    capsules: list[ContextCapsule],
    metrics: dict,
    excerpt_chars: int,
) -> str:
    lines = [
        f"# Context Sub-Agent Packet: {role['title']}",
        "",
        f"- role_id: {role['id']}",
        f"- mission: {role['mission']}",
        f"- task: {task or '(operator task not specified)'}",
        f"- context_strategy: smart_truncation_head_tail_memory_store",
        f"- source_count: {metrics.get('source_count', 0)}",
        f"- active_prompt_chars: {metrics.get('active_prompt_chars', 0)}",
        f"- omitted_middle_chars: {metrics.get('omitted_middle_chars', 0)}",
        f"- compression_ratio: {metrics.get('compression_ratio', 0)}",
        "",
        "## Operating Rules",
        "- Keep the main conversation light; do heavy source analysis inside this packet.",
        "- Use source fingerprints and path refs for retrieval; do not assume omitted middle content is irrelevant.",
        "- Preserve head/tail evidence and ask for retrieval only when the missing middle is necessary.",
        "- Do not reveal private chain-of-thought. Return concise rationale, decisions, and evidence.",
        "",
        "## Deliverables",
    ]
    lines.extend(f"- {item}" for item in role["deliverables"])
    lines.extend([
        "",
        "## Source Capsules",
    ])
    for capsule in capsules:
        lines.extend(_capsule_lines(capsule, excerpt_chars))
    lines.extend([
        "",
        "## Completion Report",
        "Return: findings, decisions, files or routes affected, verification needed, blockers.",
        "",
    ])
    return "\n".join(lines)


def _capsule_lines(capsule: ContextCapsule, excerpt_chars: int) -> list[str]:
    lines = [
        "",
        f"### {capsule.get('name', 'source')}",
        f"- path_ref: {capsule.get('path_ref', '')}",
        f"- sha256: {capsule.get('sha256', '')}",
        f"- chars: {capsule.get('char_count', 0)}",
        f"- omitted_middle_chars: {capsule.get('omitted_middle_char_count', 0)}",
        f"- omitted_middle_sha256: {capsule.get('omitted_middle_sha256', '')}",
        f"- signals: {', '.join(capsule.get('signals', [])) or '(none)'}",
    ]
    if excerpt_chars <= 0:
        lines.append("- excerpts: omitted from this packet to stay within budget")
        return lines
    head = _clip(str(capsule.get("head", "")), excerpt_chars)
    tail = _clip(str(capsule.get("tail", "")), excerpt_chars)
    lines.extend([
        "",
        "Head:",
        "```text",
        head,
        "```",
    ])
    if tail:
        lines.extend([
            "",
            "Tail:",
            "```text",
            tail,
            "```",
        ])
    return lines


def _write_packets(
    subagents: list[ContextSubagent],
    output_dir: Path,
    generated_at: str,
    task: str,
    metrics: dict,
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("CA-*.md"):
        if path.is_file():
            path.unlink()
    packet_files = []
    for subagent in subagents:
        path = output_dir / f"{subagent['id']}.md"
        path.write_text(subagent["packet_text"], encoding="utf-8")
        packet_files.append(str(path))
    index = _index_markdown(generated_at, task, metrics, subagents, packet_files)
    (output_dir / "CONTEXT_SUBAGENT_INDEX.md").write_text(index, encoding="utf-8")
    (output_dir / "CONTEXT_SUBAGENT_STATE.json").write_text(
        json.dumps({
            "generated_at_utc": generated_at,
            "task": task,
            "context_metrics": metrics,
            "packet_files": packet_files,
        }, indent=2),
        encoding="utf-8",
    )
    return packet_files


def _index_markdown(
    generated_at: str,
    task: str,
    metrics: dict,
    subagents: list[ContextSubagent],
    packet_files: list[str],
) -> str:
    lines = [
        "# Context Sub-Agent Index",
        "",
        f"- generated_at_utc: {generated_at}",
        f"- task: {task or '(not specified)'}",
        f"- source_count: {metrics.get('source_count', 0)}",
        f"- active_prompt_chars: {metrics.get('active_prompt_chars', 0)}",
        f"- omitted_middle_chars: {metrics.get('omitted_middle_chars', 0)}",
        "",
        "| id | role | chars | within_budget | packet |",
        "|---|---|---:|---:|---|",
    ]
    for subagent, packet_file in zip(subagents, packet_files):
        lines.append(
            "| {id} | {role} | {chars} | {budget} | {packet} |".format(
                id=subagent.get("id", ""),
                role=subagent.get("role_id", ""),
                chars=subagent.get("packet_char_count", 0),
                budget=subagent.get("within_budget", False),
                packet=packet_file.replace("|", "\\|"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _plan_markdown(
    generated_at: str,
    status: str,
    task: str,
    sources: list[ContextSource],
    metrics: dict,
    subagents: list[ContextSubagent],
    packet_files: list[str],
) -> str:
    lines = [
        "# Context Sub-Agent Plan",
        "",
        f"- generated_at_utc: {generated_at}",
        f"- status: {status}",
        f"- task: {task or '(not specified)'}",
        f"- context_strategy: smart_truncation_head_tail_memory_store",
        f"- active_prompt_chars: {metrics.get('active_prompt_chars', 0)}",
        f"- omitted_middle_chars: {metrics.get('omitted_middle_chars', 0)}",
        f"- compression_ratio: {metrics.get('compression_ratio', 0)}",
        "",
        "## Sources",
        "",
        "| name | path_ref | readable | chars | sha256 |",
        "|---|---|---:|---:|---|",
    ]
    for source in sources:
        sha = str(source.get("sha256", ""))[:16]
        lines.append(
            f"| {source.get('name', '')} | {source.get('path_ref', '')} | "
            f"{source.get('readable', False)} | {source.get('char_count', 0)} | {sha} |"
        )
    lines.extend([
        "",
        "## Sub-Agents",
        "",
        "| id | role | mission | packet |",
        "|---|---|---|---|",
    ])
    packet_by_id = {
        Path(path).stem: path
        for path in packet_files
    }
    for subagent in subagents:
        packet = packet_by_id.get(str(subagent.get("id", "")), "")
        lines.append(
            "| {id} | {role} | {mission} | {packet} |".format(
                id=subagent.get("id", ""),
                role=subagent.get("role_id", ""),
                mission=str(subagent.get("mission", "")).replace("|", "\\|"),
                packet=packet.replace("|", "\\|"),
            )
        )
    lines.extend([
        "",
        "COT here means completion-of-task evidence summaries, not private chain-of-thought.",
        "",
    ])
    return "\n".join(lines)


def _clip(value: str, limit: int) -> str:
    text = value or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[truncated]"


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()

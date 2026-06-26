"""Retrospective deep module — self-improving harness analysis.

Applies Nick Ni's "Case" retrospective agent pattern to Jules Bridge.
See: AI Engineer World Fair 2025, "Building AI Systems That Ship"

Core principle: Every failure is a harness bug.
Every session produces a log. The retrospective reads those logs,
extracts learnings, and writes them to per-domain memory markdown files.

The next agent session that starts will load those memory files and
automatically know what went wrong last time.

Architecture:
  - Reads: bridge.log (structured log lines)
  - Reads: JSONL transcripts from brain/ directory
  - Writes: memory/*.md files (per-domain markdown memory)
  - Writes: memory/test_evidence.json (SHA-256 of test outputs)
  - Returns: RetrospectiveReport with learnings and evidence

Evidence principle (Nick): "I made it easier to just do the work than to lie."
  - SHA-256 hash of actual pytest output stored as cryptographic proof
  - If the hash doesn't match, the tests weren't actually run

Public interface:
    analyze_session(log_path, brain_path, memory_path) -> RetrospectiveReport
    record_test_evidence(test_output, evidence_path) -> TestEvidence
    load_memory(memory_path, domain) -> str
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


LOGGER = logging.getLogger("retrospective")


# ---------------------------------------------------------------------------
# Typed contracts
# ---------------------------------------------------------------------------

@dataclass
class LogPattern:
    """A recurring pattern found in the bridge log."""
    pattern_type: str      # "doom_loop" | "repeated_error" | "slow_route" | "missing_module"
    description: str       # Human-readable description of the pattern
    count: int             # How many times this pattern appears
    examples: List[str]    # Sample log lines exhibiting this pattern


@dataclass
class TestEvidence:
    """Cryptographic proof that tests were actually run (not lied about).

    Nick's SHA-256 approach: store the hash of test output.
    If the hash matches a known pattern, the tests ran and passed.
    If the output is just "tests passed" with no hash, distrust it.
    """
    output_hash: str       # SHA-256 of the full test output
    timestamp_utc: str     # When the tests were run
    passed: bool           # Whether tests passed (from parsing output)
    test_count: int        # Number of tests that ran
    raw_output_tail: str   # Last 5 lines of test output (human-readable)

    @property
    def evidence_line(self) -> str:
        """One-line summary suitable for a memory file."""
        status = "PASSED" if self.passed else "FAILED"
        return f"[{self.timestamp_utc}] Tests: {status} ({self.test_count} tests) sha256:{self.output_hash[:12]}"


@dataclass
class DoomLoop:
    """Detected doom loop in session — same tool called N times with no change."""
    tool_name: str
    call_count: int
    consecutive: bool      # Were the calls back-to-back?
    recommendation: str    # What the harness should do differently


@dataclass
class RetrospectiveReport:
    """Full analysis of a Jules Bridge session.

    Mirrors Nick's Case retrospective agent output:
    - Was it running a lot of tools at the same time?
    - Did it run the same tool request 3 times in a row?
    - Was it getting in a doom loop?
    """
    session_id: str
    analyzed_at_utc: str
    log_lines_analyzed: int
    patterns: List[LogPattern]
    doom_loops: List[DoomLoop]
    learnings: List[str]           # Actionable lessons extracted
    memory_updates: Dict[str, str] # domain -> content written to memory file
    evidence: Optional[TestEvidence]

    @property
    def has_learnings(self) -> bool:
        return len(self.learnings) > 0

    @property
    def has_doom_loops(self) -> bool:
        return len(self.doom_loops) > 0

    def to_summary(self) -> str:
        """Compact summary for inbox or console output."""
        lines = [
            f"Retrospective [{self.session_id}] — {self.analyzed_at_utc}",
            f"  Log lines analyzed: {self.log_lines_analyzed}",
            f"  Patterns found: {len(self.patterns)}",
            f"  Doom loops detected: {len(self.doom_loops)}",
            f"  Learnings extracted: {len(self.learnings)}",
            f"  Memory domains updated: {list(self.memory_updates.keys())}",
        ]
        if self.evidence:
            lines.append(f"  Test evidence: {self.evidence.evidence_line}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

# Patterns that indicate harness problems (not model problems)
_DOOM_LOOP_RE = re.compile(
    r"POST /(?P<route>\w+/\w+)", re.IGNORECASE
)
_ERROR_LINE_RE = re.compile(
    r"\b(ERROR|WARN(?:ING)?)\b", re.IGNORECASE
)
_HTTP_STATUS_RE = re.compile(
    r'(?:->\s*|HTTP/\d(?:\.\d)?"\s+)(?P<status>400|403|404|500|504)(?!\d)',
    re.IGNORECASE,
)
_SLOW_ROUTE_RE = re.compile(
    r"(?:ms=|->\s+\d+\s+)(?P<ms>\d+(?:\.\d+)?)ms", re.IGNORECASE
)
_ROUTE_RE = re.compile(
    r'(?:"|^|\s)(?P<method>GET|POST|PUT|DELETE|PATCH)\s+(?P<path>/[^\s"]+)', re.IGNORECASE
)
_JULES_SHELL_RE = re.compile(
    r"\[JULES SHELL\].*?command=(?P<command>.+)$", re.IGNORECASE
)


def _parse_log_lines(log_path: str) -> List[str]:
    """Read and return log lines from bridge.log."""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except (OSError, FileNotFoundError):
        return []


def _detect_doom_loops(log_lines: List[str]) -> List[DoomLoop]:
    """Detect when the same route is called N times consecutively with no progress."""
    doom_loops: List[DoomLoop] = []
    route_streak: List[str] = []

    for line in log_lines:
        match = _ROUTE_RE.search(line)
        if match:
            route = f"{match.group('method')} {match.group('path')}"
            if route_streak and route_streak[-1] == route:
                route_streak.append(route)
            else:
                # Check if previous streak was a doom loop (3+ same calls)
                if len(route_streak) >= 3:
                    doom_loops.append(DoomLoop(
                        tool_name=route_streak[0],
                        call_count=len(route_streak),
                        consecutive=True,
                        recommendation=(
                            f"Route '{route_streak[0]}' called {len(route_streak)}x consecutively. "
                            "Add a circuit breaker or cache the last response."
                        ),
                    ))
                route_streak = [route]

    # Check final streak
    if len(route_streak) >= 3:
        doom_loops.append(DoomLoop(
            tool_name=route_streak[0],
            call_count=len(route_streak),
            consecutive=True,
            recommendation=(
                f"Route '{route_streak[0]}' called {len(route_streak)}x consecutively. "
                "Add a circuit breaker or cache the last response."
            ),
        ))

    deduped: Dict[str, DoomLoop] = {}
    for loop in doom_loops:
        existing = deduped.get(loop.tool_name)
        if existing is None or loop.call_count > existing.call_count:
            deduped[loop.tool_name] = loop

    return list(deduped.values())


def _detect_error_patterns(log_lines: List[str]) -> List[LogPattern]:
    """Detect recurring error patterns in the log."""
    error_counts: Dict[str, int] = {}
    error_examples: Dict[str, List[str]] = {}
    status_to_key = {
        "500": "internal_error_500",
        "504": "timeout_504",
        "404": "not_found_404",
        "403": "access_denied_403",
        "400": "bad_request_400",
    }

    for line in log_lines:
        status_match = _HTTP_STATUS_RE.search(line)
        error_match = _ERROR_LINE_RE.search(line)

        if status_match:
            key = status_to_key[status_match.group("status")]
        elif error_match and error_match.group(1).upper() == "ERROR":
            key = "general_error"
        elif error_match and "jules_bridge:" in line:
            key = "warning"
        else:
            continue

        error_counts[key] = error_counts.get(key, 0) + 1
        if key not in error_examples:
            error_examples[key] = []
        if len(error_examples[key]) < 3:
            error_examples[key].append(line.strip()[:120])

    patterns = []
    for key, count in error_counts.items():
        if count >= 2:  # Only patterns that repeat
            patterns.append(LogPattern(
                pattern_type="repeated_error",
                description=f"Error type '{key}' appeared {count} times",
                count=count,
                examples=error_examples.get(key, []),
            ))

    return patterns


def _detect_slow_routes(log_lines: List[str]) -> List[LogPattern]:
    """Detect routes that consistently take a long time (>5000ms)."""
    slow_routes: Dict[str, List[int]] = {}

    for line in log_lines:
        ms_match = _SLOW_ROUTE_RE.search(line)
        route_match = _ROUTE_RE.search(line)
        if ms_match and route_match:
            ms = int(float(ms_match.group("ms")))
            if ms > 5000:
                route = f"{route_match.group('method').upper()} {route_match.group('path')}"
                slow_routes.setdefault(route, []).append(ms)

    patterns = []
    for route, times in slow_routes.items():
        if len(times) >= 2:
            avg_ms = sum(times) // len(times)
            patterns.append(LogPattern(
                pattern_type="slow_route",
                description=f"Route '{route}' averaged {avg_ms}ms over {len(times)} calls (threshold: 5000ms)",
                count=len(times),
                examples=[f"{t}ms" for t in times[:5]],
            ))

    return patterns


def _detect_route_frequency(log_lines: List[str]) -> List[LogPattern]:
    """Detect high-frequency status polling that can hide stale-state loops."""
    route_counts: Dict[str, int] = {}
    route_examples: Dict[str, List[str]] = {}

    for line in log_lines:
        route_match = _ROUTE_RE.search(line)
        if not route_match:
            continue

        route = f"{route_match.group('method').upper()} {route_match.group('path')}"
        route_counts[route] = route_counts.get(route, 0) + 1
        route_examples.setdefault(route, [])
        if len(route_examples[route]) < 3:
            route_examples[route].append(line.strip()[:120])

    patterns: List[LogPattern] = []
    for route, count in route_counts.items():
        if route == "GET /oracle/status" and count >= 5:
            patterns.append(LogPattern(
                pattern_type="route_frequency",
                description=f"Route '{route}' called {count} times in one log",
                count=count,
                examples=route_examples.get(route, []),
            ))

    return patterns


def _detect_host_operations(log_lines: List[str]) -> List[LogPattern]:
    """Detect shell commands that mutate the host Oracle/Quantower runtime."""
    command_examples: List[str] = []

    for line in log_lines:
        command_match = _JULES_SHELL_RE.search(line)
        if not command_match:
            continue

        command = command_match.group("command").strip()
        lower = command.lower()
        if any(term in lower for term in (
            "quantower",
            "oracle",
            "run_starter",
            "starter",
            "build-deploy",
            "deploy-oracle",
        )):
            if len(command_examples) < 5:
                command_examples.append(command[:160])

    if not command_examples:
        return []

    return [LogPattern(
        pattern_type="host_operation",
        description=(
            "Oracle/Quantower host shell operations detected "
            f"({len(command_examples)} examples captured)"
        ),
        count=len(command_examples),
        examples=command_examples,
    )]


# ---------------------------------------------------------------------------
# Learning extraction
# ---------------------------------------------------------------------------

def _extract_learnings(
    patterns: List[LogPattern],
    doom_loops: List[DoomLoop],
) -> List[str]:
    """Convert detected patterns into actionable harness learnings.

    Nick: "Every failure becomes data for the next run."
    """
    learnings: List[str] = []

    for loop in doom_loops:
        learnings.append(
            f"DOOM LOOP: {loop.tool_name} called {loop.call_count}x consecutively. "
            f"{loop.recommendation}"
        )

    for pattern in patterns:
        if pattern.pattern_type == "repeated_error" and "500" in pattern.description:
            learnings.append(
                f"HARNESS BUG: Internal server errors ({pattern.count}x). "
                "Check module exception handling — add defensive try/except."
            )
        elif pattern.pattern_type == "repeated_error" and "504" in pattern.description:
            learnings.append(
                f"TIMEOUT: Subprocess/PowerShell calls timing out ({pattern.count}x). "
                "Increase timeout or add async handling."
            )
        elif pattern.pattern_type == "slow_route":
            learnings.append(
                f"PERFORMANCE: {pattern.description}. "
                "Consider caching or reducing subprocess overhead."
            )
        elif pattern.pattern_type == "route_frequency":
            learnings.append(
                f"STATUS POLLING: {pattern.description}. "
                "High-frequency status polling should be paired with changed-state checks and fresh evidence."
            )
        elif pattern.pattern_type == "host_operation":
            learnings.append(
                f"ORACLE/QUANTOWER AUTOMATION: {pattern.description}. "
                "Treat shell restarts/build/deploy commands as host mutations and pair them with /oracle/status plus screenshot or verify evidence."
            )

    if patterns:
        learnings.append(
            f"RETROSPECTIVE BASELINE: analyze_session found {len(patterns)} log patterns. "
            "Use the domain memories before the next bridge/runtime work."
        )

    if not learnings:
        learnings.append("No significant harness issues detected in this session.")

    return learnings


# ---------------------------------------------------------------------------
# Memory management
# ---------------------------------------------------------------------------

MEMORY_DOMAINS = ["general", "oracle", "quantower", "trading", "reasoning"]


def _load_existing_memory(memory_path: str, domain: str) -> str:
    """Load existing memory file for a domain."""
    path = os.path.join(memory_path, f"{domain}.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, FileNotFoundError):
        return ""


def _write_memory(memory_path: str, domain: str, content: str) -> None:
    """Write updated memory to a domain file."""
    os.makedirs(memory_path, exist_ok=True)
    path = os.path.join(memory_path, f"{domain}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _update_memory_with_learnings(
    memory_path: str,
    learnings: List[str],
    session_id: str,
) -> Dict[str, str]:
    """Write learnings to the general memory file.

    Nick's Case: per-project memory files as markdown.
    """
    updated = {}
    if not learnings:
        return updated

    # Classify learnings into domains
    domain_learnings: Dict[str, List[str]] = {"general": []}
    for learning in learnings:
        lower = learning.lower()
        if "oracle" in lower or "dll" in lower or "build" in lower:
            domain_learnings.setdefault("oracle", []).append(learning)
        elif "quantower" in lower or "starter" in lower or "telemetry" in lower:
            domain_learnings.setdefault("quantower", []).append(learning)
        elif "reasoning" in lower or "halt" in lower or "plan" in lower:
            domain_learnings.setdefault("reasoning", []).append(learning)
        else:
            domain_learnings["general"].append(learning)

    now = datetime.now(timezone.utc).isoformat()

    for domain, domain_specific_learnings in domain_learnings.items():
        if not domain_specific_learnings:
            continue

        existing = _load_existing_memory(memory_path, domain)
        new_section = f"\n## Session {session_id} — {now}\n\n"
        for learning in domain_specific_learnings:
            new_section += f"- {learning}\n"

        updated_content = existing.rstrip() + "\n" + new_section
        _write_memory(memory_path, domain, updated_content)
        updated[domain] = new_section

    return updated


# ---------------------------------------------------------------------------
# Test evidence (Nick's SHA-256 approach)
# ---------------------------------------------------------------------------

def record_test_evidence(test_output: str, evidence_path: str) -> TestEvidence:
    """Record cryptographic proof that tests were actually run.

    Nick: "I took the test output and SHA-256'd that and saved that into
    the tested file, then verify cryptographically that you actually ran the tests."

    Args:
        test_output: Full stdout of the test run (e.g. pytest output)
        evidence_path: Directory to store test_evidence.json

    Returns:
        TestEvidence with hash, pass status, and test count
    """
    output_hash = hashlib.sha256(test_output.encode("utf-8")).hexdigest()
    parse_output = _normalize_test_output_for_parse(test_output)
    passed = False
    test_count = 0

    # Parse pytest output for test count
    count_match = re.search(r"(\d+) passed", parse_output)
    if count_match:
        test_count = int(count_match.group(1))
        passed = True
    fail_match = re.search(r"(\d+) failed", parse_output)
    if fail_match:
        passed = False
    error_match = re.search(r"(\d+) errors?", parse_output)
    if error_match:
        passed = False

    lines = parse_output.strip().splitlines()
    raw_tail = "\n".join(lines[-5:]) if len(lines) >= 5 else parse_output

    evidence = TestEvidence(
        output_hash=output_hash,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        passed=passed,
        test_count=test_count,
        raw_output_tail=raw_tail,
    )

    # Persist to disk
    os.makedirs(evidence_path, exist_ok=True)
    evidence_file = os.path.join(evidence_path, "test_evidence.json")
    try:
        with open(evidence_file, "r", encoding="utf-8-sig") as f:
            history = json.load(f)
    except (OSError, json.JSONDecodeError):
        history = []

    history.append({
        "output_hash": evidence.output_hash,
        "timestamp_utc": evidence.timestamp_utc,
        "passed": evidence.passed,
        "test_count": evidence.test_count,
        "raw_output_tail": evidence.raw_output_tail,
    })

    # Keep last 50 evidence records
    history = history[-50:]
    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return evidence


def _normalize_test_output_for_parse(test_output: str) -> str:
    """Normalize captured test output before regex parsing.

    PowerShell 5.1 `Tee-Object` can create UTF-16-like text that reaches Python
    as interleaved NUL characters when read as UTF-8. The hash still covers the
    original bytes-as-read string; this cleaned copy is only for status parsing
    and human-readable tails.
    """
    return (test_output or "").replace("\x00", "")


def load_test_evidence(evidence_path: str) -> Optional[TestEvidence]:
    """Load the most recent test evidence record."""
    evidence_file = os.path.join(evidence_path, "test_evidence.json")
    try:
        with open(evidence_file, "r", encoding="utf-8-sig") as f:
            history = json.load(f)
        if not history:
            return None
        latest = history[-1]
        return TestEvidence(
            output_hash=latest["output_hash"],
            timestamp_utc=latest["timestamp_utc"],
            passed=latest["passed"],
            test_count=latest["test_count"],
            raw_output_tail=latest["raw_output_tail"],
        )
    except (OSError, json.JSONDecodeError, KeyError):
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def analyze_session(
    log_path: Optional[str] = None,
    memory_path: Optional[str] = None,
    session_id: Optional[str] = None,
    auto_prune: bool = False,
) -> RetrospectiveReport:
    """Analyze a Jules Bridge session and write learnings to memory.

    Reads bridge.log, detects doom loops and error patterns, extracts
    actionable learnings, and writes them to per-domain memory markdown files.

    Nick's principle: "Every failure becomes data for the next run."

    Args:
        log_path: Path to bridge.log (defaults to bridge.log in cwd)
        memory_path: Path to memory/ directory (defaults to memory/ in cwd)
        session_id: Identifier for this session (defaults to timestamp)
        auto_prune: If True, run prune_memory() after writing this session

    Returns:
        RetrospectiveReport with all findings

    Never raises — all sub-operations are defensive.
    """
    if log_path is None:
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bridge.log")
    if memory_path is None:
        memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")
    if session_id is None:
        session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    # Parse log
    log_lines = _parse_log_lines(log_path)

    # Detect patterns
    doom_loops = _detect_doom_loops(log_lines)
    error_patterns = _detect_error_patterns(log_lines)
    slow_patterns = _detect_slow_routes(log_lines)
    route_frequency_patterns = _detect_route_frequency(log_lines)
    host_operation_patterns = _detect_host_operations(log_lines)
    all_patterns = (
        error_patterns
        + slow_patterns
        + route_frequency_patterns
        + host_operation_patterns
    )

    # Extract learnings
    learnings = _extract_learnings(all_patterns, doom_loops)

    # Write to memory
    memory_updates = _update_memory_with_learnings(memory_path, learnings, session_id)

    if auto_prune:
        prune_result = prune_memory(memory_path=memory_path)
        LOGGER.info("auto_prune removed %s sections", prune_result["pruned_count"])

    # Load any existing test evidence
    evidence = load_test_evidence(memory_path)

    return RetrospectiveReport(
        session_id=session_id,
        analyzed_at_utc=datetime.now(timezone.utc).isoformat(),
        log_lines_analyzed=len(log_lines),
        patterns=all_patterns,
        doom_loops=doom_loops,
        learnings=learnings,
        memory_updates=memory_updates,
        evidence=evidence,
    )


def load_memory(memory_path: Optional[str] = None, domain: str = "general") -> str:
    """Load memory for a specific domain.

    Call this at the start of a session to load accumulated learnings.

    Args:
        memory_path: Path to memory/ directory
        domain: One of: general, oracle, quantower, trading, reasoning

    Returns:
        Markdown string of accumulated learnings for that domain,
        or empty string if no memory exists yet.
    """
    if memory_path is None:
        memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")
    return _load_existing_memory(memory_path, domain)


def prune_memory(
    memory_path: Optional[str] = None,
    max_age_days: int = 30,
) -> Dict[str, Any]:
    """Remove learnings older than max_age_days from all memory files.

    Claude's autodream idea: auto-prune old/redundant learnings so memory
    stays focused and doesn't grow without bound.

    Strategy: age-based pruning. Each learning section is headed by a
    session datestamp (e.g. ## Session 20250601T...). Sections whose
    datestamp is older than max_age_days are removed. Sections with no
    parseable datestamp are kept (conservative default).

    Header sections ('## How to use', '## Initial Notes') are always preserved.

    Args:
        memory_path: Path to memory/ directory. Defaults to {root}/memory/.
        max_age_days: Drop sections whose datestamp is older than this. Default 30.

    Returns:
        Dict with keys: pruned_count (int), domains_affected (list[str])
    """
    if memory_path is None:
        memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")

    # ISO 8601 compact timestamp pattern embedded in session headers
    # e.g. "## Session 20250601T143022" or "## Analysis 20260101T000000"
    _TS_RE = re.compile(r"(\d{8}T\d{6})")
    _PRESERVE_PREFIXES = ("## How to use", "## Initial Notes")

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    from datetime import timedelta
    cutoff -= timedelta(days=max_age_days)

    total_pruned = 0
    domains_affected: List[str] = []

    memory_dir = Path(memory_path)
    if not memory_dir.is_dir():
        return {"pruned_count": 0, "domains_affected": []}

    for md_file in sorted(memory_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)

        # Split into sections at "## " boundaries
        sections: List[List[str]] = []
        current: List[str] = []
        for line in lines:
            if line.startswith("## ") and current:
                sections.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append(current)

        kept: List[List[str]] = []
        pruned_in_file = 0

        for section in sections:
            heading = section[0].rstrip() if section else ""

            # Always preserve non-session headers
            if any(heading.startswith(p) for p in _PRESERVE_PREFIXES):
                kept.append(section)
                continue

            # Try to parse a timestamp from the heading
            m = _TS_RE.search(heading)
            if not m:
                # No timestamp found — keep conservatively
                kept.append(section)
                continue

            try:
                ts = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")
                if ts < cutoff:
                    pruned_in_file += 1
                else:
                    kept.append(section)
            except ValueError:
                kept.append(section)  # unparseable timestamp — keep

        if pruned_in_file > 0:
            new_text = "".join("".join(s) for s in kept)
            md_file.write_text(new_text, encoding="utf-8")
            total_pruned += pruned_in_file
            domains_affected.append(md_file.stem)

    return {
        "pruned_count": total_pruned,
        "domains_affected": domains_affected,
    }


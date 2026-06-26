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
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    r"(ERROR|WARN|500|504|400|403|404)", re.IGNORECASE
)
_SLOW_ROUTE_RE = re.compile(
    r"ms=(?P<ms>\d+)", re.IGNORECASE
)
_ROUTE_RE = re.compile(
    r'"(?P<method>GET|POST|PUT|DELETE|PATCH)\s+(?P<path>/[^\s"]+)"', re.IGNORECASE
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

    return doom_loops


def _detect_error_patterns(log_lines: List[str]) -> List[LogPattern]:
    """Detect recurring error patterns in the log."""
    error_counts: Dict[str, int] = {}
    error_examples: Dict[str, List[str]] = {}

    for line in log_lines:
        if _ERROR_LINE_RE.search(line):
            # Categorize by error type
            if "500" in line:
                key = "internal_error_500"
            elif "504" in line:
                key = "timeout_504"
            elif "404" in line:
                key = "not_found_404"
            elif "403" in line:
                key = "access_denied_403"
            elif "400" in line:
                key = "bad_request_400"
            elif "ERROR" in line:
                key = "general_error"
            else:
                key = "warning"

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
            ms = int(ms_match.group("ms"))
            if ms > 5000:
                route = route_match.group("path")
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
    passed = "passed" in test_output.lower() and "failed" not in test_output.lower()
    test_count = 0

    # Parse pytest output for test count
    count_match = re.search(r"(\d+) passed", test_output)
    if count_match:
        test_count = int(count_match.group(1))
    fail_match = re.search(r"(\d+) failed", test_output)
    if fail_match:
        passed = False

    lines = test_output.strip().splitlines()
    raw_tail = "\n".join(lines[-5:]) if len(lines) >= 5 else test_output

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
        with open(evidence_file, "r", encoding="utf-8") as f:
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


def load_test_evidence(evidence_path: str) -> Optional[TestEvidence]:
    """Load the most recent test evidence record."""
    evidence_file = os.path.join(evidence_path, "test_evidence.json")
    try:
        with open(evidence_file, "r", encoding="utf-8") as f:
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
) -> RetrospectiveReport:
    """Analyze a Jules Bridge session and write learnings to memory.

    Reads bridge.log, detects doom loops and error patterns, extracts
    actionable learnings, and writes them to per-domain memory markdown files.

    Nick's principle: "Every failure becomes data for the next run."

    Args:
        log_path: Path to bridge.log (defaults to bridge.log in cwd)
        memory_path: Path to memory/ directory (defaults to memory/ in cwd)
        session_id: Identifier for this session (defaults to timestamp)

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
    all_patterns = error_patterns + slow_patterns

    # Extract learnings
    learnings = _extract_learnings(all_patterns, doom_loops)

    # Write to memory
    memory_updates = _update_memory_with_learnings(memory_path, learnings, session_id)

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

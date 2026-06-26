"""Tests for retrospective_module.py

Tests the module boundary contract — all tests call only the public interface.
Nick Ni: "Every failure is a harness bug."
"""
import hashlib
import json
import os
import tempfile
import textwrap

import pytest

from modules.retrospective_module import (
    DoomLoop,
    LogPattern,
    RetrospectiveReport,
    TestEvidence,
    analyze_session,
    load_memory,
    load_test_evidence,
    record_test_evidence,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_dirs():
    """Provide temporary directories for log, memory, and evidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "bridge.log")
        memory_path = os.path.join(tmpdir, "memory")
        os.makedirs(memory_path, exist_ok=True)
        yield {"log": log_path, "memory": memory_path, "root": tmpdir}


def _write_log(log_path: str, lines: list[str]) -> None:
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


SAMPLE_PYTEST_OUTPUT = textwrap.dedent("""\
    ============================= test session starts ==============================
    platform win32 -- Python 3.12.10
    collected 34 items

    tests/test_reasoning_module.py::TestReason::test_returns_reasoning_trace PASSED
    tests/test_reasoning_module.py::TestReason::test_trace_has_plan PASSED

    ============================== 2 passed in 0.13s ==============================
""")

SAMPLE_PYTEST_FAIL = textwrap.dedent("""\
    ============================= test session starts ==============================
    collected 2 items

    tests/test_foo.py::test_bar FAILED

    ============================== 1 failed in 0.05s ==============================
""")


# ---------------------------------------------------------------------------
# TestLogPattern
# ---------------------------------------------------------------------------

class TestLogPattern:
    def test_dataclass_fields(self):
        p = LogPattern(
            pattern_type="doom_loop",
            description="Same route called 5 times",
            count=5,
            examples=["GET /oracle/status", "GET /oracle/status"],
        )
        assert p.pattern_type == "doom_loop"
        assert p.count == 5
        assert len(p.examples) == 2


# ---------------------------------------------------------------------------
# TestDoomLoop
# ---------------------------------------------------------------------------

class TestDoomLoop:
    def test_dataclass_fields(self):
        d = DoomLoop(
            tool_name="GET /oracle/status",
            call_count=4,
            consecutive=True,
            recommendation="Add circuit breaker.",
        )
        assert d.tool_name == "GET /oracle/status"
        assert d.call_count == 4
        assert d.consecutive is True
        assert "circuit" in d.recommendation.lower()


# ---------------------------------------------------------------------------
# TestTestEvidence
# ---------------------------------------------------------------------------

class TestTestEvidence:
    def test_passed_evidence(self):
        evidence = record_test_evidence(SAMPLE_PYTEST_OUTPUT, tempfile.mkdtemp())
        assert evidence.passed is True
        assert evidence.test_count == 2
        assert len(evidence.output_hash) == 64  # SHA-256 is 64 hex chars

    def test_failed_evidence(self):
        evidence = record_test_evidence(SAMPLE_PYTEST_FAIL, tempfile.mkdtemp())
        assert evidence.passed is False

    def test_hash_is_deterministic(self):
        tmp = tempfile.mkdtemp()
        e1 = record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        e2 = record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        assert e1.output_hash == e2.output_hash

    def test_hash_changes_with_output(self):
        tmp = tempfile.mkdtemp()
        e1 = record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        e2 = record_test_evidence(SAMPLE_PYTEST_OUTPUT + " extra", tmp)
        assert e1.output_hash != e2.output_hash

    def test_evidence_persisted_to_disk(self):
        tmp = tempfile.mkdtemp()
        record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        evidence_file = os.path.join(tmp, "test_evidence.json")
        assert os.path.exists(evidence_file)
        with open(evidence_file) as f:
            records = json.load(f)
        assert len(records) >= 1
        assert records[-1]["passed"] is True

    def test_evidence_accumulates(self):
        tmp = tempfile.mkdtemp()
        for _ in range(3):
            record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        evidence_file = os.path.join(tmp, "test_evidence.json")
        with open(evidence_file) as f:
            records = json.load(f)
        assert len(records) == 3

    def test_evidence_capped_at_50(self):
        tmp = tempfile.mkdtemp()
        for i in range(55):
            record_test_evidence(f"output {i}", tmp)
        evidence_file = os.path.join(tmp, "test_evidence.json")
        with open(evidence_file) as f:
            records = json.load(f)
        assert len(records) == 50

    def test_evidence_line_format(self):
        tmp = tempfile.mkdtemp()
        evidence = record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        line = evidence.evidence_line
        assert "PASSED" in line
        assert "sha256:" in line
        assert "2 tests" in line

    def test_load_test_evidence_returns_latest(self):
        tmp = tempfile.mkdtemp()
        record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        record_test_evidence(SAMPLE_PYTEST_FAIL, tmp)
        loaded = load_test_evidence(tmp)
        assert loaded is not None
        assert loaded.passed is False  # most recent was fail

    def test_load_test_evidence_empty_dir(self):
        tmp = tempfile.mkdtemp()
        result = load_test_evidence(tmp)
        assert result is None


# ---------------------------------------------------------------------------
# TestAnalyzeSession
# ---------------------------------------------------------------------------

class TestAnalyzeSession:
    def test_returns_report(self, tmp_dirs):
        report = analyze_session(
            log_path=tmp_dirs["log"],
            memory_path=tmp_dirs["memory"],
            session_id="test001",
        )
        assert isinstance(report, RetrospectiveReport)

    def test_empty_log_produces_no_patterns(self, tmp_dirs):
        _write_log(tmp_dirs["log"], [])
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert report.patterns == []
        assert report.doom_loops == []

    def test_missing_log_does_not_raise(self, tmp_dirs):
        # log_path doesn't exist — should return empty report, not crash
        report = analyze_session(
            log_path=os.path.join(tmp_dirs["root"], "nonexistent.log"),
            memory_path=tmp_dirs["memory"],
        )
        assert report.log_lines_analyzed == 0
        assert isinstance(report.learnings, list)

    def test_doom_loop_detected(self, tmp_dirs):
        # Same route called 4x consecutively
        lines = [
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
        ]
        _write_log(tmp_dirs["log"], lines)
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert report.has_doom_loops
        assert len(report.doom_loops) >= 1
        loop = report.doom_loops[0]
        assert loop.call_count >= 4
        assert loop.consecutive is True

    def test_no_doom_loop_for_alternating_routes(self, tmp_dirs):
        lines = [
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200',
            '127.0.0.1 "GET /fs/read HTTP/1.1" 200',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200',
            '127.0.0.1 "GET /fs/read HTTP/1.1" 200',
        ]
        _write_log(tmp_dirs["log"], lines)
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert not report.has_doom_loops

    def test_error_pattern_detected(self, tmp_dirs):
        lines = [
            '127.0.0.1 "POST /oracle/build HTTP/1.1" 500',
            '127.0.0.1 "POST /oracle/build HTTP/1.1" 500',
            '127.0.0.1 "POST /oracle/build HTTP/1.1" 500',
        ]
        _write_log(tmp_dirs["log"], lines)
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert len(report.patterns) >= 1
        pattern_types = [p.pattern_type for p in report.patterns]
        assert "repeated_error" in pattern_types

    def test_session_id_is_set(self, tmp_dirs):
        report = analyze_session(
            log_path=tmp_dirs["log"],
            memory_path=tmp_dirs["memory"],
            session_id="my-session-42",
        )
        assert report.session_id == "my-session-42"

    def test_auto_session_id_when_none(self, tmp_dirs):
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert len(report.session_id) > 0  # auto-generated timestamp

    def test_learnings_list_is_non_empty(self, tmp_dirs):
        """Even with no patterns, learnings should contain at least one entry."""
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert len(report.learnings) >= 1

    def test_learnings_written_to_memory(self, tmp_dirs):
        lines = [
            '127.0.0.1 "POST /shell/exec HTTP/1.1" 500',
            '127.0.0.1 "POST /shell/exec HTTP/1.1" 500',
        ]
        _write_log(tmp_dirs["log"], lines)
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        # Check that at least one domain got a memory update
        general_path = os.path.join(tmp_dirs["memory"], "general.md")
        if report.memory_updates:
            assert os.path.exists(general_path) or any(
                os.path.exists(os.path.join(tmp_dirs["memory"], f"{d}.md"))
                for d in report.memory_updates
            )

    def test_to_summary_is_string(self, tmp_dirs):
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        summary = report.to_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Retrospective" in summary

    def test_has_learnings_property(self, tmp_dirs):
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert isinstance(report.has_learnings, bool)

    def test_log_lines_analyzed_count(self, tmp_dirs):
        lines = ["line one", "line two", "line three"]
        _write_log(tmp_dirs["log"], lines)
        report = analyze_session(log_path=tmp_dirs["log"], memory_path=tmp_dirs["memory"])
        assert report.log_lines_analyzed == len(lines)


# ---------------------------------------------------------------------------
# TestLoadMemory
# ---------------------------------------------------------------------------

class TestLoadMemory:
    def test_returns_empty_when_no_memory(self, tmp_dirs):
        content = load_memory(memory_path=tmp_dirs["memory"], domain="general")
        assert content == ""

    def test_returns_written_content(self, tmp_dirs):
        general_path = os.path.join(tmp_dirs["memory"], "general.md")
        with open(general_path, "w") as f:
            f.write("# Memory\n\n- Learning A\n")
        content = load_memory(memory_path=tmp_dirs["memory"], domain="general")
        assert "Learning A" in content

    def test_oracle_domain_separate_from_general(self, tmp_dirs):
        oracle_path = os.path.join(tmp_dirs["memory"], "oracle.md")
        with open(oracle_path, "w") as f:
            f.write("# Oracle\n\n- Oracle gotcha\n")
        general = load_memory(memory_path=tmp_dirs["memory"], domain="general")
        oracle = load_memory(memory_path=tmp_dirs["memory"], domain="oracle")
        assert "Oracle gotcha" not in general
        assert "Oracle gotcha" in oracle

    def test_all_domains_loadable(self, tmp_dirs):
        for domain in ("general", "oracle", "quantower", "trading", "reasoning"):
            content = load_memory(memory_path=tmp_dirs["memory"], domain=domain)
            assert isinstance(content, str)  # never raises

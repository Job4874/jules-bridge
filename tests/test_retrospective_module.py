"""Tests for retrospective_module.py

Tests the module boundary contract — all tests call only the public interface.
Nick Ni: "Every failure is a harness bug."
"""
# pylint: disable=redefined-outer-name

import json
import logging
import os
import tempfile
import textwrap

import pytest

from datetime import datetime, timedelta, timezone

from modules.retrospective_module import (
    MEMORY_DOMAINS,
    DoomLoop,
    EvidenceStaleness,
    LogPattern,
    RetrospectiveReport,
    analyze_session,
    check_test_evidence_staleness,
    is_evidence_hard_gate_enabled,
    load_memory,
    load_test_evidence,
    record_test_evidence,
    validate_memory_domain,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def setup_dirs():
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

    def test_passed_evidence_ignores_failed_word_in_test_name(self):
        output = textwrap.dedent("""\
            tests/test_retrospective_module.py::TestTestEvidence::test_failed_evidence PASSED
            tests/test_akc_module.py::TestBuildAKCContext::test_missing_sources_are_reported_not_raised PASSED
            ======================= 141 passed, 1 warning in 2.08s ========================
        """)

        evidence = record_test_evidence(output, tempfile.mkdtemp())

        assert evidence.passed is True
        assert evidence.test_count == 141

    def test_passed_evidence_handles_nul_padded_powershell_capture(self):
        output = "======================= 181 passed, 1 warning in 2.58s ========================"
        nul_padded = "\x00".join(output) + "\x00"

        evidence = record_test_evidence(nul_padded, tempfile.mkdtemp())

        assert evidence.passed is True
        assert evidence.test_count == 181
        assert "\x00" not in evidence.raw_output_tail

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
        with open(evidence_file, encoding="utf-8") as f:
            records = json.load(f)
        assert len(records) >= 1
        assert records[-1]["passed"] is True

    def test_evidence_accumulates(self):
        tmp = tempfile.mkdtemp()
        for _ in range(3):
            record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)
        evidence_file = os.path.join(tmp, "test_evidence.json")
        with open(evidence_file, encoding="utf-8") as f:
            records = json.load(f)
        assert len(records) == 3

    def test_evidence_accumulates_when_existing_file_has_bom(self):
        tmp = tempfile.mkdtemp()
        evidence_file = os.path.join(tmp, "test_evidence.json")
        existing = [{
            "output_hash": "abc123",
            "timestamp_utc": "2026-06-26T00:00:00+00:00",
            "passed": True,
            "test_count": 1,
            "raw_output_tail": "======================= 1 passed in 0.01s ========================",
        }]
        with open(evidence_file, "w", encoding="utf-8-sig") as f:
            json.dump(existing, f)

        record_test_evidence(SAMPLE_PYTEST_OUTPUT, tmp)

        with open(evidence_file, encoding="utf-8") as f:
            records = json.load(f)
        assert len(records) == 2
        assert records[0]["output_hash"] == "abc123"
        assert records[-1]["test_count"] == 2

    def test_evidence_capped_at_50(self):
        tmp = tempfile.mkdtemp()
        for i in range(55):
            record_test_evidence(f"output {i}", tmp)
        evidence_file = os.path.join(tmp, "test_evidence.json")
        with open(evidence_file, encoding="utf-8") as f:
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
    def test_returns_report(self, setup_dirs):
        report = analyze_session(
            log_path=setup_dirs["log"],
            memory_path=setup_dirs["memory"],
            session_id="test001",
        )
        assert isinstance(report, RetrospectiveReport)

    def test_empty_log_produces_no_patterns(self, setup_dirs):
        _write_log(setup_dirs["log"], [])
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert not report.patterns
        assert not report.doom_loops

    def test_missing_log_does_not_raise(self, setup_dirs):
        # log_path doesn't exist — should return empty report, not crash
        report = analyze_session(
            log_path=os.path.join(setup_dirs["root"], "nonexistent.log"),
            memory_path=setup_dirs["memory"],
        )
        assert report.log_lines_analyzed == 0
        assert isinstance(report.learnings, list)

    def test_doom_loop_detected(self, setup_dirs):
        # Same route called 4x consecutively
        lines = [
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200 ms=100',
        ]
        _write_log(setup_dirs["log"], lines)
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert report.has_doom_loops
        assert len(report.doom_loops) >= 1
        loop = report.doom_loops[0]
        assert loop.call_count >= 4
        assert loop.consecutive is True

    def test_no_doom_loop_for_alternating_routes(self, setup_dirs):
        lines = [
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200',
            '127.0.0.1 "GET /fs/read HTTP/1.1" 200',
            '127.0.0.1 "POST /oracle/status HTTP/1.1" 200',
            '127.0.0.1 "GET /fs/read HTTP/1.1" 200',
        ]
        _write_log(setup_dirs["log"], lines)
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert not report.has_doom_loops

    def test_repeated_doom_loops_are_deduped_by_route(self, setup_dirs):
        lines = [
            '127.0.0.1 "POST /shell HTTP/1.1" 200',
            '127.0.0.1 "POST /shell HTTP/1.1" 200',
            '127.0.0.1 "POST /shell HTTP/1.1" 200',
            '127.0.0.1 "GET /ping HTTP/1.1" 200',
            '127.0.0.1 "POST /shell HTTP/1.1" 200',
            '127.0.0.1 "POST /shell HTTP/1.1" 200',
            '127.0.0.1 "POST /shell HTTP/1.1" 200',
            '127.0.0.1 "POST /shell HTTP/1.1" 200',
        ]
        _write_log(setup_dirs["log"], lines)

        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])

        shell_loops = [loop for loop in report.doom_loops if loop.tool_name == "POST /shell"]
        assert len(shell_loops) == 1
        assert shell_loops[0].call_count == 4

    def test_error_pattern_detected(self, setup_dirs):
        lines = [
            '127.0.0.1 "POST /oracle/build HTTP/1.1" 500',
            '127.0.0.1 "POST /oracle/build HTTP/1.1" 500',
            '127.0.0.1 "POST /oracle/build HTTP/1.1" 500',
        ]
        _write_log(setup_dirs["log"], lines)
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert len(report.patterns) >= 1
        pattern_types = [p.pattern_type for p in report.patterns]
        assert "repeated_error" in pattern_types

    def test_port_5000_and_threshold_5000ms_are_not_500_errors(self, setup_dirs):
        lines = [
            "2026-06-25T15:56:46.925817+00:00 Flask bridge online at http://127.0.0.1:5000",
            "2026-06-25T10:41:10-0600 INFO jules_bridge: Listening on 0.0.0.0:5000",
            "2026-06-25T10:41:10-0600 INFO jules_bridge: POST /shell -> 200 5000.00ms remote=127.0.0.1",
        ]
        _write_log(setup_dirs["log"], lines)

        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])

        assert not any("internal_error_500" in pattern.description for pattern in report.patterns)

    def test_dev_server_warning_is_not_a_harness_warning(self, setup_dirs):
        lines = [
            "2026-06-25T10:41:10-0600 INFO werkzeug: WARNING: This is a development server.",
            "2026-06-25T10:50:45-0600 INFO werkzeug: WARNING: This is a development server.",
            "2026-06-25T19:35:43-0600 INFO werkzeug: WARNING: This is a development server.",
        ]
        _write_log(setup_dirs["log"], lines)

        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])

        assert not any("warning" in pattern.description for pattern in report.patterns)

    def test_arrow_style_slow_route_detected(self, setup_dirs):
        lines = [
            "2026-06-25 INFO jules_bridge: GET /oracle/status -> 200 11874.35ms remote=127.0.0.1",
            "2026-06-25 INFO jules_bridge: GET /oracle/status -> 200 9844.00ms remote=127.0.0.1",
        ]
        _write_log(setup_dirs["log"], lines)

        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])

        assert any(pattern.pattern_type == "slow_route" for pattern in report.patterns)
        assert any("GET /oracle/status" in learning for learning in report.learnings)

    def test_repeated_oracle_status_polling_extracts_learning(self, setup_dirs):
        lines = [
            f"2026-06-25 INFO jules_bridge: GET /oracle/status -> 200 {1000 + i}.00ms remote=127.0.0.1"
            for i in range(6)
        ]
        _write_log(setup_dirs["log"], lines)

        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])

        assert any(pattern.pattern_type == "route_frequency" for pattern in report.patterns)
        assert any("GET /oracle/status" in learning for learning in report.learnings)

    def test_quantower_shell_operations_extract_learning(self, setup_dirs):
        lines = [
            (
                "2026-06-25 INFO jules_bridge: [JULES SHELL] shell=powershell "
                "cwd=C:\\aotp\\projects\\OracleV5 command=.\\Tools\\Restart-QuantowerLoadOracle.ps1 -ForceClose"
            ),
            (
                "2026-06-25 INFO jules_bridge: [JULES SHELL] shell=powershell "
                "cwd=C:\\Users\\abdul\\.jules command=powershell.exe -ExecutionPolicy Bypass -File scratch\\run_starter.ps1"
            ),
        ]
        _write_log(setup_dirs["log"], lines)

        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])

        assert any(pattern.pattern_type == "host_operation" for pattern in report.patterns)
        assert any("Quantower" in learning or "Oracle" in learning for learning in report.learnings)

    def test_session_id_is_set(self, setup_dirs):
        report = analyze_session(
            log_path=setup_dirs["log"],
            memory_path=setup_dirs["memory"],
            session_id="my-session-42",
        )
        assert report.session_id == "my-session-42"

    def test_auto_session_id_when_none(self, setup_dirs):
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert len(report.session_id) > 0  # auto-generated timestamp

    def test_learnings_list_is_non_empty(self, setup_dirs):
        """Even with no patterns, learnings should contain at least one entry."""
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert len(report.learnings) >= 1

    def test_learnings_written_to_memory(self, setup_dirs):
        lines = [
            '127.0.0.1 "POST /shell/exec HTTP/1.1" 500',
            '127.0.0.1 "POST /shell/exec HTTP/1.1" 500',
        ]
        _write_log(setup_dirs["log"], lines)
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        # Check that at least one domain got a memory update
        general_path = os.path.join(setup_dirs["memory"], "general.md")
        if report.memory_updates:
            assert os.path.exists(general_path) or any(
                os.path.exists(os.path.join(setup_dirs["memory"], f"{d}.md"))
                for d in report.memory_updates
            )

    def test_to_summary_is_string(self, setup_dirs):
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        summary = report.to_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Retrospective" in summary

    def test_has_learnings_property(self, setup_dirs):
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert isinstance(report.has_learnings, bool)

    def test_log_lines_analyzed_count(self, setup_dirs):
        lines = ["line one", "line two", "line three"]
        _write_log(setup_dirs["log"], lines)
        report = analyze_session(log_path=setup_dirs["log"], memory_path=setup_dirs["memory"])
        assert report.log_lines_analyzed == len(lines)

    def test_analyze_session_does_not_prune_by_default(self, setup_dirs):
        general_path = os.path.join(setup_dirs["memory"], "general.md")
        with open(general_path, "w", encoding="utf-8") as handle:
            handle.write("## Session 20000101T000000\n\n- stale learning\n")
        _write_log(setup_dirs["log"], ['127.0.0.1 "POST /shell/exec HTTP/1.1" 500'] * 2)

        analyze_session(
            log_path=setup_dirs["log"],
            memory_path=setup_dirs["memory"],
            session_id="20990101T000000",
        )

        with open(general_path, encoding="utf-8") as handle:
            text = handle.read()
        assert "stale learning" in text
        assert "20990101T000000" in text

    def test_analyze_session_auto_prune_removes_stale_sections_after_write(self, setup_dirs, caplog):
        general_path = os.path.join(setup_dirs["memory"], "general.md")
        with open(general_path, "w", encoding="utf-8") as handle:
            handle.write("## Session 20000101T000000\n\n- stale learning\n")
        _write_log(setup_dirs["log"], ['127.0.0.1 "POST /shell/exec HTTP/1.1" 500'] * 2)

        with caplog.at_level(logging.INFO, logger="retrospective"):
            analyze_session(
                log_path=setup_dirs["log"],
                memory_path=setup_dirs["memory"],
                session_id="20990101T000000",
                auto_prune=True,
            )

        with open(general_path, encoding="utf-8") as handle:
            text = handle.read()
        assert "stale learning" not in text
        assert "20990101T000000" in text
        assert "auto_prune removed 1 sections" in caplog.text


# ---------------------------------------------------------------------------
# TestLoadMemory
# ---------------------------------------------------------------------------

class TestLoadMemory:
    def test_returns_empty_when_no_memory(self, setup_dirs):
        content = load_memory(memory_path=setup_dirs["memory"], domain="general")
        assert content == ""

    def test_returns_written_content(self, setup_dirs):
        general_path = os.path.join(setup_dirs["memory"], "general.md")
        with open(general_path, "w", encoding="utf-8") as f:
            f.write("# Memory\n\n- Learning A\n")
        content = load_memory(memory_path=setup_dirs["memory"], domain="general")
        assert "Learning A" in content

    def test_oracle_domain_separate_from_general(self, setup_dirs):
        oracle_path = os.path.join(setup_dirs["memory"], "oracle.md")
        with open(oracle_path, "w", encoding="utf-8") as f:
            f.write("# Oracle\n\n- Oracle gotcha\n")
        general = load_memory(memory_path=setup_dirs["memory"], domain="general")
        oracle = load_memory(memory_path=setup_dirs["memory"], domain="oracle")
        assert "Oracle gotcha" not in general
        assert "Oracle gotcha" in oracle

    def test_all_domains_loadable(self, setup_dirs):
        for domain in ("general", "oracle", "quantower", "trading", "reasoning"):
            content = load_memory(memory_path=setup_dirs["memory"], domain=domain)
            assert isinstance(content, str)  # never raises


# ---------------------------------------------------------------------------
# Evidence-gating policy (Initiative C) — extracted from bridge.py middleware.
# Option A: built on load_test_evidence; fail-CLOSED on malformed / clock-skew.
# ---------------------------------------------------------------------------

def _write_evidence_json(memory_path: str, record) -> None:
    """Write a raw test_evidence.json (record may be a dict, list, or str)."""
    os.makedirs(memory_path, exist_ok=True)
    path = os.path.join(memory_path, "test_evidence.json")
    with open(path, "w", encoding="utf-8") as handle:
        if isinstance(record, str):
            handle.write(record)
        else:
            json.dump(record, handle)


def _evidence_record(timestamp_utc: str) -> dict:
    return {
        "output_hash": "a" * 64,
        "timestamp_utc": timestamp_utc,
        "passed": True,
        "test_count": 1,
        "raw_output_tail": "1 passed",
    }


class TestCheckEvidenceStaleness:
    def test_fresh_evidence_returns_none(self, tmp_dirs):
        ts = datetime.now(timezone.utc).isoformat()
        _write_evidence_json(tmp_dirs["memory"], [_evidence_record(ts)])
        assert check_test_evidence_staleness(tmp_dirs["memory"]) is None

    def test_stale_evidence_flagged_with_reason(self, tmp_dirs):
        ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        _write_evidence_json(tmp_dirs["memory"], [_evidence_record(ts)])
        result = check_test_evidence_staleness(tmp_dirs["memory"])
        assert isinstance(result, EvidenceStaleness)
        assert result.reason == "stale"
        assert result.age_s > 3600
        assert result.threshold_s == 3600

    def test_future_timestamp_is_clock_skew_not_fresh(self, tmp_dirs):
        ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        _write_evidence_json(tmp_dirs["memory"], [_evidence_record(ts)])
        result = check_test_evidence_staleness(tmp_dirs["memory"])
        assert isinstance(result, EvidenceStaleness)
        assert result.reason == "clock_skew"
        assert result.age_s < 0

    def test_malformed_json_is_flagged_malformed(self, tmp_dirs):
        _write_evidence_json(tmp_dirs["memory"], "{not valid json")
        result = check_test_evidence_staleness(tmp_dirs["memory"])
        assert isinstance(result, EvidenceStaleness)
        assert result.reason == "malformed"

    def test_record_missing_timestamp_is_malformed(self, tmp_dirs):
        _write_evidence_json(tmp_dirs["memory"], [{"output_hash": "x", "passed": True}])
        result = check_test_evidence_staleness(tmp_dirs["memory"])
        assert isinstance(result, EvidenceStaleness)
        assert result.reason == "malformed"

    def test_missing_file_returns_none(self, tmp_dirs):
        # No test_evidence.json written at all → no evidence yet → proceed.
        assert check_test_evidence_staleness(tmp_dirs["memory"]) is None

    def test_empty_history_returns_none(self, tmp_dirs):
        _write_evidence_json(tmp_dirs["memory"], [])
        assert check_test_evidence_staleness(tmp_dirs["memory"]) is None

    def test_custom_threshold_respected(self, tmp_dirs):
        ts = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        _write_evidence_json(tmp_dirs["memory"], [_evidence_record(ts)])
        assert check_test_evidence_staleness(tmp_dirs["memory"], threshold_s=3600) is None
        result = check_test_evidence_staleness(tmp_dirs["memory"], threshold_s=60)
        assert result is not None and result.reason == "stale"


class TestHardGateEnabled:
    def test_enabled_when_env_is_one(self):
        assert is_evidence_hard_gate_enabled({"EVIDENCE_GATE_HARD": "1"}) is True

    def test_disabled_when_env_is_zero(self):
        assert is_evidence_hard_gate_enabled({"EVIDENCE_GATE_HARD": "0"}) is False

    def test_disabled_when_env_absent(self):
        assert is_evidence_hard_gate_enabled({}) is False


class TestValidateMemoryDomain:
    def test_valid_domains_return_none(self):
        for domain in MEMORY_DOMAINS:
            assert validate_memory_domain(domain) is None

    def test_invalid_domain_returns_message(self):
        message = validate_memory_domain("bogus")
        assert message is not None
        assert "bogus" not in message or "domain" in message.lower()
        for domain in MEMORY_DOMAINS:
            assert domain in message

    def test_canonical_domains_present(self):
        assert set(MEMORY_DOMAINS) == {"general", "oracle", "quantower", "trading", "reasoning"}

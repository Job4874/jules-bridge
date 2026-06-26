"""Tests for modules/context_orchestrator.py."""

import json
import os
import tempfile

from modules.context_orchestrator import build_context_subagents


def test_builds_budgeted_capsules_without_middle_bloat():
    content = (
        "BEGIN context engineering needs memory stores and subagents.\n"
        + ("middle filler\n" * 100)
        + "MIDDLE_SHOULD_NOT_BE_IN_PACKET\n"
        + ("more middle filler\n" * 100)
        + "END long session evals need evidence gates.\n"
    )

    result = build_context_subagents(
        content=content,
        task="Optimize context handling",
        roles=["implementation_planner"],
        head_chars=80,
        tail_chars=80,
        max_packet_chars=3000,
    )

    assert result["status"] == "ready"
    assert result["context_strategy"] == "smart_truncation_head_tail_memory_store"
    assert result["capsules"][0]["omitted_middle_char_count"] > 0
    assert result["capsules"][0]["omitted_middle_sha256"]
    memory_store = result["context_memory_store"]
    assert memory_store["strategy"] == "head_tail_active_context_middle_memory_refs"
    assert memory_store["stores_raw_text"] is False
    assert memory_store["entries"][0]["omitted_middle_sha256"] == result["capsules"][0]["omitted_middle_sha256"]
    assert "MIDDLE_SHOULD_NOT_BE_IN_PACKET" not in json.dumps(memory_store)
    packet = result["subagents"][0]["packet_text"]
    assert "BEGIN context engineering" in packet
    assert "END long session evals" in packet
    assert "MIDDLE_SHOULD_NOT_BE_IN_PACKET" not in packet
    assert result["subagents"][0]["within_budget"] is True


def test_writes_context_subagent_packets_and_index():
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = build_context_subagents(
            content="Use TDD, HRM planning, and source-backed evidence.",
            task="Build context subagents",
            roles=["context_cartographer", "verification_agent"],
            write_packets=True,
            output_dir=tmp_dir,
        )

        assert result["status"] == "ready"
        assert len(result["packet_files"]) == 2
        for packet in result["packet_files"]:
            assert os.path.isfile(packet)
            with open(packet, encoding="utf-8") as handle:
                text = handle.read()
            assert "Do not reveal private chain-of-thought" in text
        assert os.path.isfile(os.path.join(tmp_dir, "CONTEXT_SUBAGENT_INDEX.md"))
        assert os.path.isfile(os.path.join(tmp_dir, "CONTEXT_SUBAGENT_STATE.json"))
        assert os.path.isfile(os.path.join(tmp_dir, "NO_SLOP_WORKFLOW.md"))
        assert os.path.isfile(os.path.join(tmp_dir, "CONTEXT_MEMORY_STORE.json"))
        assert os.path.isfile(os.path.join(tmp_dir, "CONTEXT_QUALITY_EVAL.md"))


def test_no_slop_workflow_has_spec_first_gates_and_budget():
    result = build_context_subagents(
        content="Find the flow, write the spec, then implement with evidence.",
        task="No slop workflow",
        roles=["implementation_planner"],
        context_window_chars=10000,
        max_context_utilization=0.4,
    )

    workflow = result["no_slop_workflow"]
    assert workflow["mode"] == "spec_first"
    assert [phase["id"] for phase in workflow["phases"]] == ["research", "plan", "implement"]
    assert workflow["review_gates"] == [
        "review_research_before_plan",
        "review_plan_before_code",
        "record_evidence_before_done",
    ]
    assert result["context_budget"]["target_utilization_ratio"] == 0.4
    assert result["context_budget"]["target_active_chars"] == 4000
    assert result["context_budget"]["over_budget"] is False


def test_context_budget_flags_over_budget_and_requests_compaction():
    result = build_context_subagents(
        content=("research context\n" * 400),
        context_window_chars=1000,
        max_context_utilization=0.4,
    )

    budget = result["context_budget"]
    assert budget["over_budget"] is True
    assert "intentional_compaction" in budget["recommendation"]
    assert result["no_slop_workflow"]["compaction_required"] is True


def test_long_session_eval_plan_uses_ten_plus_one_probe():
    result = build_context_subagents(
        content="Long session evals should load 10 turns and test the 11th follow-up.",
        roles=["verification_agent"],
    )

    eval_plan = result["long_session_eval_plan"]
    assert eval_plan["preload_turns"] == 10
    assert eval_plan["probe_turn"] == 11
    assert eval_plan["signal"] == "long_session_evals"
    packet = result["subagents"][0]["packet_text"]
    assert "preload 10 turns" in packet
    assert "probe turn 11" in packet


def test_missing_source_is_reported_without_raising_or_leaking_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        missing = os.path.join(tmp_dir, "missing.txt")

        result = build_context_subagents(source_paths=[missing])

        assert result["status"] == "blocked"
        assert result["error"] == "no readable source content"
        assert result["sources"][0]["readable"] is False
        assert result["sources"][0]["path_ref"].startswith("path-ref:")
        assert missing not in result["sources"][0]["error"]


def test_role_filter_selects_requested_role_only():
    result = build_context_subagents(
        content="Context management should delegate heavy search to subagents.",
        roles=["memory_curator"],
    )

    assert [agent["role_id"] for agent in result["subagents"]] == ["memory_curator"]


def test_capsule_excerpts_redact_local_paths_inside_source_text():
    result = build_context_subagents(
        content=(
            "Read C:\\Users\\abdul\\.codex\\attachments\\abc\\pasted-text-1.txt \r\n"
            "before continuing with context engineering.   \r\n"
        ),
        roles=["context_cartographer"],
    )

    packet = result["subagents"][0]["packet_text"]
    assert "C:\\Users\\abdul" not in packet
    assert "attachments\\abc" not in packet
    assert "path-redacted" in packet
    assert "\r" not in packet
    assert all(line == line.rstrip() for line in packet.splitlines())

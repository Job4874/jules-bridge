"""Tests for modules/akc_module.py.

AKC means Agent Knowledge Context: a durable, source-backed checkpoint
for the rules agents must load before daily work.
"""
import os
import tempfile

from modules.akc_module import (
    build_akc_context,
    check_akc_readiness,
    load_akc_checkpoint,
)


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


class TestBuildAKCContext:
    def test_builds_source_inventory_with_hashes_and_path_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "transcript.txt")
            checkpoint = os.path.join(tmp, "AKC_CONTEXT_CHECKPOINT.md")
            _write(
                source,
                "Run grill me before coding. Use TDD. Prove work with evidence.\n",
            )

            result = build_akc_context([source], checkpoint_path=checkpoint)

            assert result["status"] == "partial"
            assert result["source_count"] == 1
            assert result["readable_count"] == 1
            assert len(result["sources"][0]["sha256"]) == 64
            assert result["sources"][0]["path_ref"].startswith("path-ref:")
            assert source not in result["checkpoint_markdown"]
            assert os.path.exists(checkpoint)

    def test_missing_sources_are_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "missing.txt")
            result = build_akc_context([missing], checkpoint_path=None)

            assert result["status"] == "blocked"
            assert result["readable_count"] == 0
            assert result["missing_count"] == 1
            assert result["sources"][0]["readable"] is False
            assert result["sources"][0]["error"]
            assert missing not in result["sources"][0]["error"]
            assert missing not in result["checkpoint_markdown"]

    def test_extracts_operating_rules_from_transcript_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "all-rules.txt")
            _write(
                source,
                "\n".join([
                    "context files keep the agent grounded",
                    "grill me creates a shared design concept",
                    "TDD forces small feedback loops",
                    "evidence and SHA-256 prove tests ran",
                    "deep modules expose a simple interface",
                    "Ralph loop picks one ticket at a time",
                    "HRM has a high-level planner and low-level worker",
                    "smart zone and dumb zone control context window size",
                    "Google Drive and Google Cloud can back the storage layer",
                ]),
            )

            result = build_akc_context([source], checkpoint_path=None)
            rule_keys = {rule["key"] for rule in result["operating_rules"]}

            assert result["status"] == "ready"
            assert "grill_alignment" in rule_keys
            assert "tdd_feedback" in rule_keys
            assert "evidence_gates" in rule_keys
            assert "deep_modules" in rule_keys
            assert "hrm_reasoning" in rule_keys
            assert "smart_zone" in rule_keys
            assert "google_drive_cloud" in rule_keys


class TestLoadAKCCheckpoint:
    def test_load_checkpoint_reports_existing_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = os.path.join(tmp, "AKC_CONTEXT_CHECKPOINT.md")
            _write(checkpoint, "# AKC Context Checkpoint\n\nhello")

            result = load_akc_checkpoint(checkpoint_path=checkpoint)

            assert result["exists"] is True
            assert result["content"].startswith("# AKC Context Checkpoint")
            assert result["char_count"] > 0

    def test_load_checkpoint_missing_is_empty_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = load_akc_checkpoint(
                checkpoint_path=os.path.join(tmp, "missing.md")
            )

            assert result["exists"] is False
            assert result["content"] == ""
            assert result["char_count"] == 0


class TestCheckAKCReadiness:
    def test_ready_checkpoint_passes_required_rule_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = os.path.join(tmp, "AKC_CONTEXT_CHECKPOINT.md")
            _write(
                checkpoint,
                "\n".join([
                    "# AKC Context Checkpoint",
                    "",
                    "- status: ready",
                    "- operating_rule_count: 2",
                    "",
                    "## Operating Rules",
                    "",
                    "- `context_system`: Load compact context.",
                    "- `tdd_feedback`: Use tests first.",
                ]),
            )

            result = check_akc_readiness(
                checkpoint_path=checkpoint,
                required_rules=["context_system", "tdd_feedback"],
            )

            assert result["ready"] is True
            assert result["status"] == "ready"
            assert result["missing_required_rules"] == []
            assert all(gate["passed"] for gate in result["gates"])

    def test_default_required_rules_cover_all_transcript_operating_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = os.path.join(tmp, "AKC_CONTEXT_CHECKPOINT.md")
            _write(
                checkpoint,
                "\n".join([
                    "# AKC Context Checkpoint",
                    "",
                    "- status: ready",
                    "",
                    "## Operating Rules",
                    "",
                    "- `context_system`: Load compact context.",
                    "- `grill_alignment`: Align before planning.",
                    "- `tdd_feedback`: Use tests first.",
                    "- `evidence_gates`: Prove the work.",
                    "- `deep_modules`: Keep simple interfaces.",
                    "- `ralph_loop`: Work one ticket at a time.",
                    "- `hrm_reasoning`: Separate planner and worker.",
                    "- `smart_zone`: Keep context bounded.",
                    "- `google_drive_cloud`: Verify external storage state.",
                ]),
            )

            result = check_akc_readiness(checkpoint_path=checkpoint)

            assert result["ready"] is True
            assert "google_drive_cloud" in result["required_rules"]

    def test_missing_checkpoint_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = check_akc_readiness(
                checkpoint_path=os.path.join(tmp, "missing.md"),
                required_rules=["context_system"],
            )

            assert result["ready"] is False
            assert result["status"] == "blocked"
            assert "context_system" in result["missing_required_rules"]
            assert result["gates"][0]["name"] == "checkpoint_exists"
            assert result["gates"][0]["passed"] is False

    def test_missing_required_rules_makes_readiness_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = os.path.join(tmp, "AKC_CONTEXT_CHECKPOINT.md")
            _write(
                checkpoint,
                "\n".join([
                    "# AKC Context Checkpoint",
                    "",
                    "- status: ready",
                    "",
                    "## Operating Rules",
                    "",
                    "- `context_system`: Load compact context.",
                ]),
            )

            result = check_akc_readiness(
                checkpoint_path=checkpoint,
                required_rules=["context_system", "evidence_gates"],
            )

            assert result["ready"] is False
            assert result["status"] == "partial"
            assert result["missing_required_rules"] == ["evidence_gates"]
            assert result["gates"][-1]["name"] == "required_rules_present"
            assert result["gates"][-1]["passed"] is False

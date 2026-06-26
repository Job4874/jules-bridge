"""Tests for durable Quantower UI memory.

Ticket 002 is documentation-heavy, but it still has acceptance criteria:
the memory file must exist, include concrete UI gotchas, cite screenshot
evidence, and be cross-referenced from the project gotchas file.
"""
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUANTOWER_MEMORY = PROJECT_ROOT / "memory" / "quantower.md"
GOTCHAS = PROJECT_ROOT / "context" / "05_gotchas.md"


def _memory_text() -> str:
    return QUANTOWER_MEMORY.read_text(encoding="utf-8")


class TestQuantowerMemory:
    def test_quantower_memory_file_exists(self):
        assert QUANTOWER_MEMORY.exists()

    def test_contains_required_quantower_ui_sections(self):
        text = _memory_text()

        for heading in [
            "## Window Title Patterns",
            "## Modal Dialogs",
            "## Connection Status Indicators",
            "## DLL Load Confirmation Pattern",
            "## Known Failure Modes",
        ]:
            assert heading in text

    def test_contains_three_session_observations(self):
        text = _memory_text()

        assert text.count("## Session ") >= 3
        assert "real observation" not in text.lower()

    def test_references_screenshot_evidence(self):
        text = _memory_text()

        expected_refs = [
            "qw_live.png",
            "qw_connections.png",
            "qw_dialog_Strategies_manager.png",
        ]
        for ref in expected_refs:
            assert ref in text

    def test_documents_required_failure_modes(self):
        text = _memory_text().lower()

        for phrase in [
            "dll not found",
            "wrong architecture",
            "strategy already running",
        ]:
            assert phrase in text

    def test_gotchas_cross_references_quantower_memory(self):
        gotchas = GOTCHAS.read_text(encoding="utf-8")

        assert "memory/quantower.md" in gotchas

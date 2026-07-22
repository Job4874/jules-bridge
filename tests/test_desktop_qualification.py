"""Live desktop qualification test.

Runs the full qualification sequence (Notepad open, type, screenshot, close)
on a real desktop. Skipped when not running on Windows with a visible desktop.

Run explicitly with: .venv\\Scripts\\python.exe -m pytest tests/test_desktop_qualification.py -v -s
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_IS_WINDOWS_DESKTOP = os.name == "nt"

from modules.desktop_worker import DesktopWorker


@unittest.skipUnless(_IS_WINDOWS_DESKTOP, "Requires a visible Windows desktop")
class TestDesktopQualification(unittest.TestCase):
    """Live integration test: opens Notepad, types, screenshots, closes."""

    def test_qualification_sequence(self):
        """Run the full desktop qualification and verify screenshots exist."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "qualification"
            worker = DesktopWorker(headless=False)
            result = worker.run_qualification_sequence(output_dir=output_dir)

            # Must have run to completion
            self.assertIn(result["status"], ("pass", "partial"),
                          f"Qualification failed: {result.get('error', result.get('steps', []))}")

            # Must have produced screenshots
            self.assertGreater(len(result["screenshots"]), 0,
                               "No screenshots were taken — display issue?")

            # Verify screenshot files actually exist
            for ss_path in result["screenshots"]:
                self.assertTrue(Path(ss_path).exists(),
                                f"Screenshot missing: {ss_path}")

            # Must have the qualification text in the result
            self.assertIn("UnifiedOperator qualification test", result["qualification_text"])

            # Print evidence for manual inspection
            print(f"\n=== Desktop Qualification Result ===")
            print(f"Status: {result['status']}")
            print(f"Screenshots: {len(result['screenshots'])}")
            for ss in result["screenshots"]:
                print(f"  - {ss}")
            print(f"Steps completed: {len(result['steps'])}")
            for step in result["steps"]:
                print(f"  Step {step.get('step', '?')}: {step.get('action', '?')}")


if __name__ == "__main__":
    unittest.main()

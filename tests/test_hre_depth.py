import os
import tempfile
import json
from dataclasses import dataclass
from modules.reasoning_module import (
    ReasoningTrace,
    HLevelPlan,
    HaltDecision,
    score_hre_depth,
    discover_skills,
    inject_gotcha,
)

def test_score_hre_depth():
    with tempfile.TemporaryDirectory() as tmpdir:
        eval_path = os.path.join(tmpdir, "eval_results.json")
        
        # Test trace with good depth
        trace = ReasoningTrace(
            problem="test",
            plan=HLevelPlan(steps=[], goal_statement="", confidence=1.0, reasoning="", model="stub"),
            actions=[],
            halt=HaltDecision(should_halt=True, reason="goal_reached", steps_used=1, steps_budget=5),
            answer="done",
            elapsed_ms=100.0,
            hre_passes_taken=3,
            self_unblocked=True,
            blockers_resolved=["syntax error", "import error"],
            knowledge_sources_checked=["context/02_architecture.md"]
        )
        
        import unittest.mock as mock
        with mock.patch("modules.reasoning_module.open", mock.mock_open()) as mock_file:
            with mock.patch("os.makedirs"):
                res = score_hre_depth(trace)
                
                assert "depth_score" in res
                assert "self_unblock_rate" in res
                assert "gaps_found" in res
                assert res["self_unblock_rate"] == 1.0
                assert res["depth_score"] == 3.0
                
                import modules.reasoning_module as rm
                mock_file.assert_called_with(os.path.join(rm._root_dir, "memory", "eval_results.json"), "a", encoding="utf-8")

def test_discover_skills():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy skill
        skill_dir = os.path.join(tmpdir, "my-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: my-skill\ndescription: A test skill\ntrigger_condition: When testing\n---\n# Body")
            
        skills = discover_skills(tmpdir)
        assert len(skills) == 1
        assert skills[0]["name"] == "my-skill"
        assert skills[0]["description"] == "A test skill"
        assert skills[0]["trigger_condition"] == "When testing"
        assert skills[0]["skill_path"] == os.path.join(skill_dir, "SKILL.md")

def test_inject_gotcha():
    with tempfile.TemporaryDirectory() as tmpdir:
        gotchas_path = os.path.join(tmpdir, "05_gotchas.md")
        with open(gotchas_path, "w", encoding="utf-8") as f:
            f.write("# Gotchas\n\n## bridge.py\n\n- some existing gotcha\n\n## fs_service\n\n- another one\n")
            
        import unittest.mock as mock
        with mock.patch("modules.reasoning_module._GOTCHAS_PATH", gotchas_path):
            res = inject_gotcha("bridge.py", "never use print")
            assert res["status"] == "ok"
            assert res["module"] == "bridge.py"
            
            with open(gotchas_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            assert "## bridge.py" in content
            assert "never use print" in content

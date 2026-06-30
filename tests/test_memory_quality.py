import os
import tempfile
from modules.retrospective_module import assess_memory_quality

def test_assess_memory_quality():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = os.path.join(tmpdir, "general.md")
        with open(memory_path, "w", encoding="utf-8") as f:
            f.write("""# Memory
            
## Session 20250601T143022
- actionable item 1
- actionable item 2

## Undated Section
- some context

## Session 20260101T000000
- actionable item 3
""")
        
        res = assess_memory_quality(memory_path)
        
        assert "total_sections" in res
        assert "dated_sections" in res
        assert "stale_count" in res
        assert "actionable_count" in res
        assert "quality_score" in res
        
        assert res["total_sections"] == 3
        assert res["dated_sections"] == 2
        assert res["actionable_count"] == 4
        # 3 actionable items across 3 sections -> quality_score = 3/3 = 1.0 (if counting actionable bullet points)
        # Wait, the spec says `quality_score = actionable_count / total_sections`
        # and "actionable_count" could mean "number of actionable bullet points".
        # Let's say quality_score is exactly that.
        
        # Another test for poor quality
        poor_path = os.path.join(tmpdir, "poor.md")
        with open(poor_path, "w", encoding="utf-8") as f:
            f.write("""# Poor Memory
            
## Some context
just some text without bullet points

## Another context
more text
""")
        res_poor = assess_memory_quality(poor_path)
        assert res_poor["total_sections"] == 2
        assert res_poor["actionable_count"] == 0
        assert res_poor["quality_score"] == 0.0
        assert "recommendation" in res_poor

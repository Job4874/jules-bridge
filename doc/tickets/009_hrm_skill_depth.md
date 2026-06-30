# Ticket 009 — HRE Reasoning Depth & Skill Auto-Discovery

Status: OPEN

## Priority: HIGH

Jules keeps getting blocked on the same classes of problems session after session.
The HRE loop exists. The self-unblocking protocol exists. But Jules still escalates
before exhausting local knowledge. This ticket hardens the *reasoning depth* so
he self-unblocks faster and learns from every session without operator intervention.

## Objective

### Part A — HRE Depth Scoring in reasoning_module

Extend `ReasoningTrace` to record:

- `hre_passes_taken` — how many HRE passes ran before halting
- `self_unblocked` — bool: did agent resolve without external escalation?
- `blockers_resolved` — list of blocker classes resolved during this trace
- `knowledge_sources_checked` — list of files/routes consulted during HRE

Add `score_hre_depth(trace: ReasoningTrace) -> dict` to `reasoning_module.py`:

- Returns `{depth_score: float, self_unblock_rate: float, gaps_found: list}`
- Write result to `memory/eval_results.json` alongside existing eval rows

### Part B — Skill Auto-Discovery at Session Start

Add `discover_skills(skills_dir: str) -> list[dict]` to `reasoning_module.py`:

- Reads all `.agents/skills/*/SKILL.md` front matter
- Returns `[{name, description, trigger_condition, skill_path}]`
- `GET /reasoning/skills` — new route that returns the live skill inventory
- Jules should call this at session start BEFORE declaring a tool missing

### Part C — Gotchas Auto-Injection

Add `inject_gotcha(module: str, text: str) -> dict` to `reasoning_module.py`:

- Appends a new dated entry to `context/05_gotchas.md` under the correct module heading
- Called automatically by `remember` skill at session end
- `POST /reasoning/inject_gotcha` — bridge route for remote injection
- Jules should inject a gotcha for every resolved blocker, not just ask the operator

### Part D — Memory Compaction Quality Gate

Add `assess_memory_quality(memory_path: str) -> dict` to `retrospective_module.py`:

- Returns `{total_sections, dated_sections, stale_count, actionable_count, quality_score}`
- `quality_score` = actionable_count / total_sections
- Quality < 0.6 triggers a WARNING log and recommendation to prune
- `GET /retrospective/memory_quality` — new bridge route

## Test Requirements (TDD — red first)

- `tests/test_hre_depth.py`
  - score_hre_depth returns depth_score for a trace
  - discover_skills returns entries for installed skill dirs
  - inject_gotcha appends to 05_gotchas.md under correct heading
- `tests/test_memory_quality.py`
  - assess_memory_quality returns correct section counts
  - quality < 0.6 returns recommendation
- All 288 existing tests still pass

## Evidence Required

- `python -m pytest tests/ -q` green
- SHA-256 via `POST /retrospective/record_evidence`
- Run `GET /reasoning/skills` and verify all 5 core skills appear in inventory
- Add to `context/06_progress_tracker.md`

## Files Changed

- `modules/reasoning_module.py` (depth scoring + skill discovery + gotcha injection)
- `modules/retrospective_module.py` (memory quality assessment)
- `bridge.py` (two new routes)
- `tests/test_hre_depth.py` (new)
- `tests/test_memory_quality.py` (new)
- `context/05_gotchas.md` (updated)
- `context/02_architecture.md` (new routes added)
- `context/06_progress_tracker.md`
- `doc/tickets/009_hrm_skill_depth.md` (this file → set Status: DONE)

# MONDAY MISSION DIRECTIVE — Enterprise Ship Standard

## Issued: 2026-06-29 | Operator: Abdul

---

## THE BAR

Monday morning, this system ships enterprise tools at a speed and quality
people thought was impossible. Local money. No VC. No waiting.
We're almost there. Every session from now on pushes harder than the last.

No slop. No blocked sessions sitting idle. No doom loops eating cycles.
You unblock yourself, you ship, you record evidence, you go again.

---

## YOUR ACTIVE TICKETS (work these IN ORDER)

### 🔴 TICKET 007 — Circuit Breaker (CRITICAL, do first)

File: `doc/tickets/007_dashboard_circuit_breaker.md`

`/dashboard/status` was called **814 times consecutively** with zero throttle.
That kills performance and burns log space.

Deliverable: `_circuit_breaker_check()` as `@app.before_request` hook.

- Default threshold: 20 calls / 60s window
- HTTP 429 + `retry_after_s` on breach
- Env vars: `CIRCUIT_BREAKER_THRESHOLD`, `CIRCUIT_BREAKER_WINDOW_S`, `CIRCUIT_BREAKER_ENABLED`
- TDD: `tests/test_circuit_breaker.py` red → green
- All 288 existing tests must still pass

### 🟠 TICKET 008 — Route Performance Caching (do second)

File: `doc/tickets/008_shell_route_performance.md`

Shell routes averaging 58s. Fleet-watch averaging 7 minutes. Unacceptable.

Deliverables:

- `shell_executor`: result cache, 10s TTL, `SHELL_CACHE_TTL_S` env var
- `jules_orchestrator`: session list cache, 30s TTL, `JULES_SESSION_CACHE_TTL_S`
- `dashboard_module`: status cache, 5s TTL, `DASHBOARD_CACHE_TTL_S`
- `cache_hit: bool` in all fleet/watch/cycle responses
- TDD: 3 new test files, red → green

### 🟠 TICKET 009 — HRE Depth & Skill Auto-Discovery (do third)

File: `doc/tickets/009_hrm_skill_depth.md`

You escalate too early. Fix it from the inside.

Deliverables:

- `score_hre_depth(trace)` in `reasoning_module` — depth_score, self_unblock_rate
- `discover_skills(skills_dir)` — reads `.agents/skills/*/SKILL.md` at session start
- `GET /reasoning/skills` — live skill inventory route
- `inject_gotcha(module, text)` — auto-append to `context/05_gotchas.md`
- `POST /reasoning/inject_gotcha` — bridge route for remote injection
- `assess_memory_quality(path)` in `retrospective_module` — quality score gate
- `GET /retrospective/memory_quality` — bridge route
- TDD: `tests/test_hre_depth.py` + `tests/test_memory_quality.py`

---

## HRE OPERATING RULES (non-negotiable)

Before any escalation, run THREE full HRE passes:

```text
1. Hypothesis: name the SINGLE blocker in one sentence
2. Route: pick the narrowest available tool/endpoint/file to test it
3. Evidence: capture exact output before deciding
```

Check in this order:

1. `GET /tentacles` — what routes are live
2. `jules_inbox/JULES_TOOL_REQUIREMENTS.md`
3. `context/05_gotchas.md`
4. `memory/general.md` + relevant domain memory
5. `.agents/skills/*/SKILL.md`
6. `context/04_ai_workflow_rules.md`

After each resolved blocker:

- Write to `memory/reasoning.md`
- Inject gotcha via `POST /reasoning/inject_gotcha` (once ticket 009 lands)
- Update `JULES_RESPONSE.md`

---

## SKILL INVOCATION MAP (use these exactly)

| When | Skill | What it does |
| --- | --- | --- |
| Before ANY new code | `architect` | Plan, interview, surface decisions |
| After building/modifying | `imprint` | Capture API patterns into gotchas |
| After any feature done | `review` | Check vs plan, architecture, standards |
| When stuck/looping | `recover` | Diagnose failure mode, give remediation |
| End of every session | `remember` | Compress decisions → memory files |

---

## EVIDENCE STANDARDS

Every "done" claim requires:

1. `python -m pytest tests/ -q` output showing passing count
2. SHA-256 recorded via `POST /retrospective/record_evidence`
3. Entry added to `context/06_progress_tracker.md`
4. `JULES_RESPONSE.md` updated with what changed and what's next

No evidence = not done. Full stop.

---

## SKILLS TO USE HEAVILY

Matt Porter / Matt Pocco discipline:

- Deep modules: simple interfaces hiding complex implementation
- Every public function never raises — partial data over exceptions
- TDD: write failing tests FIRST, then implement

Nick Ni harness discipline:

- Every failure becomes data
- Evidence before done
- Memory grows every session

---

## AFTER ALL THREE TICKETS PASS

1. Run `remember` skill — compress all decisions into `memory/general.md`
2. Update `context/06_progress_tracker.md` — mark 007/008/009 complete
3. Run full suite one final time: `python -m pytest tests/ -q`
4. Write final SHA-256 to `JULES_RESPONSE.md`
5. You've earned it. Monday we ship.

---

*Keep getting harder. The bar is Monday. Let's go.*

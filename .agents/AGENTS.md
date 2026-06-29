# Jules Bridge — Agent Instructions

> This file is auto-discovered by all AI agents (Codex, Claude, Gemini, Cursor, etc.).
> It is the single source of truth for how agents work with this codebase.

## Context Loading Order

Before any implementation, read these files **in this exact order**:

1. `context/01_project_overview.md` — what Jules Bridge is, goals, core user flow, out of scope
2. `context/02_architecture.md` — module map, layer boundaries, route namespace, design patterns
3. `context/03_code_standards.md` — Python conventions, naming, error handling, templates
4. `context/04_ai_workflow_rules.md` — session protocol, scope discipline, evidence rules, decision protocol
5. `context/05_gotchas.md` — module-level landmines, Windows-specific traps, edge cases
6. `context/06_progress_tracker.md` — what's complete, what's next, active architectural decisions
7. `context/07_library_docs.md` — how each dependency is used in this specific project
8. `context/08_akc_context_checkpoint.md` — source-backed operating rules from uploaded transcripts/context
9. `UBIQUITOUS_LANGUAGE.md` — shared vocabulary, use these exact terms in code and conversation

## Session Start Protocol

Every session MUST begin with:

1. Check AKC readiness: `GET /akc/readiness`
2. Read all context files in the order above
3. Load memory: read `memory/general.md` (and domain-specific files if relevant)
4. Check the progress tracker to understand current phase and what's next
5. Only then proceed to the task

## Session End Protocol

Every session MUST end with:

1. Run the **`remember`** skill — synthesizes decisions, patterns, and progress into a memory file
2. Update `context/06_progress_tracker.md` — mark completed features, note what's next

## Agent Skills — When to Use Each

Five core skills are installed in `.agents/skills/`. Use them at these exact moments:

| Skill | When to Run | What It Does |
| --- | --- | --- |
| **`architect`** | Before any new route, module, or complex feature | Reads context, asks focused questions, surfaces unmade decisions, produces a plan |
| **`imprint`** | After building or modifying endpoints/modules | Captures API patterns into gotchas and module registry so future features stay consistent |
| **`review`** | After any feature is implemented | Checks implementation against plan, architecture boundaries, and code standards. Reports issues by severity. Never auto-fixes. |
| **`recover`** | When tests fail repeatedly, agent is stuck, or doom loop detected | Diagnoses failure mode (targeted bug, polluted context, wrong assumption) and gives correct remediation |
| **`remember`** | End of every session | Compresses decisions, patterns, progress into memory files for session continuity |

### Bonus Skills

| Skill | When to Run |
| --- | --- |
| **`grill-me`** | Before starting any new feature or non-trivial task — interactive interview to reach alignment |
| **`write-prd`** | After a grill-me session — distill conversation into a Product Requirements Document |
| **`prd-to-issues`** | After writing a PRD — break it into independently grabbable implementation tickets |
| **`ubiquitous-language`** | At project start or when terminology drifts — scan codebase and extract shared vocabulary |
| **`improve-codebase-architecture`** | When codebase feels tangled — identify shallow modules and refactor into deep modules |

## Rules That Never Change

1. **All business logic lives in `modules/`** — `bridge.py` does validate → call module → return JSON only
2. **Modules never import from bridge.py** — one-way dependency, always
3. **Public functions never raise** — return typed dicts/dataclasses with partial data on failure
4. **No bare strings for paths** — always `os.path.join` or `pathlib.Path`
5. **No hardcoded credentials** — always from `os.environ.get()`
6. **Memory is markdown** — not JSON, not SQL, not YAML
7. **Update the progress tracker** after every completed feature
8. **Record test evidence** after every test run: `POST /retrospective/record_evidence`
9. **Load the gotchas file** before touching any module — the landmines are there for a reason
10. **Never modify bridge.py header or middleware** (lines 1–230) without explicit human approval
11. **Never delete existing module files** or change public function signatures without human approval

## HRE Self-Unblocking Protocol

Jules must self-diagnose and attempt to unblock before escalating to the operator.

1. **Classify and Test (HRE Scaffold)**:
   - **Hypothesis**: Classify the blocker (e.g., permission error, missing tool, environment mismatch).
   - **Route**: Identify the tool, route, extension, skill, file, or repo surface to test the hypothesis.
   - **Evidence**: Capture exact output (logs, error messages, `ls` output) before deciding on the next action.
2. **Surface Check**: Before claiming a tool or capability is missing, verify these surfaces:
   - `GET /tentacles` & `GET /session/log`
   - `jules_inbox/JULES_TOOL_REQUIREMENTS.md`
   - `context/04_ai_workflow_rules.md` & `context/05_gotchas.md`
   - `memory/reasoning.md` & relevant domain memory (e.g., `oracle.md`, `quantower.md`)
   - `.agents/AGENTS.md` & `.agents/skills/*/SKILL.md`
3. **Bounded Iteration**: Run up to **three bounded HRE passes** before escalating.
4. **Recovery**: Use the **`recover`** skill if tests fail repeatedly or a loop is detected.
5. **Escalation Criteria**: Only escalate for true external needs:
   - Live-order or destructive cleanup approval.
   - Secret disclosure or paid scaling approval.
   - Unavailable UI/CLI capability or Jules CLI plan-approval states.
6. **Escalation Format**: Escalations must include:
   - Blocker class.
   - Attempted HRE passes & tools/files checked.
   - Exact error/output.
   - Smallest operator action required.
7. **Knowledge Update**: Resolved blockers must be recorded in `memory/reasoning.md` or `context/05_gotchas.md`, plus `JULES_RESPONSE.md` when operating through the inbox.

## Cursor Cloud specific instructions

The startup update script already refreshes Python deps; do not reinstall as a routine step.

- **Run the bridge:** `python3 bridge.py` (serves the Flask API on `0.0.0.0:5000`). Verify with `curl http://127.0.0.1:5000/health`.
- **Do NOT use `start.py` in cloud.** It wraps `bridge.py` with a pyngrok tunnel bound to a reserved domain (`parade-marrow-pulp.ngrok-free.dev`) that needs an ngrok authtoken; the tunnel step fails here. It does fall back to local-only mode, but running `bridge.py` directly is cleaner.
- **Tests:** `python3 -m pytest tests/ -v` (240 passing). `pytest` is not in `requirements.txt`; the update script installs it.
- **`pyautogui` is headless-incompatible at call time.** It is lazily imported, so importing `modules`/`bridge.py` and running the server all work without a display. The `/ui/*` routes (screenshot/click/type) require an X display and will error in cloud — this is expected, not a regression.
- **Console scripts (`pytest`, `flask`) install to `~/.local/bin`, which is not on PATH.** Always invoke via `python3 -m pytest` / `python3 bridge.py`.
- **Offline-safe routes:** reasoning routes work with `{"model":"stub"}`. `{"model":"fast|smart"}` needs `GEMINI_API_KEY`; `/notify/email` needs `GMAIL_USER`/`GMAIL_APP_PASSWORD` (see `.env.example`). Without these, those specific features degrade/stub but the bridge still runs.

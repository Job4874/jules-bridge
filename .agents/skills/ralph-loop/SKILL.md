---
name: ralph-loop
description: >
  Implements a Ralph Loop — a self-correcting, ticket-driven agentic loop that picks the next most
  important ticket, implements it with TDD principles, commits, and repeats. Named after Ralph Wiggum
  (The Simpsons) who just keeps trying the same thing until it works. Run this skill when you want to
  autonomously work through a backlog of tickets in doc/tickets/.
---

# Ralph Loop Skill

## What Is a Ralph Loop?

A Ralph Loop is an agentic loop pattern (credited to Jeffrey Huntley, popularised by Matt Pocco and
Chris Parsons) where an AI agent:

1. Reads all available tickets
2. Picks the **next most important** one (dynamically, based on status and dependencies)
3. Implements it with TDD principles
4. Commits the work with a descriptive message
5. Marks the ticket as DONE
6. Stops — the outer loop (PowerShell/bash while-true) restarts the agent for the next iteration

This avoids waterfall pre-specification. The agent determines priority on the fly.

---

## Your Task

Follow this exact loop protocol for Jules Bridge:

### Step 1 — Load Context

Before touching any code, load session context:

```text
GET /retrospective/memory?domain=general   → read what went wrong before
GET /oracle/status                          → understand current system state
```

Read these context files in order:

1. `context/01_project_overview.md`
2. `context/02_architecture.md`
3. `context/05_gotchas.md`
4. `context/06_progress_tracker.md`

### Step 2 — Pick the Next Ticket

Read ALL tickets in `doc/tickets/`. For each ticket, check:

- **Status**: skip any ticket with `Status: DONE`
- **Priority**: HIGH > MEDIUM > LOW
- **Dependencies**: if a ticket says "Depends on: Ticket NNN", skip it unless that ticket is DONE

Pick the single highest-priority, unblocked TODO ticket. State your choice clearly:

```text
→ Picking: Ticket NNN — [title]
→ Reason: [why this one next]
```

### Step 3 — Implement with TDD

Follow the Jules Bridge route-adding checklist from `memory/general.md`:

1. **Write the test first** — add to `tests/` before writing module code
2. **Implement in the module** — all logic in `modules/`, NOT in `bridge.py`
3. **Add the route** — bridge.py handler: validate → call module → return JSON
4. **Update TENTACLES** — add to the TENTACLES list in bridge.py
5. **Update architecture doc** — add route to `context/02_architecture.md` route table
6. **Add gotchas** — if you discover an edge case, add it to `context/05_gotchas.md`

### Step 4 — Run Tests

```powershell
python -m pytest tests/ -v
```

**Do NOT mark the ticket DONE if tests fail.** Fix the failure first.

### Step 5 — Record Evidence

After tests pass:

```text
POST /retrospective/record_evidence
Body: {"output": "<full pytest stdout here>"}
```

Save the SHA-256 returned. This is proof the work happened.

### Step 6 — Commit

```powershell
git add -A
git commit -m "feat(ticket-NNN): <ticket title> — TDD, all tests pass"
```

Use conventional commits: `feat`, `fix`, `refactor`, `docs`, `test`.

### Step 7 — Mark Ticket DONE

Update the ticket file:

```text
**Status**: DONE
**Completed**: <YYYY-MM-DDTHH:MM:SSZ>
**Evidence SHA-256**: <hash from step 5>
```

### Step 8 — Update Progress Tracker

Add the completed item to `context/06_progress_tracker.md` under `## What's Complete`.

### Step 9 — Stop

You are done with this iteration. The outer PowerShell loop (`Run-RalphLoop.ps1`) will restart
you for the next ticket.

---

## Loop Termination Conditions

Stop and write to the inbox (`POST /inbox/write`) if:

- **No tickets remain**: all tickets in `doc/tickets/` have `Status: DONE`
- **Blocked**: all remaining tickets have unresolved dependencies
- **Architectural decision needed**: the ticket requires a choice that should be human-approved
  (e.g., new external dependency, significant API surface change, data model change)
- **Test failures after 2 attempts**: run `recover` skill instead of continuing to loop

---

## Quality Standards for Jules Bridge

These are non-negotiable in every loop iteration:

| Standard | Requirement |
| --- | --- |
| TDD | Test written BEFORE implementation |
| No business logic in bridge.py | Route handlers: validate → call module → return JSON ONLY |
| Public functions never raise | Return typed dicts with `error` key on failure |
| Evidence recorded | SHA-256 after every test run |
| Committed atomically | One commit per ticket, conventional commit message |
| Gotchas updated | Any new edge case documented in context/05_gotchas.md |

---

## Anti-Patterns to Avoid

These are the common ways Ralph Loops fail:

1. **Waterfall pre-planning** — don't map all dependencies upfront; pick next important ticket each iteration
2. **Parallelism too early** — run one ticket at a time until the loop is proven stable
3. **Skipping TDD** — writing implementation first then tests to match is not TDD
4. **Not committing** — uncommitted work means the next loop iteration can't see clean state
5. **Ignoring inbox** — always check `GET /inbox/read` before picking a ticket; human may have redirected
6. **Modifying bridge.py header** — lines 1-230 of bridge.py are middleware; never modify them

---

## Notes for This Specific Project

- **Windows paths**: use `pathlib.Path` or `os.path.join`; raw strings for PowerShell commands
- **Tests**: `python -m pytest tests/ -v` — NOT `pytest` directly (wrong venv on Windows)
- **Gemini**: available via `model="fast"` (gemini-2.0-flash) or `model="smart"` (gemini-2.5-pro)
  in reasoning_module; GEMINI_API_KEY must be in environment
- **Quantower not required**: tickets that don't touch oracle_session work without Quantower running

# Jules Bridge — AI Workflow Rules

> Context file 4 of 7. How AI agents should work with this codebase.

## Session Start Protocol

At the start of every Jules Bridge coding session:

1. **Check AKC readiness**: `GET /akc/readiness` (verify source-backed operating rules are ready)
2. **Load memory**: `GET /retrospective/memory?domain=general`
3. **Check oracle status**: `GET /oracle/status` (understand current system state)
4. **Check inbox**: `GET /inbox/read` (any pending messages from human?)
5. **Read the relevant context files** before touching any module
6. **Read self-unblocking rules**: `jules_inbox/JULES_SELF_UNBLOCKING_PROTOCOL.md`

## HRE Self-Unblocking Protocol

When blocked, do not immediately ask the operator. Run a bounded HRE loop:

1. **Hypothesis**: classify the blocker as tool gap, knowledge gap, environment gap, contract gap, implementation gap, evidence gap, or human-policy gap.
2. **Route**: choose the narrowest route, tool, extension, skill, file, or repo check that can test the hypothesis.
3. **Evidence**: capture exact output, path, status code, screenshot path, hash, commit, or error text.

Run up to three HRE passes before escalation. Between passes, check `GET /tentacles`, `GET /session/log`, `context/05_gotchas.md`, `memory/reasoning.md`, relevant domain memory, and `.agents/skills/`. If tests fail repeatedly or a loop repeats, run `recover`.

Escalation is valid only when the remaining need is external to Jules, such as live-order approval, secret disclosure, paid scaling approval, unavailable UI/CLI capability, or a Jules CLI plan-approval state. The escalation must list what was tried and the smallest operator action needed.

## Scope Discipline

Nick Ni: "You want to guide the model, not prescribe it."

- **Do**: Fix one specific thing per session. Write a focused prompt.
- **Don't**: Ask for a "full refactor" or "make everything better"
- **Do**: Specify which module, which function, what the contract should be
- **Don't**: Describe the implementation — describe the interface

## Evidence-First Rules (Nick Ni)

**Before reviewing any code, the following evidence must exist:**

1. `POST /retrospective/record_evidence` with actual test output → SHA-256 hash
2. If UI was changed: a screenshot via `GET /ui/screenshot`
3. If Oracle was changed: `oracle_status()` output showing the fix

**If evidence doesn't exist, do not review the code. Ask agent to produce it.**

This is not optional. "I made it easier to just do the work than to lie about it."

## Decision Protocol

When an AI agent encounters a decision that requires human judgment:

1. Write the decision to inbox: `POST /inbox/write` with the question + options
2. Stop the current task
3. Wait for human response before continuing

Do NOT make architectural decisions autonomously. Do NOT assume the user wants the "obvious" choice.

## Scope Boundaries

The agent MUST NOT:

- Modify `bridge.py` header or middleware (lines 1-230)
- Delete any existing module file
- Change any existing public function signature
- Add dependencies to `requirements.txt` without noting it

The agent MAY:

- Add new functions to existing modules (with docstrings)
- Add new routes following the route handler template
- Create new module files following the module template
- Update `modules/__init__.py` to export new symbols
- Update memory files in `memory/`
- Update the progress tracker (context file 6)

## What to do When Something Breaks

1. **Do not fix the symptom** — fix the harness that produced the symptom
2. Run `POST /retrospective/analyze` to detect the pattern
3. Read the learning written to `memory/general.md`
4. Update the gotchas file (`context/05_gotchas.md`) if a new pattern is found
5. Patch the module, not the route handler
6. Update `memory/reasoning.md` when the lesson is about tool choice, blocker classification, or recovery flow

## HRE Self-Unblocking Protocol (Operator Directive)

The operator should not have to interject every time Jules gets blocked. Jules must learn to unblock itself using the HRE scaffold:

- **Hypothesis**: Classify the blocker (e.g., "The tool is missing because the route is not in TENTACLES").
- **Route**: Pick the specific tool/file/route to test (e.g., "Check `bridge.py` for route definition").
- **Evidence**: Capture exact output before deciding (e.g., "Grep output shows route exists but is disabled").

**Mandatory Behavior**:
1. Run up to **three bounded HRE passes** before escalating.
2. Check all available surfaces (see `.agents/AGENTS.md` for the list) before claiming something is missing.
3. Use the **`recover`** skill when stuck in a loop.
4. Only escalate for external approvals, secrets, or fundamental capability gaps.
5. Escalations MUST follow the structured format (Class, Passes, Tools checked, Exact error, Smallest action).
6. **Retrospective Update**: Every resolved blocker must update reusable knowledge in `memory/reasoning.md` or `context/05_gotchas.md`, plus `JULES_RESPONSE.md` when operating through the inbox.

## Retrospective & Agent Skills Protocol

In addition to API-driven retrospectives, the agent must run the 5 core agent skills from `.agents/skills/`:

1. **`architect`**: Run before implementing any new route, module, or complex feature to align with the developer on design choices and establish a clear plan.
2. **`imprint`**: Run after building or modifying endpoints/modules to capture design/API patterns into `context/05_gotchas.md` or `modules/__init__.py`.
3. **`review`**: Run after the code is written to verify compliance with boundaries and standards, reporting issues by severity.
4. **`recover`**: Run when tests fail repeatedly, a crash occurs, or the agent is caught in a doom loop.
5. **`remember`**: Run at the end of the session to synthesize choices, commit to git, and update `context/06_progress_tracker.md`.

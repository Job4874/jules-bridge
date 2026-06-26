# Jules Bridge — AI Workflow Rules

> Context file 4 of 6. How AI agents should work with this codebase.

## Session Start Protocol

At the start of every Jules Bridge coding session:

1. **Load memory**: `GET /retrospective/memory?domain=general`
2. **Check oracle status**: `GET /oracle/status` (understand current system state)
3. **Check inbox**: `GET /inbox/read` (any pending messages from human?)
4. **Read the relevant context files** before touching any module

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

## Retrospective Trigger

Run retrospective at the end of every session or after any test failure:
```
POST /retrospective/analyze {}
GET /retrospective/memory?domain=general
```

The retrospective output shows:
- Which routes were called N times consecutively (doom loops)
- Which error types recurred (harness bugs)
- Which routes were slow (performance issues)

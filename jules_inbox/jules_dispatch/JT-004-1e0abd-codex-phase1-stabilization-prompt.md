# Jules Worker Packet JT-004-1e0abd

- instance_index: 3
- status: needs_review
- task_type: antigravity
- source: C:\Users\abdul\jules-bridge\jules_inbox\antigravity_offload_queue.txt
- fingerprint: 1e0abd9928b0
- repo_path: C:\aotp\projects\OracleV5

## Objective
Execute this Antigravity Codex handover prompt: CODEX PHASE1 STABILIZATION PROMPT

## Task Details
- File: C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS\CODEX_PHASE1_STABILIZATION_PROMPT.md
- Issue: Execute Antigravity Codex handover prompt end-to-end
- Language: markdown
- Rationale: Offload large Codex handover work to Jules remote workers.

## Operating Rules
- Work on one card only; do not opportunistically refactor unrelated code.
- Do not stop at a plan or ask for plan approval; plan briefly in the report and proceed unless a hard blocker prevents work.
- Preserve existing behavior unless the card explicitly asks for behavior change.
- Run the narrowest relevant verification first, then the broader suite if practical.
- Record concrete evidence: commands, test result summaries, hashes, screenshots, or PR links.
- Do not reveal private chain-of-thought. Use a concise rationale, decision log, and evidence checklist instead.
- If blocked, write the blocker, attempted evidence, and the exact next question.

## Completion report
Write a short report with:
- what changed
- verification performed
- files touched
- whether a PR/commit was created
- next action or blocker

## Raw Card Excerpt
```text
# Codex Prompt — Phase 1 Deterministic Stabilization

```text
PREREQUISITE:
Phase 0 repository archaeology has been completed and reviewed.

TARGET:
Only the verified Financial Swing Analyst repository.

IMPLEMENT ONLY THE APPROVED PHASE 1 PATCH SET.

Required categories:
- deterministic lockfile
- Node/runtime engine constraints
- validated configuration
- no hard-coded PII fallback
- no mutable global browser options
- consolidated date/time utility
- isolated legacy harvester
- fake fixtures
- extraction/parser tests
- clean ignore rules
- safe startup/shutdown
- no Quantower dependency at startup
- execution disabled by default

Do not:
- expand scraping
- bypass Barchart controls
- begin ML
- place orders
- redesign the full UI
- delete unknown local files

For every changed file:
- state reason
- add/modify tests
- run typecheck/lint/test/build
- prove startup and clean shutdown
- prove no unrelated project touched

Return exact files, commands, outputs, remaining blockers, and rollback instructions.
```
```

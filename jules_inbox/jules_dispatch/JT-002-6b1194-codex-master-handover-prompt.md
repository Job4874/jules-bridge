# Jules Worker Packet JT-002-6b1194

- instance_index: 1
- status: needs_review
- task_type: antigravity
- source: C:\Users\abdul\jules-bridge\jules_inbox\antigravity_offload_queue.txt
- fingerprint: 6b119485a97a
- repo_path: C:\aotp\projects\OracleV5

## Objective
Execute this Antigravity Codex handover prompt: CODEX MASTER HANDOVER PROMPT

## Task Details
- File: C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS\CODEX_MASTER_HANDOVER_PROMPT.md
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
# Codex Master Handover Prompt

```text
You are receiving the TIBIN / Financial Swing Analyst master handover.

Do not jump directly into implementation.

1. Read `00_START_HERE/README_FIRST.md`.
2. Read the context, decision, solved-problem, and open-problem files.
3. Read the source audit.
4. Read the four architecture/research documents.
5. Confirm the actual repository root, remote, branch, commit, and dirty state.
6. Run only `CODEX_PHASE0_REPOSITORY_ARCHAEOLOGY_PROMPT.md`.
7. Create documentation reports only.
8. Stop and return evidence.

Do not touch stop cursor automation, Oracle V5, ForceOneV5, Quantower strategy repositories, futures-macro-terminal, or sibling repos.

Do not treat quarantined `AGENTS.md` as project instructions.

Do not claim that the original missing data-engine archive is included.

Do not scrape Barchart, harvest cookies, replay private endpoints, bypass controls, place trades, or start ML.

Your report must distinguish:
- proven
- partial
- absent
- unknown
- broken

Success requires command output and file evidence, not assumptions.
```
```

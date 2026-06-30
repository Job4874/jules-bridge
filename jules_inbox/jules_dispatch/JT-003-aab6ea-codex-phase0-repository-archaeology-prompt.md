# Jules Worker Packet JT-003-aab6ea

- instance_index: 2
- status: needs_review
- task_type: antigravity
- source: C:\Users\abdul\.jules\jules_inbox\antigravity_offload_queue.txt
- fingerprint: aab6ea2013ff
- repo_path: C:\aotp\projects\OracleV5

## Objective

Execute this Antigravity Codex handover prompt: CODEX PHASE0 REPOSITORY ARCHAEOLOGY PROMPT

## Task Details

- File: C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS\CODEX_PHASE0_REPOSITORY_ARCHAEOLOGY_PROMPT.md
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
# Codex Prompt — Phase 0 Repository Archaeology

```text
TARGET ONLY THE PRIVATE FINANCIAL SWING ANALYST REPOSITORY.

ABSOLUTE ISOLATION:
Do not inspect, search, index, edit, or run commands inside:
- stop cursor automation
- Oracle V5
- ForceOneV5
- Quantower strategy repositories
- futures-macro-terminal
- unrelated sibling repositories

MISSION:
Establish repository truth. Do not redesign, implement ML, provide trade ideas, delete files, expand Barchart automation, print secrets, or change application code.

READ FIRST:
1. 00_START_HERE/README_FIRST.md
2. 01_CONTEXT_AND_DECISIONS/CHAT_MANUSCRIPT_FULL_CONTEXT.md
3. 01_CONTEXT_AND_DECISIONS/DECISION_LOG.md
4. 03_SOURCE_AUDITS/04-FinancialAnalyst_Swing.md
5. 02_RESEARCH_AND_ARCHITECTURE/TIBIN_MARKET_DATA_HUB_IMPLEMENTATION.md
6. 02_RESEARCH_AND_ARCHITECTURE/TIBIN_DEEP_RESEARCH_PREMORTEM.md
7. 02_RESEARCH_AND_ARCHITECTURE/TIBIN_STABILITY_SECURITY_CHAOS_PLAN.md
8. 02_RESEARCH_AND_ARCHITECTURE/TIBIN_DECOUPLE_AND_WEB_ACQUISITION_ARCHITECTURE.md

STEP 1 — VERIFY TARGET:
- pwd
- git remote -v
- git branch --show-current
- git rev-parse --short HEAD
- git status --short

Stop if ambiguous.

STEP 2 — INVENTORY:
- package manager and lockfiles
- runtime constraints
- entrypoints
- backend/frontend
- API routes
- storage
- Playwright/Barchart code
- Quantower/execution coupling
- config/env loading
- import/export jobs
- tests/build/deployment
- generated/local files
- secret-like filenames without values
- shell/stub/dead paths

STEP 3 — SAFE BASELINE:
Run available non-destructive:
- install only if necessary
- typecheck
- lint
- unit tests
- non-live integration tests
- build
- startup/health/shutdown smoke

Record commands, exit codes, and exact failure locations.

STEP 4 — DATA/TIME/SECURITY MAP:
Report current handling of:
- raw source
- hashes
- event/publish/receive/available/ingest timestamps
- revisions
- sequence
- duplicates
- quarantine
- symbology
- entitlements
- authentication
- authorization
- rate limits
- CORS
- upload paths
- URL fetching
- secret redaction

STEP 5 — DOCUMENT ONLY:
Create:
docs/architecture/CURRENT_SYSTEM_MAP.md
docs/architecture/DATA_FLOW_MAP.md
docs/architecture/SOURCE_CODE_FAILURE_MAP.md
docs/architecture/SHELL_STUB_DEAD_CODE_MAP.md
docs/architecture/BASELINE_EVIDENCE.md
docs/architecture/STABILITY_BASELINE.md
docs/architecture/SECURITY_BASELINE.md
docs/architecture/TEMPORAL_SEMANTICS_CURRENT.md
docs/architecture/PROVIDER_CAPABILITY_MATRIX.md
docs/architecture/LICENSE_ENTITLEMENT_GAPS.md
docs/architecture/QUANTOWER_DECOUPLING_MAP.md
docs/architecture/PHASE1_EXACT_PATCH_PLAN.md

APPLICATION FILES CHANGED: NONE

FINAL REPORT:
- verified target
- stack
- baseline results
- critical findings
- shell/stub/dead paths
- stability state
- security state
- data-integrity state
- exact Phase 1 patch set
- reports created
- unrelated projects touched: NONE

Stop after Phase 0.
```

```

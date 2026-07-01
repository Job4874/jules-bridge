# Jules Worker Packet JT-001-59ae6d

- instance_index: 4
- status: unknown
- task_type: antigravity
- source: C:\Users\abdul\jules-bridge\jules_inbox\antigravity_offload_queue.txt
- fingerprint: 59ae6d4b9eb4
- repo_path: C:\aotp\projects\OracleV5

## Objective
Execute this Antigravity Codex handover prompt: CODEX DECOUPLE QUANTOWER AND BUILD API FOUNDATION

## Task Details
- File: C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS\CODEX_DECOUPLE_QUANTOWER_AND_BUILD_API_FOUNDATION.md
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
# Codex Directive — Disconnect Quantower and Establish the TIBIN API Boundary

```text
TARGET ONLY THE PRIVATE FINANCIAL SWING ANALYST REPOSITORY.

Do not touch stop cursor automation, Oracle V5, ForceOneV5, the macro terminal, or sibling projects.

READ FIRST:

1. TIBIN_DECOUPLE_AND_WEB_ACQUISITION_ARCHITECTURE.md
2. TIBIN_MARKET_DATA_HUB_IMPLEMENTATION.md
3. TIBIN_DEEP_RESEARCH_PREMORTEM.md
4. TIBIN_STABILITY_SECURITY_CHAOS_PLAN.md
5. the Phase 0 archaeology reports already produced

MISSION:

Implement only the execution-platform decoupling and API-boundary foundation.

Do not implement broad web scraping.
Do not automate Barchart.
Do not begin ML training.
Do not place trades.
Do not delete files before inventory and approval.

PART 1 — VERIFY CURRENT QUANTOWER COUPLING

Find and report:

- imports/references
- packages/DLLs
- environment variables
- startup dependencies
- routes
- UI controls
- order models
- connection services
- background jobs
- tests
- files named Quantower, Tower, execution, broker, order, trade, or bridge

Produce an exact dependency map.

PART 2 — INTRODUCE EXECUTION BOUNDARY

Create or adapt:

- ExecutionAdapter contract
- DisabledExecutionAdapter
- execution configuration validation
- explicit disabled status endpoint
- audit events for rejected execution attempts

Defaults:

EXECUTION_ENABLED=false
EXECUTION_ADAPTER=disabled
QUANTOWER_BRIDGE_ENABLED=false
ALLOW_LIVE_ORDERS=false
ALLOW_PAPER_ORDERS=false

When disabled:

- do not load Quantower libraries
- do not load execution credentials
- do not start bridge processes
- do not mount live order routes
- reject every execution call
- display intentional disconnected/research mode in UI

PART 3 — PROVE INDEPENDENCE

Prove:

- install succeeds without Quantower
- build succeeds without Quantower
- tests succeed without Quantower
- backend starts without Quantower
- frontend starts without Quantower
- data imports work
- analysis endpoints work
- execution status is DISABLED
- order submission is impossible

PART 4 — INTERNAL API FOUNDATION

Implement only the minimum secure foundation:

- application record
- API-key issue-once function/CLI
- cryptographically random key
- salted hash storage
- key prefix lookup
- scopes
- source entitlements
- expiry and revocation
- per-key rate limit
- audit log
- Authorization Bearer middleware
- one protected health/data proof endpoint
- no provider credential exposed to client

Do not put raw API keys in logs or database.

PART 5 — ACQUISITION POLICY SKELETON

Implement contracts only:

- AcquisitionRequest
- AcquisitionResult
- source policy registry
- URL validation
- public-host allowlist
- private/reserved IP blocking
- Barchart automated acquisition policy = BLOCKED
- no browser worker yet

PART 6 — TESTS

Add tests for:

- disabled adapter rejects orders
- no Quantower initialization when disabled
- execution secrets not required
- API key valid/invalid/revoked/expired
- scope denial
- source-entitlement denial
- rate limit
- no secret logging
- private URL/localhost URL blocked
- redirect to private address blocked
- Barchart automated acquisition blocked

RUN:

- typecheck
- lint
- unit tests
- integration tests
- build
- startup smoke
- protected endpoint smoke
- execution rejection smoke

FINAL RESPONSE:

QUANTOWER DECOUPLING AND API FOUNDATION REPORT

- repo path
- branch
- commit
- prior coupling found
- files changed
- execution adapter status
- Quantower loaded: YES/NO
- execution credentials loaded: YES/NO
- backend without Quantower: PASS/FAIL
- frontend without Quantower: PASS/FAIL
- imports without Quantower: PASS/FAIL
- analysis without Quantower: PASS/FAIL
- order rejection: PASS/FAIL
- API key tests: PASS/FAIL
- acquisition policy tests: PASS/FAIL
- typecheck/lint/test/build results
- remaining blockers
- unrelated projects touched: NONE

Stop after this phase.
```
```

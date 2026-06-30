# Jules Worker Packet JT-001-09a40f

- instance_index: 1
- status: ready_for_review
- task_type: code_health
- source: inline
- fingerprint: 09a40fb56d99
- repo_path: C:\Users\abdul\jules-bridge

## Objective
Complete exactly this Jules card: Code Health for modules/health_service.py; modules/chat_service.py; tests/test_health_deep.py; tests/test_chat_service.py; dashboard-ui/src/App.jsx if needed

## Task Details
- File: modules/health_service.py; modules/chat_service.py; tests/test_health_deep.py; tests/test_chat_service.py; dashboard-ui/src/App.jsx if needed
- Issue: (not provided)
- Language: Python / React
- Rationale: Abdul's deadline goal is a production-ready Jules Bridge dashboard with all functions truthfully working. The bridge must not claim provider readiness from weak evidence. Implement a minimal patch that aligns deep health, chat health, and dashboard-facing readiness. Prefer reusing shared provider probe logic over duplicate network checks. Preserve graceful offline chat behavior, redact secrets, and add tests for invalid provider keys, one-provider-ok, and keyless/offline modes. Do not edit `.env`, do not reveal secrets, do not perform unrelated refactors. Produce a concise completion report plus unified diff.

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
# Code Health Improvement Task
File: modules/health_service.py; modules/chat_service.py; tests/test_health_deep.py; tests/test_chat_service.py; dashboard-ui/src/App.jsx if needed
Issue: Live production readiness is contradictory. `/health/deep` reports OpenRouter pass because it probes the public `/models` endpoint, while `/chat/test` and `/chat` both fail real chat completion with OpenRouter 401 `User not found`. Gemini also returns invalid API key. Make provider readiness production-honest without changing or printing secrets.
Language: Python / React
Rationale: Abdul's deadline goal is a production-ready Jules Bridge dashboard with all functions truthfully working. The bridge must not claim provider readiness from weak evidence. Implement a minimal patch that aligns deep health, chat health, and dashboard-facing readiness. Prefer reusing shared provider probe logic over duplicate network checks. Preserve graceful offline chat behavior, redact secrets, and add tests for invalid provider keys, one-provider-ok, and keyless/offline modes. Do not edit `.env`, do not reveal secrets, do not perform unrelated refactors. Produce a concise completion report plus unified diff.
Ready for review
```

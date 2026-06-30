# Jules Worker Packet JT-001-a7d59b

- instance_index: 1
- status: ready_for_review
- task_type: code_health
- source: inline
- fingerprint: a7d59b0f623f
- repo_path: C:\Users\abdul\jules-bridge

## Objective
Complete exactly this Jules card: Make bridge chat production-ready by rotating OPENROUTER_API_KEYS and using the already-online VM worker as a truthful fallback when local Gemini/OpenRouter credentials fail

## Task Details
- File: modules/chat_service.py
- Issue: Make bridge chat production-ready by rotating OPENROUTER_API_KEYS and using the already-online VM worker as a truthful fallback when local Gemini/OpenRouter credentials fail
- Language: python
- Rationale: Current local /chat/test and /chat report local Gemini/OpenRouter credential failures, but /vm/status is online and a VM chat task completed successfully. The production bridge should remain truthful about local provider failures while still using the VM worker path as a bounded fallback for /chat and readiness.

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
Code Health Improvement Task
You are a production-focused Jules worker. Implement only the narrow provider-readiness self-heal described here. Do not refactor unrelated source. Do not print or persist raw secrets.

Task Details
File: modules/chat_service.py Issue: Make bridge chat production-ready by rotating OPENROUTER_API_KEYS and using the already-online VM worker as a truthful fallback when local Gemini/OpenRouter credentials fail

Language: python

Rationale: Current local /chat/test and /chat report local Gemini/OpenRouter credential failures, but /vm/status is online and a VM chat task completed successfully. The production bridge should remain truthful about local provider failures while still using the VM worker path as a bounded fallback for /chat and readiness.

Implementation requirements:
1. In modules/chat_service.py, support both OPENROUTER_API_KEY and comma-separated OPENROUTER_API_KEYS for provider checks and chat fallback. Try candidates in order, redact every candidate in error details, and never log/return raw keys.
2. Add a bounded VM chat fallback using modules.vm_relay when local Gemini/OpenRouter do not produce a response. It should enqueue task_type="chat" with a unique request marker, poll status briefly for the matching completed task, and return model_used like "vm/jules-worker" plus elapsed_ms. Use conservative timeouts suitable for HTTP routes.
3. Update test_chat_providers() so healthy is true if any real provider path works, including the VM chat fallback/probe, while preserving truthful provider entries for local gemini/openrouter failures.
4. Keep behavior offline-friendly and unit-testable by injecting env, request clients, clocks, and relay functions where practical.
5. Add or update focused tests for OpenRouter key rotation, secret redaction across plural keys, VM fallback success, VM timeout/failure, and /chat/test readiness semantics if route tests exist.
6. Do not edit generated dispatch state, screenshots, or unrelated dashboard files.

Verification expected from Jules:
- Run the focused pytest files you touched.
- Report files changed and exact test commands/results.
Ready for review
```

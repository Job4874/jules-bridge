# Jules Worker Packet JT-001-provider-external-readiness-audit

- instance_index: 1
- status: pending
- task_type: code_health
- source: codex-live-audit
- fingerprint: provider-external-readiness-audit-fa8e533
- repo_path: C:\Users\abdul\jules-bridge

## Objective

Find a real, secret-safe self-unblocking path for the remaining provider readiness blocker, or prove that the blocker is external and should stay as a release/draft condition.

## Current Live Evidence

- Branch/PR: `codex/jules-production-finish`, PR #64 draft, latest pushed head `fa8e533` (`fix: stabilize vm health polling`).
- Local bridge: `http://127.0.0.1:5000`, public LocalTunnel: `https://shaggy-kiwis-shout.loca.lt`.
- `/ping`, `/health`, `/dashboard/status` pass locally and publicly.
- `/dashboard/status`: `VM CHAT: OK`, cloud workers `1/1 ONLINE`, Gemini `ERROR`, OpenRouter `ERROR`.
- `/health/deep` now uses passive VM readiness and preserves provider `error_type`.
- `/chat/test`: Gemini returns `400 invalid_key`, OpenRouter returns `401 invalid_key`, VM worker returns `ok`.
- VM worker is online as OS Login user `atibin7_gmail_com`; source bootstrap now targets that user and preserves plural `OPENROUTER_API_KEYS`.
- Do not trust stale prior patches from sessions `2693363866417321141` or `3580112715401585773`; both were broad stale diffs that removed circuit-breaker wiring.

## Task Details

Files likely involved only if you find a real code/config fix:

- `modules/chat_service.py`
- `modules/vm_relay.py`
- `modules/health_service.py`
- `modules/dashboard_module.py`
- tests under `tests/`
- docs/handoff files only if reporting evidence

Required investigation:

1. Inspect current source at head `fa8e533`.
2. Search for any non-secret installed credential source, env alias, config mismatch, or provider routing bug that could explain Gemini/OpenRouter `invalid_key`.
3. Do not print, commit, upload, or paste raw secrets. Secret names, paths, presence, length, provider code, and redacted error class are allowed.
4. If a real fix exists without new credentials, implement the smallest current-head patch and tests.
5. If no real fix exists, do not make cosmetic changes. Write a concise completion report proving why the remaining blocker is external.

## Hard Constraints

- Do not edit `.env` or commit secrets.
- Do not mark Gemini/OpenRouter fixed unless live checks prove it.
- Do not remove `bridge.py` circuit-breaker wiring.
- Do not add backup files.
- Do not replay broad stale hunks.
- Do not change dashboard semantics to hide provider failures.

## Verification Requirements

If code changes:

- Run the narrow relevant tests first.
- Run full `python -m pytest tests/ -q`.
- Include live route evidence for `/chat/test`, `/health/deep`, `/dashboard/status`, and public tunnel if practical.

If no code changes:

- Include exact inspected files/surfaces.
- Include exact current blocker classes.
- State whether PR #64 should remain draft.

## Completion Report

Write a short report with:

- what changed, if anything
- verification performed
- files touched
- whether provider blockers remain
- whether a PR/commit was created
- next action or blocker

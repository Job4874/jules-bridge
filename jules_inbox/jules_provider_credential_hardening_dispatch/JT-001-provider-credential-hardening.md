# Jules Worker Packet JT-001-provider-credential-hardening

- instance_index: 1
- status: pending
- task_type: code_health
- source: codex-live-audit
- fingerprint: provider-credential-hardening
- repo_path: C:\Users\abdul\jules-bridge

## Objective
Harden provider readiness and OpenRouter fallback behavior without touching or exposing secrets.

## Current Live Evidence
- Branch/PR: `codex/jules-production-finish`, PR #64, current head `087c5daa45b926dc4f9f9d44cc1b3818f47a0be8`.
- Local bridge and dashboard are running; public tunnel `https://neat-oranges-wink.loca.lt/ping` returns `Jules Bridge Online`.
- `/chat`, `/chat/test`, `/health/deep`, and `/dashboard/status` currently prove VM fallback readiness.
- Local installed Gemini candidate returns `400 invalid key`.
- Local installed OpenRouter candidates return `401 user not found`.
- VM inherited Gemini key is present but returns `429 quota`.
- VM inherited OpenRouter key is present; the configured `google/gemma-3-27b-it:free` model is unavailable, and sampled free models currently return `429`.
- Secret Manager is unavailable/disabled for project `tibin-terminal-2026`.
- Redacted env-file search found no alternate plausible local keys.

## Task Details
Files likely involved:
- `modules/chat_service.py`
- `tests/test_chat_service.py`
- optionally dashboard/health tests only if needed

Implementation goals:
1. Preserve the existing bounded VM chat success/failure readiness behavior. Do not regress commit `087c5da`.
2. Classify provider failures more explicitly where possible:
   - invalid key / unauthorized
   - quota or rate limit
   - model unavailable
   - transient exception
3. For OpenRouter chat and health probes, avoid relying on exactly one hard-coded free model when OpenRouter reports a model is unavailable. Add a small ordered fallback list or discovery-backed helper if it can be done safely and testably.
4. Keep behavior secret-safe: never print, commit, upload, or paste raw keys.
5. Do not claim Gemini/OpenRouter are fixed unless live provider checks prove it. It is acceptable for the final report to say credentials/quota remain external blockers.

## Verification Requirements
- Run focused tests for chat provider routing.
- Run the broader relevant suite if practical.
- Include exact commands and summaries in the completion report.
- Leave a pullable diff for Codex review; do not commit.

## Completion Report
Write a short report with:
- what changed
- verification performed
- files touched
- whether any provider blockers remain
- whether a PR/commit was created

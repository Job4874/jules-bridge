# Jules Worker Packet JT-003-post-retry-production-readiness-audit

- instance_index: 1
- status: pending
- task_type: production_readiness
- source: codex-post-retry-current-head-audit
- repo_path: C:\Users\abdul\jules-bridge
- branch: codex/jules-production-finish
- head: 45ff2f56e6c2d49f3e1e63eb470d6d9940427f60
- generated_at_local: 2026-06-30T08:07:00-06:00

## Noninteractive Operating Rule

Do not stop for plan approval. Do not ask the operator to approve a plan. Inspect
current head and live evidence. Implement only if you find a real source bug
that can be fixed without new secrets. If the remaining blocker is external
provider credentials/quota/capacity, write a clear report and leave code
unchanged.

## Why This Packet Exists

Prior current-head refresh session `10937231877503281057` is a stale blank-status
row and was launched against an older head. Do not pull it unless a fresh remote
list later reports that exact session as `Completed`.

This JT-003 packet is the current audit target after Codex integrated and pushed
direct VM retry hardening.

## Current Live Evidence

- PR #64 is open draft at head `45ff2f56e6c2d49f3e1e63eb470d6d9940427f60`.
- Local bridge is live: `http://127.0.0.1:5000`.
- Dashboard preview is live: `http://127.0.0.1:5173`.
- Public LocalTunnel is live:
  `https://shaggy-kiwis-shout.loca.lt`.
- Public `/ping`, `/health`, and `/dashboard/status` return HTTP 200.
- GCP cloud worker is online/reachable and dashboard reports `cloud.online=1`.
- Direct `/chat` VM fallback attempts were increased from `2` to `4` in
  `modules/chat_service.py`.
- Regression coverage exists in `tests/test_chat_service.py` for two transient
  VM `No LLM available` results followed by a successful VM response.
- Focused test passed: `tests/test_chat_service.py` -> `33 passed`.
- Full suite passed: `python -m pytest tests/ -q` -> `438 passed`.
- Bridge restarted from source and is live on PID `41428`.
- Post-retry direct `/chat` stability sample returned
  `model_used=vm/jules-worker` with `OK` on 5/5 attempts.

## Current Provider Truth

- Local Gemini still reports invalid-key.
- Local OpenRouter still reports invalid-key.
- VM fallback is currently good enough for the 5/5 direct chat sample, but VM
  side provider quota/free-model capacity has previously flipped to
  `No LLM available`.
- `/chat/test` can be `healthy=true` through VM fallback while local providers
  remain red. Do not greenwash Gemini/OpenRouter.
- PR #64 should remain draft unless local credential failures are fixed or
  explicitly accepted as non-blocking.

## Scope

Audit current head for any remaining production-readiness bug that is fixable
without secrets. Candidate checks:

1. Confirm direct `/chat` retry behavior is bounded, tested, and does not hide
   final VM provider failure.
2. Confirm `/dashboard/status`, `/chat/test`, `/health/deep`, and direct
   `/chat` semantics remain honest when Gemini/OpenRouter are invalid but VM
   fallback succeeds.
3. Confirm the dashboard should still show Gemini/OpenRouter red and VM fallback
   status honestly.
4. Confirm there is no current-head code fix for the local invalid credentials
   or upstream VM provider quota.

## Hard Constraints

- Do not edit `.env`, print secrets, commit/upload credentials, or expose token
  values.
- Do not replay stale sessions `2693363866417321141`, `3580112715401585773`,
  `14998673751325827002`, `4009579503888711152`, or `10937231877503281057`
  unless a fresh list shows that exact session is `Completed` and Codex is
  explicitly pulling only that session.
- Do not remove bridge circuit-breaker wiring.
- Do not add backup or shadow source files.
- Do not hide provider failures or mark them green without live proof.
- Keep any patch minimal and current-head only.

## Verification If You Patch

- Run focused tests for changed modules.
- Run full `python -m pytest tests/ -q`.
- Verify local `/dashboard/status`, `/health/deep`, `/chat/test`, `/chat`, and
  public `/dashboard/status`.

## Completion Report Required

Return a concise report with:

- current-head files inspected
- whether code changed
- files touched
- verification performed
- provider blocker status
- whether PR #64 should remain draft
- next smallest action

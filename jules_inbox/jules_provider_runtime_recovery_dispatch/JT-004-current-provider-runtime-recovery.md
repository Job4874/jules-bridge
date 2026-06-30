# Jules Worker Packet JT-004-current-provider-runtime-recovery

- instance_index: 1
- status: pending
- task_type: production_readiness
- source: codex-current-provider-runtime-recovery
- repo_path: C:\Users\abdul\jules-bridge
- branch: codex/jules-production-finish
- head: 64d5357498b83658ca3217355175be0ac7825b97
- generated_at_local: 2026-06-30T09:22:50-06:00

## Noninteractive Operating Rule

Do not stop for plan approval. Inspect the current branch and the evidence files
listed below. Implement only if you find a real source/runtime bug that can be
fixed without secrets. If the remaining blocker is external provider
credentials, quota, or capacity, return a clear report and leave source code
unchanged.

## Why This Packet Exists

The older active session `14369052129679399317` was launched from JT-003 against
an older head and older provider evidence. A fresh remote list still reports it
as `Planning`. Do not replay or rely on older stale sessions.

This JT-004 packet reflects the current PR head and the newest degraded provider
runtime evidence. It should determine whether there is any current-head
production-readiness fix left that does not require new credentials.

## Current Evidence

- PR #64 is open draft at head
  `64d5357498b83658ca3217355175be0ac7825b97`.
- Bridge and dashboard are booted:
  - local bridge `http://127.0.0.1:5000`
  - dashboard preview `http://127.0.0.1:5173`
  - public tunnel `https://shaggy-kiwis-shout.loca.lt`
- Rendered dashboard evidence:
  `jules_inbox/jules_dashboard_realtime_enhancement/evidence/dashboard-live-recheck-20260630T085659.json`
- Provider shape evidence:
  `jules_inbox/jules_provider_external_blocker_dispatch/provider-shape-audit-20260630T091217.json`
- Current degraded provider runtime evidence:
  `jules_inbox/jules_provider_external_blocker_dispatch/provider-runtime-degraded-20260630T091752.json`

## Current Provider Truth

- Local `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, and `OPENROUTER_API_KEYS` are
  present but fail expected provider token shape checks.
- VM worker has an OpenRouter-shaped `OPENROUTER_API_KEY`, a non-Gemini-shaped
  `GEMINI_API_KEY`, and no plural `OPENROUTER_API_KEYS`.
- Latest degraded runtime evidence showed:
  - `/dashboard/status?bypass_cache=true` responding with cloud `1/1`
  - `/health/deep` status `ok` but Gemini/OpenRouter `invalid_key`
  - GET `/chat/test` `healthy: false`
  - direct `/chat` `model_used=none`
  - VM recent tasks all reporting `No LLM available`
- A later Codex live check saw VM fallback briefly return `OK` again, confirming
  intermittent provider capacity rather than dead bridge/VM wiring.

## Scope

Audit the current head for any remaining production-readiness issue that can be
fixed without new secrets.

Candidate checks:

1. Confirm dashboard, `/dashboard/status`, `/health/deep`, `/chat/test`, and
   direct `/chat` semantics honestly distinguish local provider invalid-key
   failures from VM fallback success/failure.
2. Confirm direct `/chat` bounded VM retries do not hide final VM provider
   exhaustion.
3. Confirm whether any code or runtime config bug prevents the existing
   OpenRouter-shaped VM key from being used reliably.
4. Confirm whether the current production blocker is strictly external
   credential/quota/capacity.

## Hard Constraints

- Do not edit `.env`, print secrets, commit/upload credentials, or expose token
  values.
- Do not add fallback keys, fake provider responses, or green provider failures.
- Do not remove bridge circuit-breaker wiring.
- Do not add backup/shadow source files.
- Do not replay stale sessions:
  `2693363866417321141`, `3580112715401585773`, `14998673751325827002`,
  `4009579503888711152`, `10937231877503281057`, or `14369052129679399317`.
- Keep any patch minimal and current-head only.

## Verification If You Patch

- Run focused tests for changed modules.
- Run full `python -m pytest tests/ -q`.
- Verify local `/dashboard/status?bypass_cache=true`, `/health/deep`,
  `/chat/test`, `/chat`, `/vm/status`, and public `/dashboard/status`.

## Completion Report Required

Return:

- files inspected
- whether code changed
- files touched
- tests/verification performed
- whether the provider blocker is code-fixable or external
- whether PR #64 must remain draft
- next smallest action

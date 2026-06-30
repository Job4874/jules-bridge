# Jules Worker Packet JT-002-current-head-production-readiness-refresh

- instance_index: 1
- status: pending
- task_type: production_readiness
- source: codex-current-head-refresh
- repo_path: C:\Users\abdul\jules-bridge
- branch: codex/jules-production-finish
- head: 6780117cd7154f7927cf773a23d0e14714b53e7a
- generated_at_local: 2026-06-30T07:31:56-06:00

## Noninteractive Operating Rule

Do not stop for plan approval and do not ask the operator to approve a plan.
Proceed with research, then implement only a narrow current-head fix if live
evidence proves one exists. If the remaining issue is external credentials,
quota, provider capacity, or tunnel/service availability, write the completion
report and make no cosmetic source changes.

## Why This Refresh Exists

The prior current-head session `4009579503888711152` is not Completed and now
appears in the Jules session list with blank status and last active older than
the repo's stale-unknown threshold. Do not pull that session unless a fresh
remote list says it is Completed. Treat this packet as the current noninteractive
production-readiness refresh.

## Current Live Evidence

- Local bridge is live: `http://127.0.0.1:5000`.
- Dashboard preview is live: `http://127.0.0.1:5173`.
- Public LocalTunnel is live again:
  `https://shaggy-kiwis-shout.loca.lt`.
- Local and public `/ping`, `/health`, and `/dashboard/status` return HTTP 200.
- The public tunnel had gone 503 until Codex relaunched localtunnel with
  `--host https://loca.lt --port 5000 --subdomain shaggy-kiwis-shout
  --local-host 127.0.0.1`; after that, public `/ping`, `/health`, and
  `/dashboard/status` returned HTTP 200.
- GCP worker `jules-offload-worker` is online/reachable at `34.132.193.73`.
- `GET /chat/test` currently reports `healthy=false`:
  local Gemini `error_type=invalid_key`, local OpenRouter
  `error_type=invalid_key`, and VM worker `status=error`.
- A direct `POST /chat` probe intermittently succeeds through
  `model_used=vm/jules-worker` with response `OK`, but this is not stable
  enough to mark production clean.
- `/vm/status` reports the VM online and provider env flags present, but recent
  VM task output says no LLM is available because Gemini is rate-limited and
  OpenRouter free models failed.
- Git worktree was clean at current head `6780117cd7154f7927cf773a23d0e14714b53e7a`
  before this packet was generated.

## Current Provider Truth

- Local Gemini is invalid-key.
- Local OpenRouter is invalid-key.
- VM fallback can answer intermittently, but `/chat/test` still marks VM worker
  unhealthy and provider exhaustion/rate limit remains visible.
- Therefore production readiness is not proven until chat/provider readiness is
  stable or the product explicitly classifies the provider outage as a draft
  external blocker without greenwashing it.

## Scope

Investigate only current-head production-readiness blockers that can be solved
without new secrets. If there is a real current-head bug, produce the smallest
patch. If the blocker is external credentials/quota/capacity, write a clear
report and leave code unchanged.

Candidate current-head checks:

1. Verify `/chat/test`, `/chat`, `/health/deep`, `/dashboard/status`, and
   `/vm/status` semantics agree and do not claim green production readiness when
   providers are actually unavailable.
2. Confirm whether `/chat` and `/chat/test` exposure is intentional for this
   bridge model or a production exposure bug. Do not break dashboard/dev probes.
3. Confirm `keyless_mode` and provider classification correctly handle both
   `OPENROUTER_API_KEY` and `OPENROUTER_API_KEYS` without printing secrets.
4. Confirm VM readiness reporting distinguishes worker-online from LLM-ready.
5. Confirm dashboard tunnel state follows live `tunnel_url` truth and does not
   claim the tunnel active from stale data.

## Hard Constraints

- Do not edit `.env`, print secrets, commit/upload credentials, or expose token
  values.
- Do not replay stale sessions `2693363866417321141`, `3580112715401585773`,
  `14998673751325827002`, or `4009579503888711152` unless a fresh list shows the
  exact session is Completed and you are explicitly pulling that one.
- Do not remove bridge circuit-breaker wiring.
- Do not add backup or shadow source files.
- Do not hide provider failures or mark them green without live proof.
- Keep any patch minimal and current-head only.

## Verification If You Patch

- Run focused tests for changed modules.
- Run full `python -m pytest tests/ -q`.
- Verify local `/dashboard/status`, `/health/deep`, `/chat/test`, `/chat`, and
  public `/dashboard/status`.
- If dashboard UI changes, verify browser rendering.

## Completion Report Required

Return a concise report with:

- current-head files inspected
- whether code changed
- files touched
- verification performed
- provider blocker status
- whether PR #64 should remain draft
- next smallest action

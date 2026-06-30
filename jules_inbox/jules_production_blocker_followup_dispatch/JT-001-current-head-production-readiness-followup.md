# Jules Worker Packet JT-001-current-head-production-readiness-followup

- instance_index: 1
- status: pending
- task_type: production_readiness
- source: codex-current-head-audit
- repo_path: C:\Users\abdul\jules-bridge
- branch: codex/jules-production-finish
- head: fa8e533723c2a131cd83d4f409508a164ad6bde8

## Noninteractive Operating Rule

Do not stop for plan approval or ask the operator to approve a plan. The current
Jules CLI cannot approve `Awaiting User` sessions. Proceed with research, then
implement only a narrow current-head fix if evidence proves one exists. If the
remaining issue is external credentials/quota/capacity, write a completion
report and make no cosmetic source changes.

## Current Live Evidence

- Local bridge is live: `http://127.0.0.1:5000`.
- Dashboard is live: `http://127.0.0.1:5173`.
- Public LocalTunnel is live:
  `https://shaggy-kiwis-shout.loca.lt`.
- Local and public `/ping`, `/health`, and `/dashboard/status` pass.
- Browser dashboard renders `JULES NEXUS`, `TUNNEL: ACTIVE`,
  `GEMINI: ERROR`, `OPENROUTER: ERROR`, `CLOUD WORKERS`,
  `1/1 ONLINE`, and `JULES ONLINE`.
- GCP worker `jules-offload-worker` is online/reachable at
  `34.132.193.73`.
- Full test suite passed during the Codex handoff pass:
  `434 passed`, evidence hash
  `abe202689ecb0a56513e142eeb353a066d76a4528d41a724d8ac041d931d263a`.

## Current Provider Truth

- Local Gemini reports `invalid_key`.
- Local OpenRouter reports `invalid_key`.
- VM worker is online, but latest `/chat/test` reports VM fallback provider
  unavailable: worker reported no LLM available.
- A direct `/chat` call succeeded once through `vm/jules-worker` with `OK`,
  but that success is not stable enough to mark production-clean.

This means the bridge, dashboard, tunnel, and VM process are alive. The remaining
release blocker is provider readiness unless you find a genuine current-head
logic/config bug.

## Scope

Investigate and fix only current-head production-readiness blockers that can be
solved in source or generated operational artifacts without new secrets.

Candidate current-head issues to inspect:

1. `/chat` and `/chat/test` are public/auth-exempt. Determine whether this is
   intended for dashboard/dev convenience or a production exposure bug. Do not
   break the dashboard.
2. `/health/deep` top-level `status` can remain `ok` while provider checks fail.
   Determine whether this is intentional degraded readiness or a misleading
   production signal.
3. `keyless_mode` may ignore plural `OPENROUTER_API_KEYS`.
4. VM readiness in `/health/deep` is passive by design; ensure dashboard and
   health semantics do not claim VM LLM readiness when only worker-online is
   known.
5. Dashboard fleet state may read root `JULES_*.json` while current dispatch
   state lives under `jules_inbox/...`; fix only if this affects the production
   dashboard truth and can be done narrowly.

## Hard Constraints

- Do not edit `.env`, print secrets, or commit/upload raw credentials.
- Do not replay stale sessions `2693363866417321141`,
  `3580112715401585773`, or `14998673751325827002`.
- Do not remove bridge circuit-breaker wiring.
- Do not add backup/shadow source files.
- Do not hide provider failures or mark them green without live proof.
- Do not broaden the patch beyond the smallest real production-readiness fix.

## Verification If You Patch

- Run focused tests for changed modules.
- Run full `python -m pytest tests/ -q`.
- Verify local `/dashboard/status`, `/health/deep`, `/chat/test`, and public
  `/dashboard/status` if runtime access is available.
- Report exact files touched and whether PR #64 should remain draft.

## Completion Report Required

Return a concise report with:

- current-head files inspected
- whether code changed
- files touched
- verification performed
- provider blocker status
- whether PR #64 should remain draft
- next smallest action

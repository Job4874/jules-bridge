# Genesis Build Handoff Packet

- generated_at_local: 2026-06-30 06:34 America/Denver
- repo: C:\Users\abdul\jules-bridge
- branch: codex/jules-production-finish
- source_code_changed: no
- intentional_new_artifacts: jules_inbox/genesis_indexing_agents/
- live_bridge: http://127.0.0.1:5000
- live_dashboard: http://127.0.0.1:5173
- public_tunnel_checked: https://shaggy-kiwis-shout.loca.lt

## Scope

Implement and boot the Genesis indexing handoff without touching application
source. The generated packet tree creates ten custom read-only codebase
indexing slices using the existing AKC context-subagent machinery.

## Ten Genesis Indexing Agents

All ten generated packet sets are ready, have readable sources, and are under
budget. Each lives under `jules_inbox/genesis_indexing_agents/<agent-id>/`.

| id | slice |
| --- | --- |
| AG-01-bridge-api | Bridge API, route manifest, auth, key contracts |
| AG-02-core-modules | Deep module export surface and source boundaries |
| AG-03-jules-orchestration | Jules dispatch, launch, pull, COT, watch, fleet state |
| AG-04-akc-skills | AKC checkpoint, subagent packet builder, local skills |
| AG-05-dashboard-ui | React dashboard UI, polling, cloud/provider panels |
| AG-06-health-providers | Chat provider readiness and deep health |
| AG-07-vm-cloud-runtime | VM relay, cloud worker, offload, tunnel runtime |
| AG-08-tests-evidence | Test suite, evidence recording, verification bundle |
| AG-09-install-boot | Requirements, launch scripts, Node/Python runtime wiring |
| AG-10-docs-handoff-pr | Docs, memory, handoff, PR readiness |

Summary artifact:
`jules_inbox/genesis_indexing_agents/GENESIS_INDEXING_AGENTS_SUMMARY.json`

## Installed And Verified

- Python runtime in use by the live bridge:
  `C:\Users\abdul\AppData\Local\Programs\Python\Python312\python.exe`
- Python dependencies import cleanly from that runtime:
  Flask, flask-cors, requests, pyngrok, google-cloud-aiplatform.
- Dashboard dependencies already exist at `dashboard-ui/node_modules`.
- VS Code VRL extension dependencies already exist at `vscode-vrl/node_modules`.
- Bundled Codex Node runtime is required for package scripts in this shell:
  `C:\Users\abdul\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin`
- Bare `node` is not globally on PATH here; scoped PATH wiring is required.

## Build And Test Evidence

- Dashboard lint passed with scoped bundled Node PATH:
  `pnpm run lint`
- Dashboard production build passed with scoped bundled Node PATH:
  `pnpm run build`
- VRL extension compile passed with scoped bundled Node PATH:
  `pnpm run compile`
- Focused Python slice passed:
  `133 passed in 2.00s`
- Full Python suite passed:
  `434 passed in 15.58s`
- Retrospective evidence recorded:
  `sha256:abe202689ecb0a56513e142eeb353a066d76a4528d41a724d8ac041d931d263a`

## Live Boot Evidence

- Port 5000: bridge live on Python PID 37788.
- Port 5173: dashboard Vite server live on Node PID 39320.
- Local routes passed:
  `/ping`, `/health`, `/akc/readiness`, `/tentacles`, `/dashboard/status`,
  `/health/deep`, `/chat/test`, `/vm/status`.
- Public tunnel passed:
  `/ping`, `/health`, `/dashboard/status` on
  `https://shaggy-kiwis-shout.loca.lt`.
- Browser proof rendered:
  `JULES NEXUS`, `TUNNEL: ACTIVE`, `GEMINI: ERROR`,
  `OPENROUTER: ERROR`, `VM CHAT: ERROR`, `CLOUD WORKERS`,
  `1/1 ONLINE`, `jules-offload-worker`, `34.132.193.73`,
  and `JULES ONLINE`.

## Provider Truth

The system is booted, but provider readiness is not production-clean.

- Local Gemini returns `invalid_key`.
- Local OpenRouter returns `invalid_key`.
- GCP worker is online and reachable.
- Actual `/chat` succeeded once during this pass through `vm/jules-worker`
  with response `OK`.
- Latest `/chat/test` then reported VM worker provider unavailable:
  worker online but no LLM available.

This is an external provider credential/quota/capacity blocker, not a dead
bridge, dashboard, tunnel, or VM process.

## Jules Session Truth

Live `/jules/sessions` with cache bypass showed session
`14998673751325827002` as `Awaiting User`, not completed. It was not pulled or
applied. Stale completed sessions `3580112715401585773` and
`2693363866417321141` remain known stale-risk sessions and should not be
applied blindly.

Follow-up launched after that blocker:

- packet:
  `jules_inbox/jules_production_blocker_followup_dispatch/JT-001-current-head-production-readiness-followup.md`
- new session: `4009579503888711152`
- current observed status: `Planning`
- launch state:
  `jules_inbox/jules_production_blocker_followup_dispatch/JULES_LAUNCH_STATE.json`
- later observed status: active/fresh in remote list, not `Completed`
- heartbeat monitor:
  `jules-bridge-production-follow-up-monitor`

Only pull `4009579503888711152` after it reports `Completed`. Do not pull stale
session ids that appear in older packets or warning text.

If `jules remote list --session` fails due CLI self-update or DNS, use the
direct executable path:
`C:\Users\abdul\AppData\Local\Temp\jules_tmp\jules.exe`.

## Dirty-State Discipline

Preserved pre-existing dirty runtime state:

- modified `jules_inbox/jules_dispatch/*` state files
- modified `scratch/jules-worker-agent.py`
- untracked prior dispatch folders

New intentional untracked artifacts from this pass:

- `jules_inbox/genesis_indexing_agents/`
- `jules_inbox/jules_production_blocker_followup_dispatch/`
- this handoff packet

## Next Operator-Safe Action

Do not mark PR #64 production-ready unless one of these happens:

1. valid local Gemini/OpenRouter credentials are installed and verified;
2. VM provider quota/capacity recovers and `/chat/test` reports VM OK;
3. the operator explicitly accepts current provider failures as non-blocking.

Until then, the server/dashboard/install/build side is booted and verified,
but provider readiness remains the release blocker.

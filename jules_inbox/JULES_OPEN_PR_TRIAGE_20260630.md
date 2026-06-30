# Jules Open PR Triage - 2026-06-30

## Current Base

- `master` includes PR #78, PR #65, and PR #66.
- Local verification after PR #78: `python -m pytest tests/ -q` passed 422 tests, and `npm.cmd run build` passed.
- Local verification after PR #65 and PR #66: `python -m pytest tests/ -q` passed 424 tests.
- Private inventory remains local-only. Do not put account-wide private repo names in public PR text.

## Queue Summary

Open draft PRs after PR #78, #65, and #66 merge:

| PR | Merge state | Files | Add/Del | Main area | Action |
| --- | --- | ---: | ---: | --- | --- |
| #77 | DIRTY | 2 | +45/-0 | VM manager scale entry point | Rebase onto `master`; likely overlaps #70 |
| #76 | DIRTY | 9 | +66/-58 | production/security hardening | Rebase and split by domain before merge |
| #75 | DIRTY | 2 | +109/-1 | dashboard cloud worker visibility | Rebase onto new dashboard repo-context panel |
| #74 | DIRTY | 2 | +230/-34 | production chat fallback | Rebase with #69/#71/#73 before merge |
| #73 | DIRTY | 4 | +179/-81 | honest provider readiness | Rebase with chat/health stack |
| #72 | DIRTY | 2 | +45/-4 | VM worker readiness dashboard | Rebase with #75 dashboard work |
| #71 | DIRTY | 5 | +122/-58 | VM/chat/health readiness | Rebase with #69/#73/#74 |
| #70 | DIRTY | 2 | +21/-0 | VM manager import/scale entry | Rebase; likely duplicate family with #77 |
| #69 | DIRTY | 4 | +456/-66 | provider credential hardening | Rebase with chat/health stack |
| #68 | DIRTY | 9 | +122/-51 | health/chat/dashboard readiness | Rebase with #69/#71/#73/#74 |
| #67 | DIRTY | 30 | +1837/-226 | provider classification/dashboard | Rebase or supersede with narrower PRs |
| #64 | DIRTY | 193 | +16794/-1490 | broad production readiness | Treat as umbrella/reference, not direct merge until split |

## Exact Merge Conflict Matrix

Source: `git merge-tree origin/master origin/<headRefName>` on 2026-06-30. No PR branch was checked out or merged during this scan.

| PR | Conflict files from current `origin/master` | Collision note |
| --- | --- | --- |
| #77 | `modules/vm_manager.py` | VM contract overlaps #70 |
| #76 | `bridge.py`; `modules/shell_executor.py`; `modules/vm_manager.py` | broad production/security branch crosses bridge, shell execution, and VM contracts |
| #75 | `dashboard-ui/src/App.jsx` | dashboard worker visibility must rebase over repo-context status panel |
| #74 | `modules/chat_service.py` | chat fallback work overlaps provider readiness stack |
| #73 | `modules/chat_service.py` | provider probe contract overlaps chat fallback stack |
| #72 | `dashboard-ui/src/App.jsx` | dashboard VM worker readiness overlaps #75 and repo-context panel |
| #71 | `bridge.py`; `modules/dashboard_module.py` | health/readiness contract crosses bridge route and dashboard module |
| #70 | `modules/vm_manager.py` | duplicate VM scale entry family with #77 |
| #69 | `modules/chat_service.py`; `modules/circuit_breaker.py` | provider hardening must pick canonical chat/circuit-breaker semantics |
| #68 | `bridge.py`; `dashboard-ui/src/App.jsx` | health/chat readiness crosses bridge API and dashboard display |
| #67 | `.env.example`; `bridge.py`; `context/06_progress_tracker.md`; `dashboard-ui/src/App.jsx`; `jules_inbox/JULES_RESPONSE.md`; `jules_inbox/TUNNEL_HEALTH.json`; `memory/general.md`; `memory/test_evidence.json`; `modules/chat_service.py`; `modules/dashboard_module.py`; `modules/jules_orchestrator.py`; `modules/retrospective_module.py`; `modules/shell_executor.py`; `modules/vm_manager.py`; `tests/test_dashboard_module.py` | too broad for one safe merge; split by contract |
| #64 | `.env.example`; `bridge.py`; `context/06_progress_tracker.md`; `dashboard-ui/src/App.jsx`; `dashboard-ui/src/index.css`; `implementation_plan.md`; `jules_inbox/jules_dispatch/JULES_COT_LEDGER.json`; `jules_inbox/jules_dispatch/JULES_COT_LEDGER.md`; `jules_inbox/jules_dispatch/JULES_FLEET_STATE.json`; `jules_inbox/jules_dispatch/JULES_LAUNCH_STATE.json`; `jules_inbox/jules_dispatch/JULES_PREFLIGHT.json`; `jules_inbox/JULES_RESPONSE.md`; `jules_inbox/TUNNEL_HEALTH.json`; `Launch-Dashboard.ps1`; `memory/general.md`; `memory/test_evidence.json`; `modules/chat_service.py`; `modules/dashboard_module.py`; `modules/jules_api.py`; `modules/jules_orchestrator.py`; `modules/retrospective_module.py`; `modules/shell_executor.py`; `modules/vm_manager.py`; `Open-Dashboard.cmd`; `start.py`; `tests/test_dashboard_cache.py`; `tests/test_dashboard_module.py`; `tests/test_jules_api.py`; `tests/test_tunnel_watchdog.py` | umbrella/reference branch only until split into reviewable PRs |

## Merged During Triage

| PR | Result | Verification |
| --- | --- | --- |
| #65 | Merged into `master` at `97eff99` | Simulated merge on current `origin/master`: `tests/test_oracle_session.py` passed 13 tests; full `python -m pytest tests/ -q` passed 424 tests |
| #66 | Merged into `master` at `b085201` | Simulated merge after #65: `tests/test_tunnel_watchdog.py` passed 3 tests; full `python -m pytest tests/ -q` passed 424 tests |

## Dependency Families

### Dashboard Family

- #75: dashboard cloud worker visibility
- #72: VM worker readiness in dashboard
- #67/#68: dashboard pieces mixed with provider/health work
- New base from #78 adds `repo_context` into `/dashboard/status` and UI. Dashboard PRs must preserve the compact privacy rule: no repo sample names, full paths, env key lists, or private inventory in unauthenticated dashboard status.

### Chat / Provider / Health Family

- #69, #71, #73, #74, #68, #67 all touch `modules/chat_service.py`, `modules/health_service.py`, dashboard status, or health tests.
- Do not merge these independently without deciding the canonical provider readiness contract.
- Preserve the current no-key behavior from `master`: missing Gemini/OpenRouter keys are not healthy provider success.

### VM / Compute Family

- #70 and #77 both target `modules/vm_manager.py` scale/compute entry points.
- #72/#75 surface worker visibility in dashboard.
- Merge order should be module contract first, then dashboard display.

### Broad Production Umbrella

- #64 is too broad to merge directly while dirty: 193 files, generated evidence, dispatcher state, UI, scripts, modules, and memory files.
- Use it as source material for split PRs, not as the merge unit.

## Jules Rules For Next Pass

1. Rebase dirty PR branches on current `master` after PR #78.
2. Resolve by family, not by timestamp:
   - VM contract
   - chat/provider/health contract
   - dashboard display
   - docs/evidence
3. Keep draft PRs draft until each has:
   - exact files reviewed
   - focused tests passing
   - full `python -m pytest tests/ -q` passing when shared modules are touched
   - `npm.cmd run build` passing when dashboard files are touched
4. Use repo context guard before dispatching more workers; do not reuse ports, server nodes, local dependencies, or project extensions across repos without operator approval.
5. Keep math/analysis capability work tied to its owning repo/module and evidence-backed fixtures.
6. Remaining open PRs are all `DIRTY` as of the post-merge recheck; do not mark them ready until they are rebased and retested on current `master`.

## GitHub Comments Sent

Coordinator rebase/split comments were posted on all remaining dirty draft PRs:

- VM family: #70, #77
- Dashboard family: #72, #75
- Chat/provider/health family: #68, #69, #71, #73, #74
- Production/security hardening: #76
- Provider/dashboard mixed source branch: #67
- Broad umbrella/reference branch: #64

The first comment pass included a literal `$master` placeholder from PowerShell escaping. Follow-up correction comments were posted on each PR with the actual current master ref: `dc089f5`. The instructions otherwise stand.

## Exact Conflict Comments Sent

After the conflict matrix was added, per-PR coordinator comments were posted from current master `9f482b9`. Each comment includes the exact `git merge-tree` conflict files and the family-specific Jules next action.

| PR | Comment |
| --- | --- |
| #77 | https://github.com/Job4874/jules-bridge/pull/77#issuecomment-4847783627 |
| #76 | https://github.com/Job4874/jules-bridge/pull/76#issuecomment-4847783789 |
| #75 | https://github.com/Job4874/jules-bridge/pull/75#issuecomment-4847783921 |
| #74 | https://github.com/Job4874/jules-bridge/pull/74#issuecomment-4847784043 |
| #73 | https://github.com/Job4874/jules-bridge/pull/73#issuecomment-4847784279 |
| #72 | https://github.com/Job4874/jules-bridge/pull/72#issuecomment-4847784395 |
| #71 | https://github.com/Job4874/jules-bridge/pull/71#issuecomment-4847784515 |
| #70 | https://github.com/Job4874/jules-bridge/pull/70#issuecomment-4847784640 |
| #69 | https://github.com/Job4874/jules-bridge/pull/69#issuecomment-4847784889 |
| #68 | https://github.com/Job4874/jules-bridge/pull/68#issuecomment-4847785043 |
| #67 | https://github.com/Job4874/jules-bridge/pull/67#issuecomment-4847785143 |
| #64 | https://github.com/Job4874/jules-bridge/pull/64#issuecomment-4847785264 |

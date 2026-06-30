# Jules Open PR Triage - 2026-06-30

## Current Base

- `master` includes PR #78: repo context guard dashboard connection.
- Local verification after merge: `python -m pytest tests/ -q` passed 422 tests, and `npm.cmd run build` passed.
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

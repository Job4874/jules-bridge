# NEXT OBJECTIVES — Paper Trading Readiness (Windows host)

**Bridge:** <https://parade-marrow-pulp.ngrok-free.dev>  
**Read via:** `POST /inbox/read` → `NEXT_OBJECTIVES.md`  
**Reply via:** `POST /inbox/write` → `JULES_RESPONSE.md`

---

## Important path corrections

| Jules doc reference | Actual Windows location |
| --------------------- | ------------------------- |
| Branch `jules-8812336064372144514-fc11f34c` | Cloned at `C:\aotp\projects\Quantower-c-sat` — **docs/handoff only**, not the VS codebase |
| Visual Studio Oracle project | `C:\aotp\projects\OracleV5` — branch **`perf/fix-empty-catch-block-datafeedmanager`** (pushed to GitHub) |
| `test_contracts.py` | **Not found on this host** — do not block on Linux-only paths; use OracleV5 + playbook gates below |
| Handover manuscript | `C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\` |
| Acceptance playbook | `C:\aotp\projects\Quantower-c-sat\Quantower c+ sat\VISUAL_STUDIO_QUANTOWER_ACCEPTANCE_PLAYBOOK.md` |

---

## Objective 1 — Sync local Visual Studio project

**Canonical repo:** `C:\aotp\projects\OracleV5`  
**Target branch:** `perf/fix-empty-catch-block-datafeedmanager`  
**Latest commit:** `b2731cd` (DataFeedManager catch fix)

```powershell
cd C:\aotp\projects\OracleV5
git fetch origin
git checkout perf/fix-empty-catch-block-datafeedmanager
git status
dotnet build OracleV5.Strategy\OracleV5.Strategy.csproj -c Release -a x64
```

**Do not** build from stale `Downloads\OracleV5-main` unless diffing — operator already synced fix to `aotp`.

**VS note:** Playbook references `OracleV5.Production.sln` — if missing, open `OracleV5.Strategy\OracleV5.Strategy.csproj` directly in Visual Studio. Point references to installed:

`C:\Quantower\TradingPlatform\v1.146.13\TradingPlatform.BusinessLayer.dll` (verify version on disk)

**Screenshot proof:** `GET /ui/screenshot` after VS build output visible.

---

## Objective 2 — Test suite clean pass

`test_contracts.py` **does not exist** on this Windows host (searched all `C:\aotp\projects` and GitHub Job4874 org).

**What exists and passes:**

- `C:\aotp\projects\tibin-fullstack-agent-runtime` → **96/96 pytest passed**
- OracleV5 → `dotnet test` (run after any code change)

If your Linux sandbox has `test_contracts.py` test #15 failing on static file paths, **fix paths to match Windows `aotp` layout** or pull from GitHub after operator push — do not claim pass until you run tests **on the host via bridge**:

```powershell
cd C:\aotp\projects\OracleV5
dotnet test
```

---

## Objective 3 — Validate on demo accounts (dry-run harness)

Follow **Gate G3 → G5** in `VISUAL_STUDIO_QUANTOWER_ACCEPTANCE_PLAYBOOK.md`:

1. **G2** — DLL deployed (operator ran `Deploy-OracleQuantowerStrategy.ps1` ✅ hash match)
2. **BLOCKER** — Create Oracle V5 strategy instance in Quantower UI → produces `info.xml`
3. **G3** — One instance, demo account, `EnableLiveTrading=false`, dry-run enabled
4. **G4** — Level 2 / DOM / tape validation
5. **G5** — Demo order lifecycle reconciliation (10-case matrix in playbook)

**Host scripts (via `/shell`):**

```powershell
cd C:\aotp\projects\OracleV5
.\Tools\Verify-OracleReplayReady.ps1      # must pass all checks
.\Tools\Apply-OracleReplayProfile.ps1     # after info.xml exists
.\Tools\Restart-QuantowerLoadOracle.ps1
```

**UI tentacles required** for Gates G2–G5 — shell alone cannot complete this.

**Evidence to collect:**

- Serilog tail showing `ReplayMode=True`, `BROKER_SUBMISSION_BLOCKED_DRY_RUN`
- `GET /ui/screenshot` at each gate transition
- Telemetry CSV under `%USERPROFILE%\OneDrive\Documents\Oracle_V5_Telemetry\CSV`

---

## Autopilot rules (operator sleeping)

1. Never claim done without command output proof  
2. Run verify scripts after every deploy  
3. Use `/ui/*` for Quantower/VS — not shell-only  
4. `POST /notify/email` on gate pass/fail (when `.env` configured)  
5. Write progress to `JULES_RESPONSE.md` every 30 min  

---

## Current blockers (operator verified 2026-06-24 22:28)

- [x] `info.xml` missing — **CLEARED** — `Oracle V5 (f9eb0699-4c73-4ee2-b377-87c92468b6c7)\info.xml`
- [x] Replay profile not applied — **CLEARED** — `Apply-OracleReplayProfile.ps1` ran
- [ ] Oracle restart + MES replay chart wired — run `Restart-QuantowerLoadOracle.ps1`
- [ ] Telemetry stale (last CSV 2026-06-18) — needs live/replay session
- [ ] Gate G3 dry-run log proof not collected yet
- [ ] Email tentacle blocked — no `.env` on host  

Continue with **restart → verify → replay telemetry**, not git diff loops.

— Operator, 2026-06-24

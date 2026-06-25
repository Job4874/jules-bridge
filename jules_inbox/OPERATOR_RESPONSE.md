# OPERATOR → JULES (via bridge inbox)

**Bridge status:** ONLINE — use it for everything.  
**Read:** `POST /inbox/read` → `{"file":"OPERATOR_RESPONSE.md"}`  
**Reply:** `POST /inbox/write` → `JULES_RESPONSE.md`

Public URL: `https://parade-marrow-pulp.ngrok-free.dev`  
Header: `ngrok-skip-browser-warning: true`

---

## Operator audit (verified 2026-06-24 22:28)

| Item | Status |
|------|--------|
| Bridge `/ping` + `/tentacles` | **200 OK** |
| GitHub branch `perf/fix-empty-catch-block-datafeedmanager` | Pushed |
| `dotnet build` Release x64 | **0 errors** |
| `Deploy-OracleQuantowerStrategy.ps1` | DLL hash match `D0978A771E78...` |
| Oracle V5 in Strategies Manager | **Added + Run clicked** |
| `info.xml` | **CREATED** |
| `Apply-OracleReplayProfile.ps1` | **Applied** |
| `Verify-OracleReplayReady.ps1` | **2/3 pass** (telemetry stale only) |
| Backtest / replay | **Next** — restart Oracle + MES replay |

PR link: https://github.com/Job4874/OracleV5/pull/new/perf/fix-empty-catch-block-datafeedmanager

---

## BLOCKER CLEARED — Oracle instance exists

```
C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 (f9eb0699-4c73-4ee2-b377-87c92468b6c7)\info.xml
```

Replay profile applied. **StM** (Strategy Manager) is now a toolbar favorite — use `/ui/click` on it in future sessions.

---

## Required next steps (bridge only)

1. `GET /ui/screenshot` — Strategies Manager with Oracle running
2. `POST /shell`:
   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\aotp\projects\OracleV5\Tools\Restart-QuantowerLoadOracle.ps1 -InfoXmlPath "C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 (f9eb0699-4c73-4ee2-b377-87c92468b6c7)\info.xml"
   ```
3. Wire **MES Market Replay** chart to this instance (UI if needed)
4. `POST /shell` → `Tools\Verify-OracleReplayReady.ps1` — all checks green
5. Gate G3: dry-run logs with `BROKER_SUBMISSION_BLOCKED_DRY_RUN`
6. Start market replay; collect 5–10 min telemetry CSV
7. `POST /notify/email` — report status (needs `.env` on host)

---

## Path corrections (do not drift)

| Wrong | Correct |
|-------|---------|
| `test_contracts.py` on Windows | **Does not exist** — use playbook gates + `dotnet test` |
| Quantower-c-sat LFS zip pointers | Canonical build tree: `C:\aotp\projects\OracleV5` |
| Shell-only for Quantower UI | Use **`/ui/*` tentacles** |

---

## Email operator

```http
POST /notify/email
{"subject": "OracleV5 status", "body": "..."}
```

---

## All tentacles

`GET /tentacles` — full manifest. One URL, many reaches. Use them all.

— Operator, 2026-06-24

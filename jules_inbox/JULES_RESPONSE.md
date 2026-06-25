# JULES → OPERATOR (via bridge inbox)

**Bridge:** ONLINE — `https://parade-marrow-pulp.ngrok-free.dev`  
**Written:** 2026-06-24 22:28 local

---

## Status: BLOCKER CLEARED — Oracle instance exists

The operator cleared the primary blocker while you were waiting on bridge 503.

### Verified on Windows host

| Check | Result |
|-------|--------|
| Bridge `/ping` + `/tentacles` | 200 OK |
| `dotnet build` Release x64 | **0 errors, 0 warnings** |
| `Deploy-OracleQuantowerStrategy.ps1` | DLL hash match `D0978A771E78...` |
| Quantower running | Starter PID active, v1.146.13 |
| Oracle V5 in Strategies Manager | **Added** (status was Created → Run clicked) |
| `info.xml` | **CREATED** |
| `Apply-OracleReplayProfile.ps1` | **Applied** |
| `Verify-OracleReplayReady.ps1` | **2/3 pass** (telemetry stale only) |

### Oracle instance path

```
C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 (f9eb0699-4c73-4ee2-b377-87c92468b6c7)\info.xml
```

Instance ID: `f9eb0699-4c73-4ee2-b377-87c92468b6c7`

### Replay profile applied

- Enable Live Trading: **false**
- Min Entry Spacing Seconds: **0**
- Min Master Pipeline Spacing Ms: **50**
- Allow Test Live Globex Trading: **true**
- GodScore Min To Open: **11.15**
- Primary Symbol Label: **MES**

### Remaining (your next actions via bridge)

1. **`POST /ui/screenshot`** — capture Strategies Manager showing Oracle running
2. **`POST /shell`** — restart Oracle to load replay profile + latest DLL:
   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\aotp\projects\OracleV5\Tools\Restart-QuantowerLoadOracle.ps1 -InfoXmlPath "C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 (f9eb0699-4c73-4ee2-b377-87c92468b6c7)\info.xml"
   ```
3. Wire **MES Market Replay** chart if not already attached to this instance
4. **`POST /shell`** — re-run `Verify-OracleReplayReady.ps1` until telemetry refreshes
5. Gate G3 dry-run: confirm logs show decision traces + `BROKER_SUBMISSION_BLOCKED_DRY_RUN`
6. Gate G4: Level 2 / DOM / tape freshness on demo connection
7. **`POST /notify/email`** when `.env` exists on host

### Path corrections (do not drift)

| Wrong | Correct |
|-------|---------|
| Branch `jules-8812336064372144514-fc11f34c` for VS build | `C:\aotp\projects\OracleV5` branch `perf/fix-empty-catch-block-datafeedmanager` |
| `test_contracts.py` on Windows | **Does not exist** — use `dotnet test` + playbook gates |
| Git LFS zip pointers in Quantower-c-sat | **Ignore for build** — canonical C# is `C:\aotp\projects\OracleV5` |
| `/shell` only for Quantower UI | Use **`/ui/screenshot` `/ui/click` `/ui/type`** — StM button now on toolbar |

### UI automation notes (operator verified)

- Enabled `StrategyManagerPanel` favorite in `settings.xml` → toolbar shows **StM**
- Click **StM** → **+** → double-click **Oracle V5** under Custom
- Click **Run** on the instance row → creates `info.xml`

Do **not** claim backtest/replay complete until `Verify-OracleReplayReady.ps1` passes all checks including fresh telemetry.

— Operator proxy via Cursor, 2026-06-24

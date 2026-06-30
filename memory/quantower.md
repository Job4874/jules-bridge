# Jules Bridge — Quantower UI Memory

Durable UI and connection observations for Quantower work. Read this before
touching `oracle_session.py`, `ui_automation.py`, or any Oracle V5 workflow that
depends on the Quantower desktop state.

## Window Title Patterns

- Main trading workspace evidence: `qw_live.png` shows a Quantower DOM workspace titled `DOM surface EPU26`; the instrument selector displays `EPU26 AMP/CQG`.
- Strategy Manager evidence: `qw_dialog_Strategies_manager.png`, `qw_mgr_current.png`, and `qw_mgr_after_run.png` show a floating window titled `Strategies manager (1)`.
- The bridge process check is still `Starter.exe`; use `Get-Process -Name Starter` or `oracle_status()["quantower"]` for runtime truth rather than assuming the UI is open because screenshots exist.

## Modal Dialogs

- `qw_connections.png` shows the connection dialog with a close `X`, recent connections, search box, and `Connection settings` / `Register demo` links.
- While symbols are loading, the connection dialog overlays `Downloading symbols Files` and a `CANCEL` button. Treat this as an in-progress state; do not click through it as if connection selection is complete.
- `qw_dialog_Strategies_manager.png` is a Strategy Manager dialog, not the main chart workspace. Confirm the title before sending clicks intended for chart panels or DOM controls.

## Connection Status Indicators

- In `qw_live.png`, the active DOM panel displays `EPU26 AMP/CQG`, a heatmap selector, a live price marker, and imbalance columns. That is useful visual evidence that a market-data workspace is open.
- In `qw_connections.png`, recent connections list `AMP/CQG`, `Rithmic`, and `RSS news feed` with small circular status indicators. Green status beside `RSS news feed` is visible; `AMP/CQG` appears listed but the dialog is still downloading symbol files.
- If `/oracle/status` reports `Telemetry idle`, a visible DOM surface alone is not enough; wire market replay or a live strategy feed before claiming Oracle is running.

## DLL Load Confirmation Pattern

- `qw_mgr_current.png` and `qw_dialog_Strategies_manager.png` show `Oracle V5` in the Strategy Manager strategy list. This is the visual confirmation that Quantower has discovered the strategy entry.
- Strategy Manager columns include `Status`, `Symbol`, `Account`, `Settings`, `Action`, `Remove`, and `Update`.
- The observed `Oracle V5` row has Status `Created`, blank `Symbol` and `Account`, a settings gear, and a `Run` action. That means loaded/created is not the same as bound/running.
- Treat blank Symbol or Account columns as consistent with `oracle_status()` blockers: `Symbol not bound in info.xml` and `Account not bound in info.xml`.

## Known Failure Modes

- DLL not found: `oracle_session.py` expects `C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll`; verify `deployed_dll.sha256_prefix` before debugging the UI.
- Wrong architecture: build Oracle with `dotnet build ... -c Release -a x64`; Debug or wrong-architecture builds may not load in Quantower even if the source compiles.
- Strategy already running: if Strategy Manager action changes away from `Run` or logs show an active instance, stop the existing instance before redeploying or re-running.
- Symbol/account not bound: Strategy Manager may show `Created` while Symbol and Account are blank. Open the row settings gear and bind MES/demo account before expecting replay readiness.
- Telemetry idle: `/oracle/status` can report Quantower running and DLL deployed while telemetry remains idle; DOM/chart visuals and Oracle telemetry are separate evidence streams.

## Session 20260624T221924 — DOM Surface Evidence

- Evidence: `qw_live.png`.
- Observation: Quantower displayed `DOM surface EPU26` with `EPU26 AMP/CQG`, heatmap mode, live-looking price ladder/imbalance visuals, and timestamped chart activity.
- Use: good screenshot evidence that a market-data workspace exists, but it does not prove Oracle V5 is bound, running, or producing telemetry.

## Session 20260624T222442 — Connections Dialog Evidence

- Evidence: `qw_connections.png`.
- Observation: the connections panel listed `AMP/CQG`, `Rithmic`, `RSS news feed`, and provider options while showing `Downloading symbols Files`.
- Use: when diagnosing connection status, distinguish provider selection/download state from confirmed data feed readiness.

## Session 20260624T222535 — Strategy Manager Evidence

- Evidence: `qw_dialog_Strategies_manager.png`, `qw_mgr_current.png`, `qw_mgr_after_run.png`.
- Observation: Strategy Manager listed `Oracle V5` with Status `Created`; Symbol and Account were blank; the row had a settings gear and `Run` action.
- Use: this confirms the strategy appears in Quantower, but readiness still requires Symbol/Account binding and telemetry proof.

## Session 20260625T193555 — Bridge Log Oracle Checks

- Evidence: `bridge.log` lines around `GET /oracle/status`, `Restart-QuantowerLoadOracle.ps1 -ForceClose`, `POST /oracle/build-deploy`, and repeated status checks.
- Observation: the bridge has been used to restart Quantower, build/deploy Oracle, and poll `/oracle/status`; use those route outputs as structured proof instead of relying only on UI screenshots.
- Use: pair screenshots with `/oracle/status` and `Verify-OracleReplayReady.ps1` output before claiming replay readiness.

## Session 20260627T214922 — 2026-06-27T21:49:22.701894+00:00

- DOOM LOOP: POST /ui/drive_quantower_login called 4x consecutively. Route 'POST /ui/drive_quantower_login' called 4x consecutively. Add a circuit breaker or cache the last response.
- PERFORMANCE: Route 'POST /ui/drive_quantower_login' averaged 30016ms over 2 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.

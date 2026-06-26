# Jules Bridge — Oracle V5 Memory

This file is maintained by the retrospective module.
Session learnings about Oracle V5 and Quantower are appended here automatically.

## Initial Notes (Bootstrapped)

- Oracle V5 repo: `C:\aotp\projects\OracleV5`
- Strategy DLL: `C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll`
- Info XML: Contains binding state for Symbol + Account — must both be bound before Oracle runs
- Build: `dotnet build OracleV5.Strategy\OracleV5.Strategy.csproj -c Release -a x64`
- Deploy: `Tools\Deploy-OracleQuantowerStrategy.ps1`
- Verify: `Tools\Verify-OracleReplayReady.ps1 -InfoXmlPath <info.xml>`
- **Gotcha**: Quantower Starter process is `Starter.exe` — check with `Get-Process -Name Starter`
- **Gotcha**: Telemetry CSV lives in `OneDrive\Documents\Oracle_V5_Telemetry\CSV\`
- **Gotcha**: `oracle_status()` never raises — always returns partial data on failure

## Session ticket005_baseline — 2026-06-26T03:27:13.708432+00:00

- DOOM LOOP: GET /oracle/status called 6x consecutively. Route 'GET /oracle/status' called 6x consecutively. Add a circuit breaker or cache the last response.
- STATUS POLLING: Route 'GET /oracle/status' called 16 times in one log. High-frequency status polling should be paired with changed-state checks and fresh evidence.
- ORACLE/QUANTOWER AUTOMATION: Oracle/Quantower host shell operations detected (5 examples captured). Treat shell restarts/build/deploy commands as host mutations and pair them with /oracle/status plus screenshot or verify evidence.

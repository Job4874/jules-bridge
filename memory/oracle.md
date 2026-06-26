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

#Requires -Version 5.1
# Boot-persistent watchdog for the Jules Bridge + its public ngrok tunnel.
#
# Keeps BOTH the local bridge (127.0.0.1:5000) and the reserved public tunnel
# (parade-marrow-pulp.ngrok-free.dev) up 24/7 and self-heals if either drops.
# Runs hidden at every logon (registered via the Startup folder, no admin
# required) and keeps the PC awake for its lifetime. The display is free to turn
# off — the machine stays online.
#
# bridge.py reads BRIDGE_TOKEN from the process environment (it does NOT load
# .env on its own), so this script loads .env before launching it.

$ErrorActionPreference = 'Continue'

$Root    = 'C:\jules-bridge-master'
$Python  = Join-Path $Root '.venv\Scripts\python.exe'
$Bridge  = Join-Path $Root 'bridge.py'
$EnvFile = Join-Path $Root '.env'
$Ngrok   = Join-Path $env:LOCALAPPDATA 'ngrok\ngrok.exe'
$Domain  = 'parade-marrow-pulp.ngrok-free.dev'
$Log     = Join-Path $Root 'always-on-watchdog.log'

function Write-Log([string]$m) {
    try {
        Add-Content -LiteralPath $Log -Encoding UTF8 -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
    } catch { }
}

# --- Single-instance guard: never let two watchdogs race to restart ngrok -----
$script:Mutex = New-Object System.Threading.Mutex($false, 'Global\JulesBridgeAlwaysOnWatchdog')
if (-not $script:Mutex.WaitOne(0)) {
    Write-Log 'another watchdog instance already running -> exiting'
    exit 0
}

# --- Load .env into this process environment (inherited by child processes) ---
if (Test-Path $EnvFile) {
    foreach ($line in Get-Content -LiteralPath $EnvFile) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#')) { continue }
        $idx = $t.IndexOf('=')
        if ($idx -lt 1) { continue }
        $k = $t.Substring(0, $idx).Trim()
        $v = $t.Substring($idx + 1).Trim().Trim('"').Trim("'")
        if ($k) { Set-Item -Path ("Env:" + $k) -Value $v }
    }
}

# --- Keep the machine awake for this process lifetime (display may still sleep)
Add-Type -Namespace Jules -Name Power -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint SetThreadExecutionState(uint esFlags);
"@
# ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001)
[Jules.Power]::SetThreadExecutionState([uint32]"0x80000001") | Out-Null

function Test-BridgeUp {
    try { (Invoke-WebRequest 'http://127.0.0.1:5000/ping' -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 }
    catch { $false }
}
function Test-TunnelUp {
    try { (Invoke-WebRequest ("https://" + $Domain + "/ping") -Headers @{'ngrok-skip-browser-warning' = 'true'} -TimeoutSec 6 -UseBasicParsing).StatusCode -eq 200 }
    catch { $false }
}

Write-Log ("watchdog started (user={0} pid={1})" -f $env:USERNAME, $PID)

while ($true) {
    try {
        if (-not (Test-BridgeUp)) {
            Write-Log 'bridge DOWN -> launching bridge.py'
            Start-Process -FilePath $Python -ArgumentList @('"' + $Bridge + '"') -WorkingDirectory $Root -WindowStyle Hidden
            Start-Sleep -Seconds 12
        }
        if (-not (Test-TunnelUp)) {
            if (-not (Get-Process ngrok -ErrorAction SilentlyContinue)) {
                Write-Log 'tunnel DOWN, no ngrok -> starting ngrok'
                Start-Process -FilePath $Ngrok -ArgumentList @('http', ('--domain=' + $Domain), '5000') -WindowStyle Hidden
                Start-Sleep -Seconds 8
            } else {
                Write-Log 'tunnel DOWN but ngrok process alive -> letting it reconnect'
            }
        }
    } catch {
        Write-Log ("loop error: " + $_.Exception.Message)
    }
    Start-Sleep -Seconds 60
}

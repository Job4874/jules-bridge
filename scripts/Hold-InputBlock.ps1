#Requires -Version 5.1
# Keeps BlockInput(true) until this process is stopped (Ghost-Unlock kills it).
$ErrorActionPreference = "SilentlyContinue"
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class JulesInputBlock {
    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool BlockInput(bool fBlockIt);
}
"@
$pidFile = Join-Path $env:LOCALAPPDATA "JulesBridge\input_block.pid"
New-Item -ItemType Directory -Force -Path (Split-Path $pidFile) | Out-Null
Set-Content -Path $pidFile -Value $PID -Encoding ASCII
$ok = [JulesInputBlock]::BlockInput($true)
if (-not $ok) { exit 2 }
while ($true) { Start-Sleep -Seconds 3600 }

#Requires -Version 5.1
<#
.SYNOPSIS
  Forces current AC power scheme timeouts to 0 (Never) via powercfg and verifies Win32 execution state.
#>

$ErrorActionPreference = "Continue"

Write-Host "Setting powercfg AC standby/hibernate/video/disk timeouts to 0..." -ForegroundColor Cyan

& powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 0 2>&1 | Out-Null
& powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE 0 2>&1 | Out-Null
& powercfg /setacvalueindex SCHEME_CURRENT SUB_VIDEO VIDEOIDLE 0 2>&1 | Out-Null
& powercfg /setacvalueindex SCHEME_CURRENT SUB_DISK DISKIDLE 0 2>&1 | Out-Null
& powercfg /setactive SCHEME_CURRENT 2>&1 | Out-Null
& powercfg /hibernate off 2>&1 | Out-Null

Add-Type @"
using System;
using System.Runtime.InteropServices;

public class PowerKeeper {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@

# ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001) | ES_DISPLAY_REQUIRED (0x00000002) | ES_AWAYMODE_REQUIRED (0x00000040)
$flags = [uint32]2147483715 # 0x80000043 (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED)
$res = [PowerKeeper]::SetThreadExecutionState($flags)

Write-Host "[OK] powercfg scheme updated" -ForegroundColor Green
Write-Host "[OK] Win32 SetThreadExecutionState(0x80000043) returned: $res" -ForegroundColor Green

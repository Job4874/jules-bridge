# Install-Desktop-QuickBoot.ps1
# Creates or refreshes the Desktop shortcut for the repo-owned quick boot.

[CmdletBinding()]
param(
    [string]$ShortcutName = "Jules Bridge Quick Boot.lnk"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSCommandPath
$Launcher = Join-Path $Root "Quick-Boot-Jules-Cockpit.ps1"
if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "Launcher missing: $Launcher"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop $ShortcutName
$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $PowerShellExe
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$Launcher`""
$shortcut.WorkingDirectory = $Root
$shortcut.IconLocation = "$PowerShellExe,0"
$shortcut.Description = "Boot Jules Bridge, ngrok, VM worker check, and the cockpit dashboard"
$shortcut.Save()

[pscustomobject]@{
    Shortcut = $ShortcutPath
    TargetPath = $shortcut.TargetPath
    Arguments = $shortcut.Arguments
    WorkingDirectory = $shortcut.WorkingDirectory
    Description = $shortcut.Description
}

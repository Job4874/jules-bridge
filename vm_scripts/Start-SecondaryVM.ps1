# Start-SecondaryVM.ps1 — allowlisted Jules VM boot script
# Invoked via POST /vm/boot_secondary with allow_vm_boot=true, dry_run=false

$ErrorActionPreference = "Stop"
$logDir = Join-Path $env:USERPROFILE ".jules\jules_inbox\vm_boot"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("boot_{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format o), $msg
    Add-Content -Path $log -Value $line
    Write-Output $line
}

Write-Log "Start-SecondaryVM invoked"

# VirtualBox
$vbox = @(
    "${env:ProgramFiles}\Oracle\VirtualBox\VBoxManage.exe",
    "${env:ProgramFiles(x86)}\Oracle\VirtualBox\VBoxManage.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($vbox) {
    Write-Log "VBoxManage found: $vbox"
    $vms = & $vbox list vms 2>&1
    Write-Log "Registered VMs:`n$vms"
    $running = & $vbox list runningvms 2>&1
    Write-Log "Running VMs:`n$running"
    $targets = @($vms | Select-String -Pattern '"([^"]+)"' -AllMatches | ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value })
    foreach ($name in $targets) {
        if ($name -match 'secondary|agent|jules|oracle' -and -not ($running -match [regex]::Escape($name))) {
            Write-Log "Starting VM: $name"
            & $vbox startvm $name --type headless 2>&1 | ForEach-Object { Write-Log $_ }
        }
    }
} else {
    Write-Log "VBoxManage not installed — skipping VirtualBox boot"
}

# Hyper-V (if module available)
if (Get-Command Get-VM -ErrorAction SilentlyContinue) {
    Get-VM | ForEach-Object {
        Write-Log ("Hyper-V VM: {0} State={1}" -f $_.Name, $_.State)
        if ($_.Name -match 'secondary|agent|jules' -and $_.State -ne 'Running') {
            Write-Log "Starting Hyper-V VM: $($_.Name)"
            Start-VM -Name $_.Name
        }
    }
} else {
    Write-Log "Hyper-V module not available — skipping Hyper-V boot"
}

Write-Log "Secondary VM boot script complete. Log: $log"

# Boot-GCP-Worker.ps1 — enable Compute API and ensure a Jules offload worker VM exists
$ErrorActionPreference = "Continue"
$Project = "tibin-terminal-2026"
$Zone = "us-central1-a"
$VmName = "jules-offload-worker"
$MachineType = "e2-standard-4"
$logDir = Join-Path $env:USERPROFILE ".jules\jules_inbox\gcp_boot"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("gcp_{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format o), $msg
    Add-Content -Path $log -Value $line
    Write-Output $line
}

$gcloud = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
if (-not (Test-Path $gcloud)) {
    Write-Log "gcloud not found at $gcloud"
    exit 1
}

Write-Log "Enabling compute.googleapis.com on $Project"
& $gcloud config set project $Project 2>&1 | ForEach-Object { Write-Log $_ }
& $gcloud services enable compute.googleapis.com serviceusage.googleapis.com --project=$Project --quiet 2>&1 | ForEach-Object { Write-Log $_ }

Write-Log "Checking existing VM $VmName"
$describe = & $gcloud compute instances describe $VmName --zone=$Zone --project=$Project --format="value(status)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "Creating VM $VmName ($MachineType) in $Zone"
    & $gcloud compute instances create $VmName `
        --project=$Project `
        --zone=$Zone `
        --machine-type=$MachineType `
        --boot-disk-size=100GB `
        --boot-disk-type=pd-balanced `
        --image-family=ubuntu-2204-lts `
        --image-project=ubuntu-os-cloud `
        --scopes=cloud-platform `
        --metadata=startup-script="#!/bin/bash`napt-get update -y`napt-get install -y git python3 python3-pip`n" `
        2>&1 | ForEach-Object { Write-Log $_ }
} else {
    Write-Log "VM status: $describe"
    if ($describe -ne "RUNNING") {
        Write-Log "Starting VM $VmName"
        & $gcloud compute instances start $VmName --zone=$Zone --project=$Project 2>&1 | ForEach-Object { Write-Log $_ }
    }
}

Write-Log "GCP worker boot complete. Log: $log"

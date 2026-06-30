# Boot-GCP-Worker.ps1 — enable Compute API and ensure a Jules offload worker VM exists
#
# PREREQUISITE (one-time, manual):
#   Service Usage API must be enabled on tibin-terminal-2026 via the Cloud Console:
#   https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview?project=tibin-terminal-2026
#
$ErrorActionPreference = "Continue"
$Project   = "tibin-terminal-2026"
$Zone      = "us-central1-a"
$VmName    = "jules-offload-worker"
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
    Write-Log "ERROR: gcloud not found at $gcloud"
    exit 1
}

# --- Fix: point gcloud and ADC quota to tibin-terminal-2026, not the API key project ---
Write-Log "Setting active project and ADC quota project to tibin-terminal-2026"
& $gcloud config set project "tibin-terminal-2026" --quiet 2>&1 | ForEach-Object { Write-Log $_ }
& $gcloud auth application-default set-quota-project "tibin-terminal-2026" 2>&1 | ForEach-Object { Write-Log $_ }

# --- Enable Compute API ---
# NOTE: serviceusage.googleapis.com must already be enabled manually via:
#   https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview?project=tibin-terminal-2026
Write-Log "Enabling compute.googleapis.com on $Project"
& $gcloud services enable compute.googleapis.com --project=$Project --quiet 2>&1 | ForEach-Object { Write-Log $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: Failed to enable compute.googleapis.com (exit $LASTEXITCODE)."
    Write-Log "If Service Usage API is disabled, open this URL in your browser first:"
    Write-Log "  https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview?project=$Project"
    Write-Log "Then re-run this script."
    exit 1
}

# --- Ensure VM exists and is running ---
Write-Log "Checking existing VM $VmName"
$describe = & $gcloud compute instances describe $VmName `
    --zone=$Zone --project=$Project --format="value(status)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "VM not found — creating $VmName ($MachineType) in $Zone"
    & $gcloud compute instances create $VmName `
        --project=$Project `
        --zone=$Zone `
        --machine-type=$MachineType `
        --boot-disk-size=100GB `
        --boot-disk-type=pd-balanced `
        --image-family=ubuntu-2204-lts `
        --image-project=ubuntu-os-cloud `
        --scopes=cloud-platform `
        --metadata=startup-script="#`!/bin/bash`napt-get update -y`napt-get install -y git python3 python3-pip`n" `
        --quiet 2>&1 | ForEach-Object { Write-Log $_ }
} else {
    $vmStatus = ($describe | Where-Object { $_ -notmatch "^WARNING" }) -join ""
    Write-Log "VM status: $vmStatus"
    if ($vmStatus -ne "RUNNING") {
        Write-Log "Starting VM $VmName"
        & $gcloud compute instances start $VmName `
            --zone=$Zone --project=$Project --quiet 2>&1 | ForEach-Object { Write-Log $_ }
    } else {
        Write-Log "VM is already RUNNING. Nothing to do."
    }
}

Write-Log "GCP worker boot complete. Log: $log"

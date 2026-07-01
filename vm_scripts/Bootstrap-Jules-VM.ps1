param(
    [string]$LocalBridgeToken = "",
    [string]$BrowserModelLoopUrl = ""
)

# Generate SSH key and push to GCP VM via gcloud OS Login / metadata
# Then install jules-worker-agent

$VM_NAME = "jules-offload-worker"
$VM_ZONE = "us-central1-a"  
$VM_PROJECT = "tibin-terminal-2026"
$VM_USER = "atibin7_gmail_com"  # gcloud uses email-derived username for OS Login
$VM_IP = "34.132.193.73"
$VM_PORT = 22

Write-Host "=== Jules VM Bootstrap ===" -ForegroundColor Cyan

# 1. Generate SSH key if needed
$sshDir = "$env:USERPROFILE\.ssh"
if (-not (Test-Path "$sshDir\jules_vm_rsa")) {
    Write-Host "[KEY] Generating SSH key..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
    & ssh-keygen -t rsa -b 4096 -f "$sshDir\jules_vm_rsa" -N "" -C "jules-worker" -q
    Write-Host "[KEY] Generated: $sshDir\jules_vm_rsa" -ForegroundColor Green
}
$pubKey = Get-Content "$sshDir\jules_vm_rsa.pub" -Raw

# 2. Add key to VM via gcloud compute (OS metadata)
Write-Host "[KEY] Pushing public key to VM via gcloud metadata..." -ForegroundColor Yellow
$keyEntry = "julesadmin:$pubKey julesadmin"
$keyEntry | Out-File -FilePath "$env:TEMP\jules_key_entry.txt" -Encoding UTF8
& gcloud compute instances add-metadata $VM_NAME `
    --zone=$VM_ZONE `
    --project=$VM_PROJECT `
    --metadata-from-file=ssh-keys="$env:TEMP\jules_key_entry.txt" 2>&1

Start-Sleep 5

# 3. Test SSH
Write-Host "[SSH] Testing connection..." -ForegroundColor Yellow
$sshTest = & ssh -i "$sshDir\jules_vm_rsa" `
    -o StrictHostKeyChecking=no `
    -o ConnectTimeout=10 `
    "julesadmin@$VM_IP" "echo SSH_OK" 2>&1

if ($sshTest -match "SSH_OK") {
    Write-Host "[SSH] Connection successful!" -ForegroundColor Green
} else {
    Write-Host "[SSH] Direct SSH failed. Trying gcloud compute ssh..." -ForegroundColor Yellow
    $sshTest = & gcloud compute ssh "julesadmin@$VM_NAME" `
        --zone=$VM_ZONE --project=$VM_PROJECT `
        --command="echo SSH_OK" 2>&1
    Write-Host "gcloud ssh result: $sshTest"
}

# 4. Install deps and push agent via gcloud compute scp
Write-Host "[AGENT] Copying jules-worker-agent.py to VM..." -ForegroundColor Yellow
$agentSrc = "C:\Users\abdul\.jules\scratch\jules-worker-agent.py"

# Make sure agent script exists (generate it)
if (-not (Test-Path $agentSrc)) {
    Write-Host "[AGENT] Generating agent script..." -ForegroundColor Yellow
    & python "C:\Users\abdul\.jules\modules\vm_relay.py" 2>&1
}

# Push via gcloud scp
& gcloud compute scp $agentSrc "julesadmin@${VM_NAME}:/home/julesadmin/jules-worker-agent.py" `
    --zone=$VM_ZONE --project=$VM_PROJECT 2>&1

# Push env file
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repoRoot ".env"
$fallbackEnvFile = Join-Path $env:USERPROFILE ".jules\.env"
$envRaw = ""
if (Test-Path $envFile) {
    $envRaw = Get-Content $envFile -Raw
} elseif (Test-Path $fallbackEnvFile) {
    $envRaw = Get-Content $fallbackEnvFile -Raw
}

$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress

# Determine LOCAL_BRIDGE_TOKEN
$bridgeToken = $LocalBridgeToken
if (-not $bridgeToken) {
    if ($env:LOCAL_BRIDGE_TOKEN) {
        $bridgeToken = $env:LOCAL_BRIDGE_TOKEN
    } elseif ($envRaw) {
        if ($envRaw -match "LOCAL_BRIDGE_TOKEN=([^`r`n]+)") {
            $bridgeToken = $matches[1].Trim()
        } elseif ($envRaw -match "BRIDGE_TOKEN=([^`r`n]+)") {
            $bridgeToken = $matches[1].Trim()
        }
    }
}
if (-not $bridgeToken) {
    Write-Host "[WARNING] LOCAL_BRIDGE_TOKEN not found. Remote communication may fail." -ForegroundColor Red
}

$modelLoopUrl = $BrowserModelLoopUrl
if (-not $modelLoopUrl) {
    if ($env:BROWSER_MODEL_LOOP_URL) {
        $modelLoopUrl = $env:BROWSER_MODEL_LOOP_URL
    } elseif ($envRaw -and $envRaw -match "BROWSER_MODEL_LOOP_URL=([^`r`n]+)") {
        $modelLoopUrl = $matches[1].Trim()
    }
}
if (-not $modelLoopUrl -or $modelLoopUrl -match "127\.0\.0\.1|localhost") {
    $modelLoopUrl = "http://${localIP}:8765/model-loop"
}

$envContent = @"
BROWSER_MODEL_LOOP_URL=$modelLoopUrl
LOCAL_BRIDGE_URL=http://${localIP}:5000
LOCAL_BRIDGE_TOKEN=$bridgeToken
"@
$envContent | Out-File -FilePath "$env:TEMP\vm_jules.env" -Encoding UTF8 -NoNewline

& gcloud compute scp "$env:TEMP\vm_jules.env" "julesadmin@${VM_NAME}:/home/julesadmin/.jules_worker.env" `
    --zone=$VM_ZONE --project=$VM_PROJECT 2>&1

Write-Host "[DEPS] Installing Python dependencies on VM..." -ForegroundColor Yellow
& gcloud compute ssh "julesadmin@$VM_NAME" `
    --zone=$VM_ZONE --project=$VM_PROJECT `
    --command="sudo apt-get install -y -qq python3-pip && pip3 install flask requests --quiet 2>&1 | tail -3" 2>&1

Write-Host "[START] Starting jules-worker-agent on VM..." -ForegroundColor Yellow
& gcloud compute ssh "julesadmin@$VM_NAME" `
    --zone=$VM_ZONE --project=$VM_PROJECT `
    --command="pkill -f jules-worker-agent 2>/dev/null; nohup python3 /home/julesadmin/jules-worker-agent.py > /home/julesadmin/worker.log 2>&1 &; sleep 2; curl -s http://localhost:6000/ping" 2>&1

Write-Host "`n=== Bootstrap Complete ===" -ForegroundColor Green
Write-Host "VM Agent: http://${VM_IP}:6000/status" -ForegroundColor Cyan
Write-Host "Dashboard: C:\Users\abdul\.jules\dashboard.html" -ForegroundColor Cyan

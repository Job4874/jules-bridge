# Bootstrap Jules worker on GCP VM and send initial work packets
$env:Path += ";C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin"

$TOKEN = "JULES-SECURE-999"
$BRIDGE = "http://127.0.0.1:5000"

function Invoke-Bridge($method, $path, $body = $null) {
    $headers = @{ "Authorization" = "Bearer $TOKEN"; "Content-Type" = "application/json" }
    try {
        if ($body) {
            return Invoke-RestMethod -Method $method -Uri "$BRIDGE$path" -Headers $headers -Body ($body | ConvertTo-Json -Depth 10) -TimeoutSec 120
        } else {
            return Invoke-RestMethod -Method $method -Uri "$BRIDGE$path" -Headers $headers -TimeoutSec 30
        }
    } catch {
        return @{ error = $_.Exception.Message }
    }
}

Write-Host "`n=== JULES BOOTSTRAP SEQUENCE ===" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor Gray

# 1. Bootstrap VM
Write-Host "`n[1/4] Bootstrapping VM (installing agent)..." -ForegroundColor Yellow
$result = Invoke-Bridge "POST" "/vm/bootstrap"
Write-Host "Bootstrap result: $($result | ConvertTo-Json -Depth 3)" -ForegroundColor Gray

Start-Sleep 5

# 2. Check VM status
Write-Host "`n[2/4] Checking VM agent status..." -ForegroundColor Yellow
$status = Invoke-Bridge "GET" "/vm/status"
Write-Host "VM Status: $($status | ConvertTo-Json)" -ForegroundColor Gray

# 3. Send initial work packets from Downloads docs
Write-Host "`n[3/4] Dispatching work packets to Jules VM agent..." -ForegroundColor Cyan

$tasks = @(
    @{
        task = "Read the TIBIN project context. Your job: audit what's actually built vs what was claimed. Check for: (1) working Flask/Express routes with real business logic, (2) live market data connections with evidence, (3) production-ready modules. Report EXACTLY what works and what is slop. Be brutally honest. Output a markdown report."
        task_type = "research"
        context = "This is the TIBIN Terminal — a quant trading platform. It claims live market data, bot execution, and multi-provider data aggregation. Verify these claims."
    },
    @{
        task = "Build a production-grade health check endpoint for the Jules Bridge that tests: (1) all configured API keys are valid by making real test calls, (2) GCP VM reachability, (3) disk space, (4) memory pressure. Return a /health/deep endpoint with evidence-backed status for each check. Write complete Python code."
        task_type = "build"
        context = "Jules Bridge is a Flask app at port 5000 with token auth (Bearer JULES-SECURE-999). Bridge code is in /modules/."
    },
    @{
        task = "Research the top 5 free-tier compute resources available in 2025 for running AI agents 24/7. For each: provider name, free tier limits, how to sign up, what API keys are needed, estimated compute hours per month free. Output a markdown table. Focus on: Oracle Cloud Free Tier (Always Free), Hugging Face Spaces, Railway.app, Render.com free tier, Fly.io free tier."
        task_type = "research"
        context = "We want to run autonomous AI workers 24/7 at zero cost. Already have GCP, Azure Student, and local machine."
    }
)

foreach ($t in $tasks) {
    Write-Host "  Sending: $($t.task.Substring(0, [Math]::Min(60, $t.task.Length)))..." -ForegroundColor Gray
    $r = Invoke-Bridge "POST" "/vm/task" $t
    Write-Host "  Result: $($r.status)" -ForegroundColor $(if ($r.ok) { "Green" } else { "Red" })
    Start-Sleep 2
}

# 4. Log to inbox
Write-Host "`n[4/4] Bootstrap complete. Results will appear in jules_inbox/vm_results.jsonl" -ForegroundColor Green
Write-Host "Monitor VM at: http://34.132.193.73:6000/status" -ForegroundColor Cyan
Write-Host "Dashboard: $(Resolve-Path 'C:\Users\abdul\.jules\dashboard.html')" -ForegroundColor Cyan

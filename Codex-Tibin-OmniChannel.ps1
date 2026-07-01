#Requires -Version 5.1
<#
.SYNOPSIS
  Tibin Codex Anti-Gravity Omni-Channel shell (v11)
.NOTES
  DO NOT paste this file backwards into PowerShell.
  Run:  c:\Users\abdul\.jules\Launch-Codex.cmd
  Or:   powershell -NoProfile -ExecutionPolicy Bypass -File "c:\Users\abdul\.jules\Codex-Tibin-OmniChannel.ps1"
#>

$ErrorActionPreference = "Continue"

# ========================= CONFIG =========================
$ProjectDir     = "C:\aotp\projects\OracleV5"
$ToolboxPath    = "$ProjectDir\Codex_Toolbox"
$EvidencePath   = "$ProjectDir\Codex_Evidence"
$GoogleOneDrive = "G:\My Drive\Tibin_Codex_Brain"
$CursorPath     = "$env:LOCALAPPDATA\Programs\cursor\Cursor.exe"
$JulesRoot      = "C:\Users\abdul\.jules"
$InboxDir       = "$JulesRoot\jules_inbox"
$BridgeUrl      = "http://127.0.0.1:5000"
$BridgeLauncher = "$JulesRoot\Run-JulesBridge.cmd"
$DeployScript   = "$ProjectDir\Tools\Deploy-OracleQuantowerStrategy.ps1"
$VerifyScript   = "$ProjectDir\Tools\Verify-OracleReplayReady.ps1"

# ========================= SETUP =========================
foreach ($p in @($ProjectDir, $ToolboxPath, $EvidencePath, $InboxDir)) {
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}
if ($GoogleOneDrive -match '^([A-Za-z]):\\') {
    $root = $Matches[1] + ':\'
    if ((Test-Path $root) -and -not (Test-Path $GoogleOneDrive)) {
        New-Item -ItemType Directory -Path $GoogleOneDrive -Force | Out-Null
    }
}
if (Test-Path $ProjectDir) { Set-Location $ProjectDir }

$script:ExitCodex   = $false
$script:TerminalLog = @()
$script:ChatLog     = @()
$global:McpStatus   = "STANDBY"
$global:SwarmState  = "IDLE"
$global:BridgeState = "OFFLINE"

$Directive = "SYSTEM DIRECTIVE: Tibin Codex Anti-Gravity. Tools: $ToolboxPath. Lake: $GoogleOneDrive. Oracle: $ProjectDir. Operator: Abdulwahab Tibin. Coordinate with Cursor Ultra."

# ========================= UI =========================
function Write-Log([string]$Msg) {
    $e = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Msg
    $script:TerminalLog += $e
    if ($script:TerminalLog.Count -gt 300) { $script:TerminalLog = $script:TerminalLog[-300..-1] }
}

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "  ================================================================================" -ForegroundColor Cyan
    Write-Host "   TIBIN CODEX  |  ANTI-GRAVITY OMNI-CHANNEL  v11" -ForegroundColor Cyan
    Write-Host "  ================================================================================" -ForegroundColor Cyan
    Write-Host "   MCP: $($global:McpStatus.PadRight(14))  SWARM: $($global:SwarmState.PadRight(8))  BRIDGE: $($global:BridgeState)" -ForegroundColor Green
    Write-Host "   Oracle V5  |  Jules/GPT-20x  |  Cursor  |  30TB G-One Lake" -ForegroundColor DarkGray
    Write-Host "  ================================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   1  Chat with Jules          6  MCP boot (force online)" -ForegroundColor Yellow
    Write-Host "   2  GPT-20x proxy             7  Open Cursor" -ForegroundColor Yellow
    Write-Host "   3  Swarm (5 agents)          8  Start Jules bridge" -ForegroundColor Yellow
    Write-Host "   4  Vault ingest file         9  Oracle status" -ForegroundColor Yellow
    Write-Host "   5  Lake sync file            0  Exit" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Type a number and follow the prompt.  OR type any message to chat." -ForegroundColor DarkGray
    Write-Host "   Commands: help  menu  log  history  inbox  oracle deploy  oracle verify" -ForegroundColor DarkGray
    Write-Host ""
}

function Read-CodexInput([string]$Prompt) {
    Write-Host $Prompt -NoNewline -ForegroundColor Yellow
    return (Read-Host)
}

# ========================= BRIDGE / JULES =========================
function Test-BridgeOnline {
    try {
        $r = Invoke-RestMethod -Uri "$BridgeUrl/ping" -Method Get -TimeoutSec 3
        if ($r.status) { $global:BridgeState = "ONLINE"; return $true }
    } catch { }
    $global:BridgeState = "OFFLINE"
    return $false
}

function Send-Jules([string]$Text, [int]$Parallel = 0) {
    Write-Log "SEND: $Text"

    if (Get-Command jules -ErrorAction SilentlyContinue) {
        try {
            if ($Parallel -gt 1) {
                & jules remote new --repo $ProjectDir --session $Text --parallel $Parallel 2>&1 | Out-Null
            } else {
                & jules remote new --repo $ProjectDir --session $Text 2>&1 | Out-Null
            }
            Write-Host "[+] Sent via Jules CLI." -ForegroundColor Green
            Write-Log "Jules CLI OK"
            return $true
        } catch {
            Write-Log "Jules CLI error: $($_.Exception.Message)"
        }
    }

    if (Test-BridgeOnline) {
        try {
            $body = @{
                file    = "JULES_RESPONSE.md"
                content = "## Codex`n`n$Text`n`n---`n$(Get-Date -Format u)"
            } | ConvertTo-Json
            Invoke-RestMethod -Uri "$BridgeUrl/inbox/write" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 10 | Out-Null
            Write-Host "[+] Sent via Jules bridge inbox." -ForegroundColor Green
            Write-Log "Bridge inbox OK"
            return $true
        } catch {
            Write-Log "Bridge write error: $($_.Exception.Message)"
        }
    }

    $out = Join-Path $InboxDir "CODEX_DIRECTIVE.md"
    @(
        "# CODEX DIRECTIVE",
        "",
        "**Time:** $(Get-Date -Format u)",
        "",
        $Text,
        ""
    ) | Set-Content -Path $out -Encoding UTF8
    Write-Host "[+] Saved locally: $out" -ForegroundColor Green
    Write-Log "Local inbox: $out"
    return $true
}

function Clean-Path([string]$p) {
    $p = $p.Trim().Trim('"').Trim("'")
    if ($p -match "^& '(.+)'$") { $p = $Matches[1] }
    return $p
}

# ========================= ACTIONS =========================
function Do-Chat([string]$Msg) {
    if ([string]::IsNullOrWhiteSpace($Msg)) { Write-Host "[-] Empty message." -ForegroundColor Red; return }
    $script:ChatLog += "YOU: $Msg"
    Write-Host "[*] Jules processing..." -ForegroundColor Cyan
    Send-Jules "$Directive`n`nUSER: $Msg" | Out-Null
    $script:ChatLog += "JULES: Request received."
}

function Do-Gpt([string]$Msg) {
    if ([string]::IsNullOrWhiteSpace($Msg)) { Write-Host "[-] Empty message." -ForegroundColor Red; return }
    $script:ChatLog += "GPT: $Msg"
    Write-Host "[+] GPT-20x logged to context." -ForegroundColor Green
}

function Do-Swarm([string]$Task) {
    if ([string]::IsNullOrWhiteSpace($Task)) { Write-Host "[-] Empty task." -ForegroundColor Red; return }
    $global:SwarmState = "ACTIVE"
    Write-Host "[*] Deploying 5-agent swarm..." -ForegroundColor Yellow
    Send-Jules "$Directive`n`nSWARM: $Task" -Parallel 5 | Out-Null
    Show-Menu
}

function Do-Vault([string]$Path) {
    $Path = Clean-Path $Path
    if (-not (Test-Path $Path)) { Write-Host "[-] Not found: $Path" -ForegroundColor Red; return }
    Copy-Item $Path $ToolboxPath -Force
    Copy-Item $Path $EvidencePath -Force
    Send-Jules "VAULT: ingested $Path" | Out-Null
    Write-Host "[+] Vault + evidence updated." -ForegroundColor Green
}

function Do-Lake([string]$Path) {
    $Path = Clean-Path $Path
    if (-not (Test-Path $Path)) { Write-Host "[-] Not found: $Path" -ForegroundColor Red; return }
    if (-not (Test-Path $GoogleOneDrive)) {
        Write-Host "[-] G: lake not mounted. Skipping copy." -ForegroundColor Red
        return
    }
    Copy-Item $Path $GoogleOneDrive -Recurse -Force
    Send-Jules "LAKE: synced $Path" | Out-Null
    Write-Host "[+] Lake sync done." -ForegroundColor Green
}

function Do-Mcp {
    $global:McpStatus = "ONLINE"
    Send-Jules "SYSTEM: MCP bridges online." | Out-Null
    Write-Host "[+] MCP status: ONLINE" -ForegroundColor Green
    Show-Menu
}

function Do-Cursor {
    if (Test-Path $CursorPath) {
        Start-Process $CursorPath -ArgumentList "`"$JulesRoot`"", "`"$ProjectDir`""
    } else {
        Start-Process cmd.exe -ArgumentList "/c cursor `"$ProjectDir`""
    }
    Write-Host "[+] Cursor launched." -ForegroundColor Green
}

function Do-Bridge {
    if (Test-BridgeOnline) {
        Write-Host "[+] Bridge already online: $BridgeUrl" -ForegroundColor Green
        return
    }
    if (-not (Test-Path $BridgeLauncher)) {
        Write-Host "[-] Missing: $BridgeLauncher" -ForegroundColor Red
        return
    }
    Start-Process cmd.exe -ArgumentList "/c start `"Jules Bridge`" `"$BridgeLauncher`""
    Write-Host "[*] Bridge window opening... wait 5 sec then type 9 to verify." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Test-BridgeOnline | Out-Null
    Show-Menu
}

function Do-Oracle([string]$Action) {
    $Action = if ($Action) { $Action.ToLower() } else { "status" }

    if ($Action -eq "status") {
        if (Test-BridgeOnline) {
            try {
                $d = Invoke-RestMethod -Uri "$BridgeUrl/oracle/status" -Method Get -TimeoutSec 20
                Write-Host ($d | ConvertTo-Json -Depth 5) -ForegroundColor Cyan
                return
            } catch { }
        }
        Write-Host "  Repo:   $(Test-Path $ProjectDir)" -ForegroundColor Cyan
        Write-Host "  Deploy: $(Test-Path $DeployScript)" -ForegroundColor Cyan
        Write-Host "  Verify: $(Test-Path $VerifyScript)" -ForegroundColor Cyan
        Write-Host "  DLL:    $(Test-Path 'C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll')" -ForegroundColor Cyan
        return
    }

    if ($Action -eq "deploy") {
        Push-Location $ProjectDir
        dotnet build OracleV5.Strategy\OracleV5.Strategy.csproj -c Release -a x64
        & $DeployScript
        Pop-Location
        Write-Host "[+] Deploy finished." -ForegroundColor Green
        return
    }

    if ($Action -eq "verify") {
        & $VerifyScript
        return
    }

    Write-Host "[-] Use: oracle status | deploy | verify" -ForegroundColor Red
}

function Do-Inbox([string]$File) {
    $File = if ($File) { $File } else { "OPERATOR_RESPONSE.md" }
    if (Test-BridgeOnline) {
        try {
            $body = @{ file = $File } | ConvertTo-Json
            $r = Invoke-RestMethod -Uri "$BridgeUrl/inbox/read" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 10
            if ($r.content) { Write-Host $r.content; return }
        } catch { }
    }
    $local = Join-Path $InboxDir $File
    if (Test-Path $local) { Get-Content $local -Raw | Write-Host }
    else { Write-Host "[-] Not found: $File" -ForegroundColor Red }
}

function Show-Log {
    Write-Host "`n--- TERMINAL LOG ---" -ForegroundColor Yellow
    $script:TerminalLog | Select-Object -Last 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
}

function Show-History {
    Write-Host "`n--- CHAT ---" -ForegroundColor Yellow
    $script:ChatLog | Select-Object -Last 15 | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }
}

# ========================= COMMAND ROUTER =========================
function Invoke-CodexLine([string]$Line) {
    $Line = $Line.Trim()
    if (-not $Line) { return }

    # bare Windows path -> vault
    if ($Line -match '^[A-Za-z]:\\' -and ($Line -notmatch '\s')) {
        Do-Vault $Line
        return
    }

    # number only -> interactive prompt (THIS IS HOW IT IS SUPPOSED TO WORK)
    if ($Line -match '^\d$') {
        switch ($Line) {
            "1" { Do-Chat (Read-CodexInput "  Your message: "); return }
            "2" { Do-Gpt  (Read-CodexInput "  GPT question: "); return }
            "3" { Do-Swarm (Read-CodexInput "  Swarm task: "); return }
            "4" { Do-Vault (Read-CodexInput "  File path (drag-drop OK): "); return }
            "5" { Do-Lake  (Read-CodexInput "  File path (drag-drop OK): "); return }
            "6" { Do-Mcp; return }
            "7" { Do-Cursor; return }
            "8" { Do-Bridge; return }
            "9" { Do-Oracle "status"; return }
            "0" { $script:ExitCodex = $true; Write-Host "[*] Goodbye." -ForegroundColor Cyan; return }
        }
    }

    # number + text on same line: 1 hello
    if ($Line -match '^(\d)\s+(.+)$') {
        $n = $Matches[1]; $t = $Matches[2].Trim().Trim('"')
        switch ($n) {
            "1" { Do-Chat $t; return }
            "2" { Do-Gpt $t; return }
            "3" { Do-Swarm $t; return }
            "4" { Do-Vault $t; return }
            "5" { Do-Lake $t; return }
        }
    }

    $tok = $Line -split '\s+', 2
    $cmd = $tok[0].ToLower()
    $arg = if ($tok.Count -gt 1) { $tok[1].Trim().Trim('"') } else { "" }

    switch ($cmd) {
        "help"  { Show-Menu }
        "menu"  { Show-Menu }
        "clear" { Show-Menu }
        "log"   { Show-Log }
        "history" { Show-History }
        "exit"  { $script:ExitCodex = $true }
        "chat"  { Do-Chat $arg }
        "gpt"   { Do-Gpt $arg }
        "swarm" { Do-Swarm $arg }
        "vault" { Do-Vault $arg }
        "lake"  { Do-Lake $arg }
        "mcp"   { Do-Mcp }
        "cursor"{ Do-Cursor }
        "bridge"{ Do-Bridge }
        "inbox" {
            if ($arg -match '^read\s+(.+)$') { Do-Inbox $Matches[1] }
            else { Do-Inbox $arg }
        }
        "oracle" { Do-Oracle $arg }
        default  { Do-Chat $Line }
    }
}

# ========================= BOOT =========================
Write-Host "[+] Tibin Codex v11 starting..." -ForegroundColor DarkCyan
Write-Log "Boot"
Test-BridgeOnline | Out-Null
Show-Menu

while (-not $script:ExitCodex) {
    Write-Host "Codex> " -NoNewline -ForegroundColor Cyan
    try {
        $line = Read-Host
        Write-Host ""
        Invoke-CodexLine $line
        Write-Host ""
    } catch {
        Write-Host "[!] $($_.Exception.Message)" -ForegroundColor Red
        Write-Log "ERR: $($_.Exception.Message)"
    }
}

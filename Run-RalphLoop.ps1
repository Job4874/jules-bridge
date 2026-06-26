<#
.SYNOPSIS
    Run-RalphLoop.ps1 — The Jules Bridge Ralph Loop runner.
    
.DESCRIPTION
    A Ralph Loop (named after Ralph Wiggum, The Simpsons) is a self-correcting,
    ticket-driven agentic loop. This script runs Claude Code repeatedly, each time
    using the ralph-loop skill to pick and implement the next most important ticket.
    
    Based on the workshop by Chris Parsons:
    "The dumbest Ralph Loop is literally just a while loop and it goes through
    and implements stuff — super, super easy."

.PARAMETER MaxIterations
    Maximum number of loop iterations before stopping. Default: 999 (effectively infinite).
    
.PARAMETER SleepBetweenSeconds
    Seconds to wait between iterations. Default: 2.
    
.PARAMETER DryRun
    If set, prints what would run without actually running Claude.

.EXAMPLE
    .\Run-RalphLoop.ps1
    .\Run-RalphLoop.ps1 -MaxIterations 5
    .\Run-RalphLoop.ps1 -DryRun

.NOTES
    Requirements:
    - Claude Code CLI installed and authenticated
    - Run from the jules-bridge project root (c:\Users\abdul\.jules\)
    - GEMINI_API_KEY set in environment for reasoning module
#>

param(
    [int]$MaxIterations = 999,
    [int]$SleepBetweenSeconds = 2,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# ── Config ────────────────────────────────────────────────────────────────────

$ProjectRoot = $PSScriptRoot
$TicketsDir  = Join-Path $ProjectRoot "doc\tickets"
$LogFile     = Join-Path $ProjectRoot "ralph_loop.log"
$InboxDir    = Join-Path $ProjectRoot "jules_inbox"

# The prompt Claude gets each iteration.
# Principle (from workshop): keep it short — the skill file does the heavy lifting.
$LoopPrompt = @"
Use the ralph-loop skill from .agents/skills/ralph-loop/SKILL.md to implement the
next most important ticket from doc/tickets/. Follow the skill exactly:
load context, pick ticket, TDD, run tests, record evidence, commit, mark done, stop.
"@

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Get-PendingTicketCount {
    if (-not (Test-Path $TicketsDir)) { return 0 }
    $tickets = Get-ChildItem -Path $TicketsDir -Filter "*.md"
    $pending = $tickets | Where-Object {
        $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
        $content -notmatch "\*\*Status\*\*:\s*DONE"
    }
    return ($pending | Measure-Object).Count
}

function Test-InboxHasStop {
    # Check if a human wrote a STOP message into the inbox
    if (-not (Test-Path $InboxDir)) { return $false }
    $msgs = Get-ChildItem -Path $InboxDir -Filter "*.md" | Sort-Object LastWriteTime -Descending
    foreach ($msg in $msgs) {
        $content = Get-Content $msg.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "RALPH_STOP|ralph_stop|STOP_LOOP") {
            Write-Log "Inbox STOP signal detected in: $($msg.Name)" "WARN"
            return $true
        }
    }
    return $false
}

# ── Pre-flight checks ─────────────────────────────────────────────────────────

Write-Log "=== Ralph Loop starting ==="
Write-Log "Project root: $ProjectRoot"
Write-Log "Tickets dir:  $TicketsDir"
Write-Log "Max iterations: $MaxIterations"
Write-Log "Dry run: $DryRun"

if (-not (Test-Path $TicketsDir)) {
    Write-Log "Tickets directory not found: $TicketsDir" "ERROR"
    Write-Log "Create doc/tickets/ and add at least one ticket before running the loop." "ERROR"
    exit 1
}

$pending = Get-PendingTicketCount
Write-Log "Pending tickets at start: $pending"

if ($pending -eq 0) {
    Write-Log "No pending tickets — nothing to do. Add tickets to doc/tickets/ first." "WARN"
    exit 0
}

# ── The Loop ──────────────────────────────────────────────────────────────────

$iteration = 0
$startTime = Get-Date

while ($iteration -lt $MaxIterations) {
    $iteration++
    $elapsed = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
    Write-Log "--- Iteration $iteration (elapsed: ${elapsed}m) ---"

    # Check for human STOP signal in inbox
    if (Test-InboxHasStop) {
        Write-Log "Human STOP signal received. Exiting loop." "WARN"
        break
    }

    # Check pending ticket count
    $pending = Get-PendingTicketCount
    Write-Log "Pending tickets: $pending"

    if ($pending -eq 0) {
        Write-Log "All tickets complete! Loop finished naturally." "INFO"
        break
    }

    # Run Claude
    if ($DryRun) {
        Write-Log "[DRY RUN] Would run: claude -p `"$LoopPrompt`"" "INFO"
    }
    else {
        Write-Log "Launching Claude (iteration $iteration)..."
        
        try {
            # Run claude with the ralph-loop prompt.
            # --dangerously-skip-permissions: required for autonomous loop (no interactive prompts)
            # Redirect output so we can log it.
            $claudeOutput = claude --dangerously-skip-permissions -p $LoopPrompt 2>&1
            $exitCode = $LASTEXITCODE
            
            Write-Log "Claude exited with code: $exitCode"
            
            # Log the first 500 chars of output for debugging
            if ($claudeOutput) {
                $preview = ($claudeOutput | Out-String).Substring(0, [Math]::Min(500, ($claudeOutput | Out-String).Length))
                Write-Log "Claude output preview: $preview"
            }
            
            if ($exitCode -ne 0) {
                Write-Log "Claude returned non-zero exit code $exitCode — may indicate an error." "WARN"
            }
        }
        catch {
            Write-Log "Exception running Claude: $_" "ERROR"
            Write-Log "Is 'claude' installed and on PATH? Run: claude --version" "ERROR"
            break
        }
    }

    # Brief pause between iterations
    if ($SleepBetweenSeconds -gt 0) {
        Write-Log "Waiting ${SleepBetweenSeconds}s before next iteration..."
        Start-Sleep -Seconds $SleepBetweenSeconds
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────

$elapsed = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
$remaining = Get-PendingTicketCount
Write-Log "=== Ralph Loop ended ==="
Write-Log "Iterations run: $iteration"
Write-Log "Elapsed time:   ${elapsed}m"
Write-Log "Tickets remaining: $remaining"
Write-Log "Log file: $LogFile"

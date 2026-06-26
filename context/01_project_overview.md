# Jules Bridge — Project Overview

> Context file 1 of 7. Read before writing any code.
> Part of the seven-file context system (Ghost AI / spec-driven development approach).

## What Is Jules Bridge?

Jules Bridge is a self-improving agentic harness for orchestrating AI coding agents (Jules, Claude, Codex) alongside live trading infrastructure (Quantower + Oracle V5).

It is an HTTP API that runs locally on Windows and exposes structured, typed endpoints for:
- File system operations (read, write, grep, tail)
- Shell execution (PowerShell, cmd)
- UI automation (screenshot, click, type)
- Inbox message passing (agent ↔ human communication)
- Oracle V5 / Quantower health and deployment
- Hierarchical reasoning (HRM-inspired H/L/ACT)
- Retrospective analysis (self-improving memory)

## Goals

1. **Zero setup per session** — agents load memory files and immediately know the codebase state
2. **Evidence over trust** — all work is cryptographically proved (SHA-256 test hashes, screenshots, recordings)
3. **Every failure is a harness bug** — retrospective module reads logs and writes learnings to memory
4. **Deep modules** — simple typed interface hides complex implementation (Matt Pocco principle)
5. **Guide, don't prescribe** — gotchas file (553-line style), not 10,000 lines of docs
6. **CDLC compliant** — generate context → evaluate with evals → distribute as skills → observe via retrospective

## Core User Flow

```
Session start
  → GET /retrospective/memory?domain=general    (load what went wrong before)
  → GET /oracle/status                           (understand current system state)
  → ... do work using modules ...
  → python -m pytest tests/ -v                   (run tests)
  → POST /retrospective/record_evidence          (prove tests ran: SHA-256)
  → POST /retrospective/analyze                  (extract learnings → write to memory)
Session end
```

## Deliberate Out of Scope

- No database (memory is markdown files, not SQL)
- No authentication (runs locally, firewall-protected)
- No frontend UI (pure HTTP API + inbox markdown files)
- No cloud deployment (Quantower is a desktop app — must run on same machine)
- No LLM calls in the bridge itself (reasoning_module has LLM stubs — swap in at integration layer)

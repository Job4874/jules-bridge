# Jules Bridge — Architecture

> Context file 2 of 7. Defines module map, invariants, and boundaries.

## Module Map

```text
bridge.py                   ← Thin HTTP routing only. NO business logic.
├── modules/
│   ├── __init__.py         ← Package exports (single public API surface)
│   ├── fs_service.py       ← File read/write/grep/tail/list_dir
│   ├── shell_executor.py   ← PowerShell/cmd execution with timeout
│   ├── ui_automation.py    ← Screenshot/click/type, guarded secrets, UI state detection
│   ├── human_mimic_driver.py ← H/L/ACT UI driver loops built from ui_automation primitives
│   ├── vm_manager.py      ← CPU/memory pressure and dry-run-first VM boot gating
│   ├── inbox_service.py    ← Message files in jules_inbox/ dir
│   ├── oracle_session.py   ← Oracle V5 + Quantower health/build/deploy
│   ├── reasoning_module.py ← HRM-inspired H/L/ACT hierarchical reasoning
│   ├── retrospective_module.py ← Log analysis, memory writes, test evidence
│   ├── jules_orchestrator.py ← Jules task packets, launch state, remote session checks
│   └── akc_module.py       ← Agent Knowledge Context checkpoints from source files
├── memory/                 ← Per-domain markdown memory files
│   ├── general.md          ← General harness learnings
│   ├── oracle.md           ← Oracle V5 / Quantower specific
│   ├── quantower.md        ← Quantower UI / connection patterns
│   ├── trading.md          ← Trading domain concepts
│   └── reasoning.md        ← Reasoning module learnings
├── context/                ← Seven-file context system (this directory)
├── tests/                  ← pytest test suite
│   ├── test_fs_service.py
│   ├── test_shell_executor.py
│   ├── test_inbox_service.py
│   ├── test_reasoning_module.py
│   └── test_retrospective_module.py
└── jules_inbox/            ← Inbox message drop files
```

## Layer Boundaries (Invariants — NEVER break these)

1. **bridge.py routes are ONLY**: validate → call module → return JSON
2. **Modules NEVER import from bridge.py** (one-way dependency)
3. **All public module functions NEVER raise** — they return typed dicts or dataclasses with partial data on failure
4. **No bare strings for paths** — always use `os.path.join` or `pathlib.Path`
5. **No hardcoded credentials** — always from `os.environ.get()`
6. **Memory files are markdown** — not JSON, not SQL, not YAML (markdown is human-readable and agent-parseable)

## Route Namespace Map

| Prefix | Module | Purpose |
| -------- | -------- | --------- |
| `/health` | bridge.py | Liveness + uptime — no module backing |
| `/fs/` | fs_service | File system operations |
| `/shell/` | shell_executor | Command execution |
| `/ui/` | ui_automation + human_mimic_driver | Screenshot, click, type, UI detection, and guarded Human-Mimic ACT loops |
| `/vm/` | vm_manager | Resource pressure checks and allowlisted secondary-VM boot dry-runs |
| `/inbox/` | inbox_service | Message passing |
| `/jules/` | jules_orchestrator | Jules task dispatch, worker packets, launch state, and remote session checks |
| `/oracle/` | oracle_session | Oracle V5 + Quantower |
| `/reasoning/` | reasoning_module | H/L/ACT reasoning (Gemini or stub) |
| `/retrospective/` | retrospective_module | Log analysis + memory + pruning |
| `/akc/` | akc_module | Agent Knowledge Context source inventory, checkpoint loading, and readiness gating |
| `/notify/` | notify_email | Email notifications |

## Key Design Patterns

### Deep Module Pattern (Matt Pocco)

Every module has a **simple typed interface** hiding complex implementation:

- `oracle_status()` → one call returns full health snapshot (hides XML parsing, PS invocation, DLL hashing)
- `reason(problem)` → one call runs full H/L/ACT cycle (hides LLM calls, halting logic)
- `analyze_session()` → one call reads logs, detects patterns, writes memory (hides regex, file I/O, pattern matching)
- `build_akc_context(source_paths)` → one call reads sources, masks paths, hashes files, extracts operating rules, and writes a checkpoint
- `check_akc_readiness()` → one call verifies the checkpoint exists, is `ready`, and contains required operating rules before session start
- `boot_secondary_vm(script_name)` → one call validates allowlisted VM boot scripts and defaults to dry-run

### Evidence-Based Verification (Nick Ni)

- Tests: `record_test_evidence(output)` → stores SHA-256 hash
- Oracle evidence gate: soft stale-evidence warning by default; `EVIDENCE_GATE_HARD=1` preempts stale `/oracle/*` route execution with HTTP 423
- Memory GC: `analyze_session(auto_prune=True)` writes current learnings first, then runs `prune_memory()`
- UI: screenshots attached to evidence (via `/ui/screenshot`)
- Builds: build output tails stored in `BuildDeployResult`

### CDLC (Patrick Debois)

- Generate: AGENTS.md, context/ files, ubiquitous language
- Evaluate: `hrm_context_eval.py`, pytest suite, `tests/eval_reasoning.py`
- Distribute: skills in `.agents/skills/`

### Context Sub-Agent Planning

- `modules/context_orchestrator.py` builds smart-truncated source capsules and
  role-specific context packets without launching workers.
- `POST /akc/subagents` accepts inline `content` or explicit `source_paths`,
  keeps source heads/tails in active context, hashes omitted middles, and reports
  context metrics for budget checks.
- Omitted middles are indexed in `context_memory_store` and
  `CONTEXT_MEMORY_STORE.json` as retrieval refs and hashes, not copied into every
  packet. This keeps the parent prompt lean while preserving a retrieval path.
- It also emits a spec-first no-slop workflow: `research -> plan -> implement`,
  review gates before code, and a context-utilization target that defaults to
  40% of a 170k-character window.
- `long_session_eval_plan` and `CONTEXT_QUALITY_EVAL.md` use the 10-turn
  preload / 11th-turn probe pattern to catch late context loss.
- `write_packets=true` writes markdown packets under
  `jules_inbox/context_subagents/` plus `NO_SLOP_WORKFLOW.md`,
  `CONTEXT_MEMORY_STORE.json`, and `CONTEXT_QUALITY_EVAL.md`; it never calls
  `jules new`.
- Keep this distinct from `/jules/dispatch`: AKC subagents handle source
  context, Jules dispatch handles executable Jules task cards.

### Performance & Stability Patterns

- **Per-Route Circuit Breaker**: Middleware in `bridge.py` tracks call frequency and returns 429 when thresholds are exceeded, preventing status-check doom loops.
- **Selective Result Caching**: High-latency idempotent routes (`/shell`, `/jules/sessions`, `/dashboard/status`) use TTL-based in-memory caching to protect the event loop.
- **Bypass Gates**: Critical state-dependent operations can bypass caches via `bypass_cache=true` to ensure they always operate on ground truth.

### Jules Dispatch

- `modules/jules_orchestrator.py` parses pasted Jules task dumps, classifies task
  cards by status/type, and builds worker packets plus explicit launch commands.
- `POST /jules/dispatch` is dry-run by default. It can write packet files under
  `jules_inbox/jules_dispatch/`, but it never starts remote Jules sessions.
- `POST /jules/launch` is also dry-run by default. With `dry_run=false`, it
  launches prepared packet files through the Jules CLI, writes
  `JULES_LAUNCH_STATE.json`, and records stdout/stderr/session ids per packet.
  Packet input is piped as UTF-8 so Windows console code pages cannot corrupt
  emoji or other non-ASCII packet text. Repeated launches can skip packets
  already marked `launched` and merge state so the COT ledger remains cumulative.
  Speculative duplicate launches can preserve older session ids so COT can pull
  whichever duplicate finishes first.
- `POST /jules/preflight` diagnoses the local Jules CLI before launch. It
  prefers the direct `npm\bin\jules.exe` binary for bare `jules` commands,
  checks `jules version`, optionally checks `jules remote list --session`, and
  writes `JULES_PREFLIGHT.json`.
- `POST /jules/sessions` lists remote Jules sessions through
  `jules remote list --session`; live calls use timeout-protected process-tree
  cleanup so a blocked npm shim does not leave `node`/`jules.exe` children.
- `POST /jules/pull` is dry-run by default. With `dry_run=false`, it runs
  `jules remote pull --session <id>` and stores pull stdout/stderr JSON under
  `jules_inbox/jules_dispatch/JULES_REMOTE_PULLS/`.
- `POST /jules/cot` builds `JULES_COT_LEDGER.md` and JSON from packet launch
  state plus pulled completion reports. It tracks completion-of-task evidence
  summaries only; it never requests private chain-of-thought.
- `POST /jules/cycle` composes dispatch, remote readiness, gated launch, pull,
  and COT ledger refresh into one dry-run-first communication cycle. Live launch
  stays disabled when remote listing times out and `require_remote_ready=true`.
- `POST /jules/watch` repeatedly runs pull-only cycles inside a bounded watch
  window, pulls completed sessions, refreshes the COT ledger, and writes
  `JULES_WATCH_STATE.json`. It reports `Awaiting Plan`/`Awaiting User` rows as
  attention-required because the current Jules CLI does not expose plan approval.
- `POST /jules/fleet` maintains a larger Jules worker queue, pulls completed
  launched sessions, counts active remote sessions, and launches only the next
  unlaunched packets that fit inside `max_concurrent` and `launch_batch_size`.
  It is dry-run by default and writes `JULES_FLEET_STATE.json`. Failed rows,
  stale blank/unknown rows, and `Awaiting Plan` rows are retried by replacing
  the tracked packet session id when capacity is available.
- `POST /jules/fleet-watch` repeatedly runs the fleet cycle in a bounded loop,
  so completed sessions are pulled, COT is refreshed, and newly freed capacity
  is filled without manually alternating fleet and watch calls. It writes
  `JULES_FLEET_WATCH_STATE.json`.
- Observe: `retrospective_module.py` reads logs → writes memory

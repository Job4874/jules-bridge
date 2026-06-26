# Jules Bridge — Architecture

> Context file 2 of 6. Defines module map, invariants, and boundaries.

## Module Map

```
bridge.py                   ← Thin HTTP routing only. NO business logic.
├── modules/
│   ├── __init__.py         ← Package exports (single public API surface)
│   ├── fs_service.py       ← File read/write/grep/tail/list_dir
│   ├── shell_executor.py   ← PowerShell/cmd execution with timeout
│   ├── ui_automation.py    ← Screenshot/click/type via pyautogui
│   ├── inbox_service.py    ← Message files in jules_inbox/ dir
│   ├── oracle_session.py   ← Oracle V5 + Quantower health/build/deploy
│   ├── reasoning_module.py ← HRM-inspired H/L/ACT hierarchical reasoning
│   └── retrospective_module.py ← Log analysis, memory writes, test evidence
├── memory/                 ← Per-domain markdown memory files
│   ├── general.md          ← General harness learnings
│   ├── oracle.md           ← Oracle V5 / Quantower specific
│   ├── quantower.md        ← Quantower UI / connection patterns
│   ├── trading.md          ← Trading domain concepts
│   └── reasoning.md        ← Reasoning module learnings
├── context/                ← Six-file context system (this directory)
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
|--------|--------|---------|
| `/fs/` | fs_service | File system operations |
| `/shell/` | shell_executor | Command execution |
| `/ui/` | ui_automation | Screenshot and click |
| `/inbox/` | inbox_service | Message passing |
| `/oracle/` | oracle_session | Oracle V5 + Quantower |
| `/reasoning/` | reasoning_module | H/L/ACT reasoning |
| `/retrospective/` | retrospective_module | Log analysis + memory |
| `/notify/` | notify_email | Email notifications |

## Key Design Patterns

### Deep Module Pattern (Matt Pocco)
Every module has a **simple typed interface** hiding complex implementation:
- `oracle_status()` → one call returns full health snapshot (hides XML parsing, PS invocation, DLL hashing)
- `reason(problem)` → one call runs full H/L/ACT cycle (hides LLM calls, halting logic)
- `analyze_session()` → one call reads logs, detects patterns, writes memory (hides regex, file I/O, pattern matching)

### Evidence-Based Verification (Nick Ni)
- Tests: `record_test_evidence(output)` → stores SHA-256 hash
- UI: screenshots attached to evidence (via `/ui/screenshot`)
- Builds: build output tails stored in `BuildDeployResult`

### CDLC (Patrick Debois)
- Generate: AGENTS.md, context/ files, ubiquitous language
- Evaluate: `hrm_context_eval.py`, pytest suite
- Distribute: skills in `.agents/skills/`
- Observe: `retrospective_module.py` reads logs → writes memory

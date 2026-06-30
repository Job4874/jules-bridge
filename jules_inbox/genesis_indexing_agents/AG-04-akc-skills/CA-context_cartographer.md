# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 04: AKC subagent and local skill system map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 7
- active_prompt_chars: 11761
- omitted_middle_chars: 52050
- compression_ratio: 0.1835

## No Slop Workflow
- mode: spec_first
- compaction_required: False
- phases: research -> plan -> implement
- gates: review research before plan; review plan before code; record evidence before done

## Context Handling Policy
- active_context: source head/tail excerpts only
- memory_store: head_tail_active_context_middle_memory_refs (7 refs)
- retrieve omitted middles before assuming missing details are irrelevant
- subagent_boundary: keep heavy source analysis inside role packets
- long_session_eval: preload 10 turns; probe turn 11
## Operating Rules
- Keep the main conversation light; do heavy source analysis inside this packet.
- Use source fingerprints and path refs for retrieval; do not assume omitted middle content is irrelevant.
- Preserve head/tail evidence and ask for retrieval only when the missing middle is necessary.
- Do not reveal private chain-of-thought. Return concise rationale, decisions, and evidence.

## Deliverables
- source inventory
- operating rules
- missing or risky source notes

## Source Capsules

### akc_module.py
- path_ref: path-ref:26cf320da283
- sha256: 2f8d29c91896c28904a5c56fa7b48338dcd218126033066d2fb867cc6546ab25
- chars: 15282
- omitted_middle_chars: 12882
- omitted_middle_sha256: 115da863fbb674e096eb65934196b2de10f9d56c74372f163f1fc00a0f17490a
- signals: context_engineering, smart_truncation, tdd, evidence, hrm

Head:
```text
"""Agent Knowledge Context checkpoint module.

AKC turns source material such as transcripts, project context, and notes into
a compact, source-backed checkpoint that agents can load before daily work.

Public interface:
    build_akc_context(source_paths, checkpoint_path) -> AKCContext
    load_akc_checkpoint(checkpoint_path) -> AKCCheckpoint
    check_akc_readiness(checkpoint_path, required_rules) -> AKCReadiness
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class AKCCont
...[truncated]
```

Tail:
```text
"
    rules_ready = not missing_rules
    ready = exists and status_ready and rules_ready

    if ready:
        status = "ready"
    elif not exists or checkpoint_status == "blocked":
        status = "blocked"
    else:
        status = "partial"

    gates = [
        _gate(
            "checkpoint_exists",
            exists,
            "present" if exists else "checkpoint file is missing",
        ),
        _gate(
            "checkpoint_ready",
            exists and status_ready,
            f"status={checkpoint_status}",
        ),
        _gate(
            "required_rules_present",
            rules_ready,
            "all present" if rules_ready else "missing: " + ", ".join(missing_rules),
        ),
    ]

    return AKCReadiness({
        "status": status,
        "ready": r
...[truncated]
```

### context_orchestrator.py
- path_ref: path-ref:bd51e6ae3281
- sha256: ec7e2e97607117f9152204844a8c5349539e71421aef520283963874e80a18e5
- chars: 35791
- omitted_middle_chars: 33391
- omitted_middle_sha256: a340104739a504c3e3bef7d788904be27e4d1a055813de5e79b8dfd81a2bc9eb
- signals: context_engineering, smart_truncation, memory_store, subagents, long_session_evals, tdd, evidence, hrm

Head:
```text
"""Context sub-agent planning.

This module turns large source material into budgeted context capsules and
role-specific sub-agent packets. It keeps the main conversation small while
preserving enough head/tail evidence and source fingerprints for follow-up
retrieval.

Public interface:
    build_context_subagents(...) -> ContextSubagentPlan
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class ContextSource(dict):
    """A source inventory row with redacted path metadata."""


class Conte
...[truncated]
```

Tail:
```text
    f"| {source.get('name', '')} | {source.get('path_ref', '')} | "
            f"{source.get('readable', False)} | {source.get('char_count', 0)} | {sha} |"
        )
    lines.extend([
        "",
        "## Sub-Agents",
        "",
        "| id | role | mission | packet |",
        "|---|---|---|---|",
    ])
    packet_by_id = {
        Path(path).stem: path
        for path in packet_files
    }
    for subagent in subagents:
        packet = packet_by_id.get(str(subagent.get("id", "")), "")
        lines.append(
            f"| {subagent.get('id', '')} | {subagent.get('role_id', '')} | {str(subagent.get('mission', '')).replace('|', '\\|')} | {packet.replace('|', '\\|')} |"
        )
    lines.extend([
        "",
        "COT here means completion-of-task evidence summaries, not pri
...[truncated]
```

### AGENTS.md
- path_ref: path-ref:b054f06f1c9e
- sha256: 83cc050b2c03ceab9aba01de7dbfad5de67ab3f5dff428e9b024c38011d89b65
- chars: 8177
- omitted_middle_chars: 5777
- omitted_middle_sha256: e362fd4b8884606bd88d544c28fe8d06afe1cdbe2b829e43537af1568b354d73
- signals: smart_truncation, evidence

Head:
```text
# Jules Bridge — Agent Instructions

> This file is auto-discovered by all AI agents (Codex, Claude, Gemini, Cursor, etc.).
> It is the single source of truth for how agents work with this codebase.

## Context Loading Order

Before any implementation, read these files **in this exact order**:

1. `context/01_project_overview.md` — what Jules Bridge is, goals, core user flow, out of scope
2. `context/02_architecture.md` — module map, layer boundaries, route namespace, design patterns
3. `context/03_code_standards.md` — Python conventions, naming, error handling, templates
4. `context/04_ai_workflow_rules.md` — session protocol, scope discipline, evidence rules, decision protocol
5. `context/05_gotchas.md` — module-level landmines, Windows-specific traps, edge cases
6. `context/06_progress_
...[truncated]
```

Tail:
```text
0`). Verify with `curl http://127.0.0.1:5000/health`.
- **Do NOT use `start.py` in cloud.** It wraps `bridge.py` with a pyngrok tunnel bound to a reserved domain (`parade-marrow-pulp.ngrok-free.dev`) that needs an ngrok authtoken; the tunnel step fails here. It does fall back to local-only mode, but running `bridge.py` directly is cleaner.
- **Tests:** `python3 -m pytest tests/ -v` (240 passing). `pytest` is not in `requirements.txt`; the update script installs it.
- **`pyautogui` is headless-incompatible at call time.** It is lazily imported, so importing `modules`/`bridge.py` and running the server all work without a display. The `/ui/*` routes (screenshot/click/type) require an X display and will error in cloud — this is expected, not a regression.
- **Console scripts (`pytest`, `flask`
...[truncated]
```

### SKILL.md
- path_ref: path-ref:31329545867f
- sha256: 5116d515e3c67729d4de6497f633dbcea3e206328e056cfa1e574c02a4d916fd
- chars: 1466
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
---
name: architect
description: >
  Run before starting any complex feature, new module, or major change.
  Reads the project context files, interviews the user one question at a time to resolve design decisions,
  and produces a clear, structured implementation plan.
---

# Architect Skill

## Purpose

Prevent implementation drift, architectural misalignment, and wasted tokens by establishing a clear, agreed-upon technical plan before writing any code.

## Instructions

1. **Gather Context**:
   - Read all context files in the `context/` directory (`01_project_overview.md`, `02_architecture.md`, `03_code_standards.md`, etc.).
   - Inspect the codebase for relevant existing files or patterns.
2. **Conduct the Design Interview**:
   - Ask **one question at a time** in the chat. Do not list
...[truncated]
```

### SKILL.md
- path_ref: path-ref:8ca1a1dcc028
- sha256: 575061eb219e0f2a2a4dd1a4643cb0b201eff6e9a0ae5468ab3ce7aa36cc16ce
- chars: 1025
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
---
name: recover
description: >
  Run when a session is stuck, tests are failing repeatedly, or the agent is in a doom loop.
  Diagnoses the current failure mode and provides the correct remediation steps.
---

# Recover Skill

## Purpose

Halt agent spiraling and context pollution by diagnosing failures and returning to a clean, known-good baseline.

## Instructions

1. **Identify the Failure Mode**:
   - **Doom Loop**: The agent is making the same edit or running the same command repeatedly.
   - **Polluted Context**: The chat history is bloated with failed attempts and the model is guessing.
   - **Broken Assumption**: A fundamental assumption about an API or system interface was wrong.
2. **Diagnose and Prescribe**:
   - Check test outputs, compilation logs, or `bridge.log`.
   - Run
...[truncated]
```

### SKILL.md
- path_ref: path-ref:cf4d7a4287b8
- sha256: 381ea0400ba54f2615c8cb9686850e750df1371f1f50e2ed8997f739c81641af
- chars: 1212
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
---
name: review
description: >
  Run after completing any feature or file modification.
  Checks the implementation against the plan, verifies code standards, and surfaces potential bugs.
---

# Review Skill

## Purpose

Enforce quality, standards, and correctness without making automatic edits. Provides feedback categorized by severity.

## Instructions

1. **Compare Implementation against Plan**:
   - Check if all deliverables in the approved plan have been met.
   - Verify signatures match the spec.
2. **Check Code Standards**:
   - Review imports, type hints, docstrings, and architectural boundaries (e.g. components should not contain database logic, deep modules should expose simple surfaces).
3. **Run Checks**:
   - Compile code and run existing tests (`python -m pytest tests/ -v`).
...[truncated]
```

### SKILL.md
- path_ref: path-ref:af559f9340a5
- sha256: e28a3e55c804d2929ead2cf1479ef99d9135536cdfb2ab7e978ceb4d9d8779a8
- chars: 1153
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: smart_truncation

Head:
```text
---
name: remember
description: >
  Run at the end of every coding session.
  Synthesizes decisions made, patterns established, and progress completed during the session,
  and compresses them into a memory file in the `memory/` directory.
---

# Remember Skill

## Purpose

Ensure continuity across separate sessions. Instead of starting from scratch or re-explaining context, this skill preserves the history of decisions, gotchas, and architectural choices.

## Instructions

1. **Analyze the Session**:
   - Scan the git history or modified files to review changes made.
   - Scan the `bridge.log` or test outputs for errors or behavior solved.
2. **Synthesize Changes**:
   - Extract any new conventions, patterns, or library patterns discovered.
   - Document any resolved blockers.
3. **Write
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.

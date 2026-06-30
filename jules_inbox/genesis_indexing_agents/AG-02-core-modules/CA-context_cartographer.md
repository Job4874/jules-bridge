# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 02: Core deep module boundary map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 5
- active_prompt_chars: 11621
- omitted_middle_chars: 48199
- compression_ratio: 0.193

## No Slop Workflow
- mode: spec_first
- compaction_required: False
- phases: research -> plan -> implement
- gates: review research before plan; review plan before code; record evidence before done

## Context Handling Policy
- active_context: source head/tail excerpts only
- memory_store: head_tail_active_context_middle_memory_refs (5 refs)
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

### fs_service.py
- path_ref: path-ref:56cebebc6edb
- sha256: 9aef1ec97d6559aa51a4b241d0c1c5e6a1aea2441c13fabf223f213ea8d9ca27
- chars: 6112
- omitted_middle_chars: 3712
- omitted_middle_sha256: 19edfee25b7bc79fed35590304717a4f7f685f54b75450aab34d1c181b79b670
- signals: smart_truncation

Head:
```text
"""Filesystem deep module — read, write, tail, grep, list.

Simple typed interface hiding all filesystem complexity.
All path validation and error handling lives here; callers get
clean TypedDicts back.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class FSResult(dict):
    """TypedDict-style result for single-file operations.

    Keys always present:
      path (str): absolute path operated on
      content (str): file text content
      data (str): alias of content (legacy compat)
    Optional keys:
      offset (int): for
...[truncated]
```

Tail:
```text
       if len(matches) >= max_matches:
                    break

    return FSResult(path=path, pattern=pattern, matches=matches,
                    content="", data="")


def list_dir(path: str) -> list:
    """List files and folders under a directory path.

    Args:
        path: Absolute path to directory.

    Returns:
        Sorted list of ListEntry dicts (dirs first, then files alpha).

    Raises:
        FileNotFoundError: if path does not exist.
        NotADirectoryError: if path is not a directory.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such directory: {path}", path)
    if not os.path.isdir(path):
        raise NotADirectoryError(f"Path is not a directory: {path}", path)

    entries = []
    for name in os.listdir(path):
        full
...[truncated]
```

### shell_executor.py
- path_ref: path-ref:7f175dac0b08
- sha256: bf232686c43d6b0f9f2629899fb93da6ca9ca41b3f2caf86525564f75e38b384
- chars: 9537
- omitted_middle_chars: 7137
- omitted_middle_sha256: b18b79b5a494209a22dbba6e57efdea76e55bb06fc9314f7a6edfed71ba8892f
- signals: smart_truncation, evidence

Head:
```text
"""Shell executor deep module — powershell / cmd / bash routing.

Simple typed interface hiding shell discovery, arg construction,
subprocess management, and output coercion.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import hashlib
import logging
from typing import Optional

LOGGER = logging.getLogger("jules_bridge")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SUPPORTED_SHELLS = ("powershell", "cmd", "bash")

_BASH_CANDIDATES = (
    r"path-redacted Files\Git\bin\bash.exe",
    r"path-redacted Files (x86)\Git\bin\bash.exe",
    r"path-redacted Files\Git\usr\bin\bash.exe",
)

# In-memory cache for sh
...[truncated]
```

Tail:
```text
 LOGGER.warning("Slow shell call (>5s): %s (duration: %.2fs)", command[:50], duration)

        result = ShellResult(
            exit_code=res.returncode,
            code=res.returncode,          # legacy alias
            stdout=_coerce_text(res.stdout),
            stderr=_coerce_text(res.stderr),
            shell=resolved_shell,
            cache_hit=False,
        )
        if shell_auto_selected:
            result["shell_auto_selected"] = True
            result["requested_shell"] = (shell or "powershell").strip().lower()

        # Update cache
        if cache_ttl > 0:
            _shell_result_cache[cache_key] = (now, result)
        return result

    except subprocess.TimeoutExpired:
        LOGGER.warning("Shell call timed out: %s", command[:50])
        raise


def availabl
...[truncated]
```

### inbox_service.py
- path_ref: path-ref:970b010158de
- sha256: 6c030ebcb1d95247f5fb8685211c2873979efa41040f71e2b650bd6c4ccfff26
- chars: 4236
- omitted_middle_chars: 1836
- omitted_middle_sha256: aa4a2348fbc109e92d0de12802ddc4d5f2e9cc3196b8399c863af85649e6dc6e
- signals: (none)

Head:
```text
"""Inbox service deep module — operator ↔ Jules message exchange.

Simple typed interface hiding path construction, file I/O,
directory listing, and error semantics.
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class InboxMessage(dict):
    """A message read from jules_inbox/.

    Keys always present:
      file (str): basename of the file read
      content (str): full text of the file

    Error variant (404):
      error (str): description
      hint (str): guidance for the caller
      inbox_files (list[str]): available filenames
    """


# ---------------------------------------------------------
...[truncated]
```

Tail:
```text
ontent), 200


def inbox_write(
    content: str,
    file: str | None = None,
    inbox_dir: str | None = None,
) -> dict:
    """Write content to a file in jules_inbox/.

    Args:
        content: Text to write (may be empty).
        file: Basename of the target file.
              Defaults to 'JULES_RESPONSE.md'.
        inbox_dir: Override the default inbox directory path.

    Returns:
        dict with status and file keys.
    """
    base = inbox_dir or _DEFAULT_INBOX_DIR
    name = _safe_basename(file, _DEFAULT_WRITE_FILE)
    path = os.path.join(base, name)
    os.makedirs(base, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return {"status": "success", "file": name}


# ----------------------------------------------------
...[truncated]
```

### retrospective_module.py
- path_ref: path-ref:41ab80cee797
- sha256: 5e7e8e67168a51b27a7eecb2d4435b80f64a3180f365368a4b51837a455e1a5b
- chars: 34697
- omitted_middle_chars: 32297
- omitted_middle_sha256: dc4ef03ffb6a38d4160542a8b0bd408b5909dc86a5e240c4c10aeaea434600d6
- signals: smart_truncation, evidence

Head:
```text
"""Retrospective deep module — self-improving harness analysis.

Applies Nick Ni's "Case" retrospective agent pattern to Jules Bridge.
See: AI Engineer World Fair 2025, "Building AI Systems That Ship"

Core principle: Every failure is a harness bug.
Every session produces a log. The retrospective reads those logs,
extracts learnings, and writes them to per-domain memory markdown files.

The next agent session that starts will load those memory files and
automatically know what went wrong last time.

Architecture:
  - Reads: bridge.log (structured log lines)
  - Reads: JSONL transcripts from brain/ directory
  - Writes: memory/*.md files (per-domain markdown memory)
  - Writes: memory/test_evidence.json (SHA-256 of test outputs)
  - Returns: RetrospectiveReport with learnings and evidence
...[truncated]
```

Tail:
```text
tions = 0
    dated_sections = 0
    actionable_count = 0

    _ts_re = re.compile(r"(\d{8}T\d{6})")

    for line in lines:
        if line.startswith("## "):
            total_sections += 1
            if _ts_re.search(line):
                dated_sections += 1
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            # Bullet point roughly counts as actionable context
            actionable_count += 1

    if total_sections == 0:
        quality_score = 0.0
    else:
        quality_score = float(actionable_count) / float(total_sections)

    res = {
        "total_sections": total_sections,
        "dated_sections": dated_sections,
        "stale_count": total_sections - dated_sections, # Simple heuristic
        "actionable_count": actionable_count,
...[truncated]
```

### __init__.py
- path_ref: path-ref:672557dfcb03
- sha256: d3726b6f0f599cae258a7ef094f0360b527d74cec22feb1eb5797f21c2cdc630
- chars: 5617
- omitted_middle_chars: 3217
- omitted_middle_sha256: 84de8231c085e1007760eee544c146effa91046155c1e93545905c3b838c8bda
- signals: smart_truncation, subagents, evidence

Head:
```text
"""Jules Bridge modules package — deep module interfaces for the bridge API.

Each sub-module hides its implementation complexity behind a typed interface.
bridge.py imports from here and does nothing but HTTP routing.
"""

from .fs_service import FSResult, ListEntry, read, write, tail, grep, list_dir
from .shell_executor import (
    ShellResult,
    ShellNotAvailableError,
    UnsupportedShellError,
    execute,
    spawn,
    available_shells,
)
from .ui_automation import (
    ScreenshotResult,
    ClickResult,
    SecretResult,
    UIDetectionResult,
    screenshot,
    click,
    type_text,
    get_secret,
    detect_ui_state,
)
from .inbox_service import InboxMessage, inbox_read, inbox_write
from .human_mimic_driver import (
    HumanMimicResult,
    drive_quantower_login,
)
from .v
...[truncated]
```

Tail:
```text
sult",
    "HandoverIndex",
    "oracle_status",
    "oracle_build_deploy",
    "codex_handover_index",
    # reasoning_module
    "HLevelPlan",
    "LLevelAction",
    "HaltDecision",
    "ReasoningTrace",
    "reason",
    "plan_only",
    "execute_step",
    # retrospective_module
    "MEMORY_DOMAINS",
    "LogPattern",
    "TestEvidence",
    "EvidenceStaleness",
    "DoomLoop",
    "RetrospectiveReport",
    "analyze_session",
    "record_test_evidence",
    "load_test_evidence",
    "load_memory",
    "prune_memory",
    "check_test_evidence_staleness",
    "is_evidence_hard_gate_enabled",
    "validate_memory_domain",
    # akc_module
    "AKCContext",
    "AKCCheckpoint",
    "AKCReadiness",
    "build_akc_context",
    "load_akc_checkpoint",
    "check_akc_readiness",
    # contex
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.

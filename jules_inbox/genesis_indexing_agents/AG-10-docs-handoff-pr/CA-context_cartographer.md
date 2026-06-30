# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 10: Docs memory handoff and PR readiness map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 6
- active_prompt_chars: 10709
- omitted_middle_chars: 127639
- compression_ratio: 0.0772

## No Slop Workflow
- mode: spec_first
- compaction_required: False
- phases: research -> plan -> implement
- gates: review research before plan; review plan before code; record evidence before done

## Context Handling Policy
- active_context: source head/tail excerpts only
- memory_store: head_tail_active_context_middle_memory_refs (6 refs)
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

### README.md
- path_ref: path-ref:60d2ef7bed95
- sha256: 21953a335b60c3be496b5914e864ac3ae0d5458c78be3fe5f416e8d3e9563ad9
- chars: 45251
- omitted_middle_chars: 42851
- omitted_middle_sha256: b9f74ef9741d72de2deeb2928ff3572372254ac731411008ba188ff173a5a86d
- signals: smart_truncation, long_session_evals, evidence

Head:
```text

ComputerComputer BrowserBrowser Godmodejumboskill
Filter by
All Requests
POST /shell
200 OK 421.07ms
GET /ui/screenshot
200 OK 381.32ms
POST /inbox/write
200 OK 26ms
POST /inbox/read
500 INTERNAL SERVER ERROR 2.41ms
POST /fs/read
200 OK 25.66ms
POST /fs/read
200 OK 18.7ms
POST /inbox/read
500 INTERNAL SERVER ERROR 5.3ms
GET /oracle/status
200 OK 1.31s
POST /inbox/read
200 OK 8.63ms
POST /shell
400 BAD REQUEST 21.85ms
POST /shell
400 BAD REQUEST 3.62ms
POST /shell
200 OK 243.71ms
POST /shell
200 OK 294.34ms
POST /shell
400 BAD REQUEST 2.51ms
POST /shell
200 OK 278.84ms
POST /shell
200 OK 355.08ms
POST /shell
400 BAD REQUEST 2.38ms
GET /ping
200 OK 1.7ms
GET /ping
200 OK 2.47ms
1 minute agoDuration421.07ms
IP34.28.228.31
POST /shell
Summary
Headers
Raw
Binary
164 bytes application/json
{
...[truncated]
```

Tail:
```text
, error mapping, shell selector docs, and open-access warnings.
JULES_TOOL_REQUIREMENTS.md: rewritten as a safe operator manifest for shell routing, UI safety, request rules, and Quantower/Oracle evidence flow.
bridge.py: log rotation is now 10MB, shell timeout default is now 30s, PowerShell uses -NoProfile -NonInteractive, /shell returns both code and exit_code, and /fs/read//fs/tail return both content and data.
start.py: startup log rotation now matches 10MB.
test_bridge_routes.py: updated for the new PowerShell invocation and exit_code alias.
Verified:

python -m py_compile bridge.py notify_email.py start.py
python -m unittest discover -s tests -p "test_*.py": 14 passed
Live bridge restarted successfully on port 5000
Live /shell PowerShell returned code: 0, exit_code: 0
Live /shell cmd
...[truncated]
```

### PROJECT_STATE.md
- path_ref: path-ref:589d0aa6337c
- sha256: 0d5de1e542f80c4ac366253a671bac72e81d658deea565f7b2669ae26ef3c1fe
- chars: 3884
- omitted_middle_chars: 1484
- omitted_middle_sha256: 020d0bbe76aa36bfb570783caff2fcb612afaf4697392f8ec2a81e0149e91661
- signals: subagents, evidence

Head:
```text
# PROJECT_STATE — Jules Bridge + Oracle V5 Operator

> **Audience:** Global Verdent Rule / Oracle V5 Advanced Operator handoff chain
> **Updated:** 2026-06-29 (session: Chat Service Deep Module Cleanup)
> **Companion systems:** `context/` (Project Agents Rule) · `.agents/AGENTS.md` (orchestrator)

---

## Snapshot

| Field | Value |
| --- | --- |
| **Repo** | `path-redacted` |
| **Branch** | `master` |
| **Working tree** | Dirty (Chat Service Deep Module Cleanup) |
| **Last commit** | `f1d2114` — chore: initialize dispatch cycle state, launch state, and completion ledger tracking files |
| **Tests** | 315 passed (`python -m pytest tests/ -q`) |
| **Bridge entry** | `python bridge.py` → Flask on `0.0.0.0:5000` |
| **Oracle V5 source** | `path-redacted` |
| **Oracle DLL** | `path-redacted` |
...[truncated]
```

Tail:
```text
ence triggers soft warning or HTTP 423 when `EVIDENCE_GATE_HARD=1` |
| B3 | `vm_manager` not implemented | **Resolved this session** | Added `modules/vm_manager.py`, `/vm/*` routes, and evidence hash `9c9f9477f26ebdcc9c8696bb67ed1cffbdc54f6632be10242c27c41aaed2de7a` |

---

## Dual Handoff Systems (do not conflate)

| System | Primary files | Audience |
| --- | --- | --- |
| **Project Agents Rule** | `context/01–08`, `.agents/AGENTS.md`, `memory/*.md` | Jules Bridge coding agents |
| **Global Verdent Rule (Oracle V5)** | `PROJECT_STATE.md`, `docs/HANDOFF_PROTOCOL.md`, `docs/NEXT_PROFILE_PROMPT.md`, `docs/CLAIM_AUDIT.md` | Profile/credit switches, Oracle operator continuity |

Both must be read at session start when work touches Oracle V5 trading claims or Quantower host operations.

---

#
...[truncated]
```

### pr_description.md
- path_ref: path-ref:26863f07eabb
- sha256: 76ad4a64d35d10be27b42abd876fc7890e3e1f274cb303b2b10b406fff0e690e
- chars: 388
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
🎯 **What:** The testing gap in `modules/app_launcher.py` addressed, covering all previously untested edge cases.
📊 **Coverage:** Test coverage for `modules/app_launcher.py` is now at 100%. Tested rejecting URLs with newlines and correct execution paths using `shutil.which`.
✨ **Result:** Test coverage for the file improved to 100%, and new tests cover previously untested functions.

```

### 06_progress_tracker.md
- path_ref: path-ref:304c1e400e9c
- sha256: 1e8a3d06fce3f56219982c6dc5e121112e5d1b92e7af6ec7cb4705204ea3e3ea
- chars: 37664
- omitted_middle_chars: 35264
- omitted_middle_sha256: 8d212b36fbf5beed6c881ce047270fce83abb01f2f8408079d248c392de25dc0
- signals: smart_truncation, memory_store, subagents, long_session_evals, tdd, evidence, hrm

Head:
```text
# Jules Bridge — Progress Tracker

> Context file 6 of 7. The ONLY file that updates constantly.
| Decision | Choice | Rationale |
| Decision | Choice | Rationale |
| Memory format | Markdown files | Human + agent readable; matches Nick's Case |
| Evidence storage | SHA-256 in JSON | Cryptographic proof; cannot be faked |
| LLM integration | Gemini via alias system | No new API key; `fast`/`smart` aliases hide provider details |
| Module contract | Never raises | Partial data beats exceptions in a harness |
| Context system | 7-file + AGENTS.md | Ghost AI spec-driven approach + orchestrator |
| Gotchas over docs | ~553 lines | Guides without prescribing; smaller context |
| Agent Skills | 5 core skills | Systematize planning, continuity, review, recovery, and patterns |
| Evidence gating |
...[truncated]
```

Tail:
```text
r launches VM LLM health tasks or burns scarce VM provider quota.
- [x] Updated VM relay bootstrap defaults to target the active GCP OS Login worker user `atibin7_gmail_com`, write under `/home/{VM_USER}`, preserve `OPENROUTER_API_KEYS`, and generate a worker template with active-home env loading plus multi-model OpenRouter fallback.
- [x] Added focused tests for passive deep-health VM probing, configured worker-user bootstrap paths, and generated worker OpenRouter rotation.
- [x] Verification: focused health/chat/dashboard/vm relay slice passed (`54 passed`), full suite passed (`434 passed`), and `git diff --check` passed with only normal CRLF warnings.
- [x] Restarted bridge to PID `37788`, recycled LocalTunnel to `https://shaggy-kiwis-shout.loca.lt`, verified public `/ping`, `/health`,
...[truncated]
```

### general.md
- path_ref: path-ref:97cf69da61e8
- sha256: f4a71357552b9191966ac8bdf3ecb9e2cdfceea18cfab40b7d0a25407e92f1f6
- chars: 50440
- omitted_middle_chars: 48040
- omitted_middle_sha256: 02923ef55b4a0e1d58448c02efbd73291b7cc58a16b9043f59c1acd220f091f0
- signals: smart_truncation, memory_store, subagents, long_session_evals, tdd, evidence, hrm

Head:
```text
# Jules Bridge — General Memory

This file is maintained by the retrospective module.
Each session that runs `POST /retrospective/analyze` will append learnings here.

> **Principle (Nick Ni)**: "Every failure becomes data for the next run."

## How to use this file

Read this at the start of a Jules Bridge coding session to understand what
has gone wrong before and what to avoid.

## Initial Notes (Bootstrapped)

- Jules Bridge is a thin HTTP routing layer — all business logic lives in `modules/`
- Never add business logic to `bridge.py` — route handlers do validate → call module → return JSON only
- The 5 core modules: `fs_service`, `shell_executor`, `ui_automation`, `inbox_service`, `oracle_session`
- Phase 2 added: `reasoning_module` (HRM H/L/ACT pattern)
- Phase 3 added: `retrospectiv
...[truncated]
```

Tail:
```text
/home/{VM_USER}`, preserves `OPENROUTER_API_KEYS`, carries the bridge token from env, and generates a worker template that reads `Path.home() / ".jules_worker.env"` with multi-key/multi-model OpenRouter fallback.
- Verification: focused health/chat/dashboard/vm relay slice passed `54 passed`; full `python -m pytest tests/ -q` passed `434 passed`; `git diff --check` passed with only normal CRLF warnings. Bridge restarted to PID `37788`.
- Runtime proof: local `/health/deep` reports VM `pass` without forcing a VM LLM probe, `/chat/test` reports `vm_worker: ok`, dashboard reports `VM worker online; VM chat recently succeeded`, and LocalTunnel was recycled to `https://shaggy-kiwis-shout.loca.lt`. Public `/ping`, `/health`, and `/dashboard/status` passed. Native Chrome proof saved `jules_inbox/
...[truncated]
```

### JULES_RESPONSE.md
- path_ref: path-ref:af4b1cd2f75c
- sha256: e87932c0316148a97a1ddb4b023dfabb68d30ad5e612b7e5e0f641ae1cfb1cc2
- chars: 1127
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
Context bleed acknowledged.
Applied micro-refactor: added -> Any to def chat() and LOGGER.debug() to log payload keys in bridge.py.
PR submitted to close the task.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.

[TUNNEL_DEAD] Ngrok tunnel cannot sel
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.

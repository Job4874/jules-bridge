# PROJECT_STATE — Jules Bridge + Oracle V5 Operator

> **Audience:** Global Verdent Rule / Oracle V5 Advanced Operator handoff chain  
> **Updated:** 2026-06-29 (session: Chat Service Deep Module Cleanup)
> **Companion systems:** `context/` (Project Agents Rule) · `.agents/AGENTS.md` (orchestrator)

---

## Snapshot

| Field | Value |
| --- | --- |
| **Repo** | `C:\Users\abdul\.jules` |
| **Branch** | `master` |
| **Working tree** | Dirty (Chat Service Deep Module Cleanup) |
| **Last commit** | `f1d2114` — chore: initialize dispatch cycle state, launch state, and completion ledger tracking files |
| **Tests** | 315 passed (`python -m pytest tests/ -q`) |
| **Bridge entry** | `python bridge.py` → Flask on `0.0.0.0:5000` |
| **Oracle V5 source** | `C:\aotp\projects\OracleV5` |
| **Oracle DLL** | `C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll` |

---

## Current Phase

**Phase 5 — LLM Integration + Self-Improvement** (per `context/06_progress_tracker.md`)

Parallel track in progress:

**Human-Mimic UI & VM Driver** — green phase for secret provider + UI detection; Quantower login ACT driver landed (`POST /ui/drive_quantower_login`). See `implementation_plan.md`.

---

## Recently Completed (high signal)

| Area | Status | Evidence |
| --- | --- | --- |
| App launcher (Edge) | Done | `modules/app_launcher.py`, `POST /apps/launch_browser`, 8 unit tests |
| Token auth on bridge | Done | commit `98af291` |
| Jules fleet / COT automation | Done | 29/29 packets complete per `JULES_COT_LEDGER.json` |
| Context sub-agents + no-slop workflow | Done | `POST /akc/subagents` |
| Human-mimic UI & VM Driver | Done | Phase 5 completion evidence hash `93c3c248eb977a5969a1ab02fc9d3968a721e6ef40b5947319b117a9874ad68b` |
| Chat service deep module | Done | `modules/chat_service.py`, thin `/chat` + `/chat/test`, evidence hash `e1e7b4bce3b265a14326d66a18eb33d1a99af42a348d85cb1d45c9a614065408` |

---

## Active Work / Next Queue

1. **Oracle V5 claim audit** — begin 8-target verification in `docs/CLAIM_AUDIT.md` (source reads done; runtime telemetry cross-check pending).
2. **Medium-priority Oracle docs** — `docs/INVENTORY.md`, `docs/PARAMETERS.md`, `docs/ORACLE_V5_MASTER_SPEC.md` (not yet created).

---

## Blocking Issues

| ID | Issue | Severity | Notes |
| --- | --- | --- | --- |
| B1 | Oracle V5 handoff chain was missing | **Resolved this session** | Created `PROJECT_STATE.md`, `docs/HANDOFF_PROTOCOL.md`, `docs/NEXT_PROFILE_PROMPT.md`, `docs/CLAIM_AUDIT.md` |
| B2 | No live Oracle runtime evidence in Jules repo | Medium | `/oracle/*` routes depend on `test_evidence.json`; stale evidence triggers soft warning or HTTP 423 when `EVIDENCE_GATE_HARD=1` |
| B3 | `vm_manager` not implemented | **Resolved this session** | Added `modules/vm_manager.py`, `/vm/*` routes, and evidence hash `9c9f9477f26ebdcc9c8696bb67ed1cffbdc54f6632be10242c27c41aaed2de7a` |

---

## Dual Handoff Systems (do not conflate)

| System | Primary files | Audience |
| --- | --- | --- |
| **Project Agents Rule** | `context/01–08`, `.agents/AGENTS.md`, `memory/*.md` | Jules Bridge coding agents |
| **Global Verdent Rule (Oracle V5)** | `PROJECT_STATE.md`, `docs/HANDOFF_PROTOCOL.md`, `docs/NEXT_PROFILE_PROMPT.md`, `docs/CLAIM_AUDIT.md` | Profile/credit switches, Oracle operator continuity |

Both must be read at session start when work touches Oracle V5 trading claims or Quantower host operations.

---

## Quick Health Commands

```powershell
cd C:\Users\abdul\.jules
python -m pytest tests/ -q
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/oracle/status
curl http://127.0.0.1:5000/akc/readiness
```

---

## Update Rule

Any agent that changes phase, branch, blocking issues, or last verified test count **must update this file** before ending the session.

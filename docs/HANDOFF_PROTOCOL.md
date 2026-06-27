# HANDOFF_PROTOCOL — Oracle V5 Advanced Operator

> Checklist for profile switches, credit switches, and cross-agent continuity.  
> Use alongside the Project Agents Rule (`context/` + `.agents/AGENTS.md`).

---

## When This Protocol Applies

Run the full checklist when **any** of these occur:

- Switching AI profile (Verdent ↔ Cursor ↔ Jules ↔ Codex)
- Starting a new paid/credit session after idle gap
- Handing off Quantower or Oracle V5 host operations
- Resuming after bridge restart, Quantower restart, or DLL redeploy
- Claiming Oracle V5 behavior is verified or production-ready

---

## Pre-Handoff (outgoing agent)

### 1. Freeze state

- [ ] Record git branch, last commit hash, working tree status
- [ ] Run `python -m pytest tests/ -q` and note pass count
- [ ] If tests ran for a feature claim, call `POST /retrospective/record_evidence` with SHA-256

### 2. Update handoff artifacts

- [ ] Update `PROJECT_STATE.md` (phase, blockers, last commit, test count)
- [ ] Update `docs/NEXT_PROFILE_PROMPT.md` with **one** concrete next action
- [ ] If Oracle claims changed, append rows to `docs/CLAIM_AUDIT.md`
- [ ] Update `context/06_progress_tracker.md` for Jules Bridge feature work

### 3. Oracle / Quantower host snapshot (if touched)

- [ ] `GET /oracle/status` — capture JSON or note stale evidence warning
- [ ] Confirm Quantower process: `Get-Process -Name Starter` (Starter.exe)
- [ ] If strategy instance changed, note active `info.xml` path in `memory/quantower.md`
- [ ] Do **not** restart Quantower casually — logs out and drops connections

### 4. Secrets and safety

- [ ] No plaintext credentials in commits, memory, or handoff docs
- [ ] UI/secret routes used with `allow_secret_use=true` only when operator authorized
- [ ] Browser launch routes used with `allow_launch=true` only when operator authorized

---

## Post-Handoff (incoming agent)

### 1. Read order (Oracle operator)

1. `PROJECT_STATE.md`
2. `docs/NEXT_PROFILE_PROMPT.md`
3. `docs/CLAIM_AUDIT.md` (check which claims are verified vs pending)
4. `docs/HANDOFF_PROTOCOL.md` (this file)
5. `memory/oracle.md` + `memory/quantower.md` if host work
6. Project Agents context chain (`context/01` → `08`, `.agents/AGENTS.md`)

### 2. Verify environment

- [ ] `GET /akc/readiness` — checkpoint status `ready`
- [ ] `GET /health` — bridge up
- [ ] `GET /tentacles` — route manifest matches task
- [ ] Git state matches `PROJECT_STATE.md`

### 3. Evidence gate awareness

- [ ] Check age of `test_evidence.json` before trusting `/oracle/*` responses
- [ ] Soft mode: `X-Evidence-Age-Warning: stale:{N}s` header
- [ ] Hard mode: `EVIDENCE_GATE_HARD=1` → HTTP 423 on stale `/oracle/*`

### 4. Do not assume

- [ ] Jules COT complete ≠ Oracle V5 runtime verified
- [ ] Source code constants ≠ live Quantower instance settings (check `info.xml`)
- [ ] Context files ≠ Oracle V5 master spec (see pending `docs/ORACLE_V5_MASTER_SPEC.md`)

---

## Profile-Specific Notes

| Profile | Extra step |
|---|---|
| **Verdent / Oracle V5 operator** | Read `CLAIM_AUDIT.md` before stating penalty weights, Kelly, GodScore, or execution timeouts |
| **Jules remote worker** | Read `jules_inbox/JULES_COT_LEDGER.md` before launching duplicate packets |
| **Cursor / local dev** | Read `context/05_gotchas.md` before editing `bridge.py` header (lines 1–230) |

---

## Handoff Quality Bar

A handoff is **complete** when the next agent can answer without guessing:

1. What phase are we in?
2. What is the single next action?
3. What is blocked?
4. Which Oracle claims are verified vs pending?
5. What test evidence proves the last change?

---

## Escalation

If incoming agent finds `PROJECT_STATE.md` stale by >1 session or git diverges:

1. Re-run git + pytest snapshot
2. Overwrite `PROJECT_STATE.md` from facts
3. Mark conflicting claims in `docs/CLAIM_AUDIT.md` as `STALE — needs re-verify`

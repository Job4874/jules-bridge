# NEXT_PROFILE_PROMPT — Copy This Into the Next Session

> **Generated:** 2026-06-26  
> **Single next action below** — do not start unrelated work until this is done or explicitly superseded by the operator.

---

## Prompt Block (paste verbatim)

```
Oracle V5 operator session — continue from Jules Bridge handoff chain.

READ FIRST (in order):
1. PROJECT_STATE.md
2. docs/CLAIM_AUDIT.md
3. docs/HANDOFF_PROTOCOL.md
4. context/06_progress_tracker.md
5. memory/oracle.md

CURRENT STATE:
- Branch: master @ af319fa (clean tree)
- Tests: 265 passed
- Phase 5 + Human-Mimic UI driver (Quantower login route landed)
- Oracle V5 handoff docs created this session; claim audit started (source verified, runtime pending)

YOUR SINGLE NEXT ACTION:
Complete Oracle V5 8-target claim audit runtime verification:
1. Open docs/CLAIM_AUDIT.md
2. For each target marked PENDING_RUNTIME, collect evidence from:
   - Live Quantower instance info.xml (GodScore Min To Open/Add/Flatten)
   - CSV telemetry under OneDrive\Documents\Oracle_V5_Telemetry\CSV\ (pipeline_trace row exists)
   - GET /oracle/status with fresh test_evidence.json (record via POST /retrospective/record_evidence if you run tests)
3. Update CLAIM_AUDIT.md status columns — do not mark VERIFIED without file path or HTTP evidence
4. Update PROJECT_STATE.md blocking issue B2 if evidence gate cleared

DO NOT:
- Restart Quantower unless operator explicitly requires it
- Commit secrets or paste credentials into memory/handoff files
- Claim Jules COT completion equals Oracle runtime verification

WHEN DONE:
- Update PROJECT_STATE.md and this file with the next single action
- Run remember skill → memory/oracle.md if Oracle learnings emerged
```

---

## After This Action

Likely follow-ups (pick one per next session — do not batch without operator approval):

| Priority | Follow-up |
| --- | --- |
| High | Create `docs/ORACLE_V5_MASTER_SPEC.md` consolidated from OracleV5 source + verified claims |
| Medium | Implement `modules/vm_manager.py` per `implementation_plan.md` |
| Medium | Create `docs/INVENTORY.md` + `docs/PARAMETERS.md` |
| Low | Extend `app_launcher` beyond Edge if operator defines new approved app workflows |

---

## Supersession Rule

Replace this entire file when the single next action changes. Keep exactly **one** primary action in the prompt block.

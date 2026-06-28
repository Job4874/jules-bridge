# Jules Full Objective - 2026-06-28

This supersedes narrow blocker notes. Treat this as the active operating objective until the operator replaces it.

## Objective

Inherit the full available Jules Bridge tool surface and use it with no-slop HRE discipline to move Oracle/Quantower toward verified G3 dry-run proof.

## Current Proven State

- Source-of-truth repo commit: `7c0a5fe docs: harden Jules self-unblocking protocol`.
- Public bridge URL: `https://parade-marrow-pulp.ngrok-free.dev`.
- Public `/ping`: HTTP 200, `{"status":"Jules Bridge Online"}`.
- Public authenticated `/tentacles`: HTTP 200, 50 routes.
- Available tool groups include filesystem, Oracle status/build, UI screenshot/click/type, VM, apps, notify/email, Jules dispatch/launch/watch/fleet, reasoning, retrospective, and AKC.
- Local Oracle status currently reports `Quantower Starter not running`.
- Oracle V5 `info.xml` exists and binds MES plus account.
- `Enable Live Trading=false`.
- `Enable Dry Run Mode=false`.
- G3 dry-run broker-block proof is not yet captured.

## Required Operating Mode

Use no-slop HRE checkpoints:

1. Hypothesis: classify the blocker.
2. Route: pick the narrowest tool, route, skill, file, or repo check.
3. Evidence: capture exact output before deciding.

Before escalating, run up to three bounded HRE passes using:

- `GET /tentacles`
- `GET /session/log`
- `jules_inbox/JULES_SELF_UNBLOCKING_PROTOCOL.md`
- `jules_inbox/JULES_TOOL_REQUIREMENTS.md`
- `context/05_gotchas.md`
- `memory/reasoning.md`
- relevant domain memory such as `memory/oracle.md` and `memory/quantower.md`
- `.agents/skills/*/SKILL.md`

## Mission Sequence

1. Pull or read commit `7c0a5fe` and confirm the self-unblocking protocol is present.
2. Verify public bridge reach:
   - `GET /ping`
   - authenticated `GET /tentacles`
   - authenticated `GET /oracle/status`
3. Use the `/oracle/status` blocker list as the current source of truth.
4. If Quantower is still down, decide the narrowest safe recovery path and record evidence before acting.
5. Do not place live orders or enable live trading.
6. Continue toward G3:
   - Quantower running
   - Oracle V5 instance loaded on MES
   - dry-run/demo state verified
   - telemetry refreshed
   - `BROKER_SUBMISSION_BLOCKED_DRY_RUN` or equivalent broker-block proof captured
7. Save progress to `JULES_RESPONSE.md` with exact evidence and next action.

## Escalation Bar

Escalate only when the remaining need is external to Jules, such as live-order approval, secret disclosure, paid scaling approval, destructive cleanup approval, or a Jules CLI plan-approval state.

Escalation must include:

- blocker class
- task
- attempted HRE passes
- tools/files checked
- exact error/output
- why operator input is required
- smallest requested action

No vague blocker reports. No hidden chain-of-thought. Evidence first.

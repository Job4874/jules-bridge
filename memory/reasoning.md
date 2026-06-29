## Session 20260627T214922 - 2026-06-27T21:49:22.701894+00:00

- DOOM LOOP: POST /reasoning/solve called 4x consecutively. Route 'POST /reasoning/solve' called 4x consecutively. Add a circuit breaker or cache the last response.

## Session 20260628T020000 - Self-unblocking protocol

- When blocked, use public HRE checkpoints: Hypothesis, Route, Evidence. Do not ask the operator until three bounded passes have checked `GET /tentacles`, request logs, gotchas, memory, relevant skills, and the route/file contracts.
- Treat tool/extension claims as unproven until the manifest, `.agents/skills/`, `JULES_TOOL_REQUIREMENTS.md`, and relevant memory files have been inspected. Record resolved blocker lessons here or in `context/05_gotchas.md`.
- Screenshot route contract gap: `/ui/screenshot?save=true` returns JSON containing `image_base64` and `saved_path`; use `self_created_tools/safe_bridge_probe.py` to omit raw base64 before writing proof reports.

## Self-Sufficiency Operating Rules — Injected by Codex 2026-06-29

### Rule 0: Connectivity Gate (MUST run before ANY work)
1. `GET /ping` on the public ngrok URL — if fail, tunnel is dead
2. `GET /tentacles` with auth — if fail, bridge is unreachable
3. `GET /health` — if fail, bridge process is down
NEVER skip this. If tunnel is dead, use Offline Escalation below.
If local bridge is up but tunnel is dead, the operator must restart ngrok.

### Rule 1: Offline Escalation Protocol
When tunnel is confirmed dead and cannot self-heal:
1. Write blocker details to `jules_inbox/JULES_RESPONSE.md`
2. `git add jules_inbox/JULES_RESPONSE.md`
3. `git commit -m "[TUNNEL_DEAD] <one-line blocker description>"`
4. `git push origin master`
The `[TUNNEL_DEAD]` commit tag gives the operator visibility without bridge access.
Do NOT continue working on bridge-dependent tasks when the tunnel is dead.

### Rule 2: Doom Loop Prevention
Before calling any route > 3 times consecutively, check `memory/general.md` for prior doom loop entries.
Known catastrophic doom loops from bridge.log analysis:
- `GET /dashboard/status`: 814x consecutive (worst offender — Ticket 007 circuit breaker)
- `GET /ping`: 42x consecutive
- `GET /health`: 32x consecutive
- `POST /shell`: 20x consecutive (avg 58s per call = 19 min wasted)
- `POST /fs/read`: 30x consecutive
- `POST /jules/fleet-watch`: 34x consecutive (avg 441s per call = 4.1 hrs wasted)
If you detect yourself calling the same route > 5x, STOP and run the `recover` skill.

### Rule 3: Skill Usage Discipline (Non-Negotiable)
- Before coding any ticket: run `architect` skill
- After coding any ticket: run `review` skill + `imprint` skill
- When stuck or looping: run `recover` skill
- End of EVERY session: run `remember` skill
- NEVER skip `remember` — it's what keeps the next session from repeating your mistakes.
- Read `memory/general.md` (318 lines of learnings) BEFORE starting work.

### Rule 4: Evidence Discipline
- Every test run → `POST /retrospective/record_evidence` with raw pytest output
- Every ticket completion → update `context/06_progress_tracker.md`
- Every resolved blocker → add gotcha to `context/05_gotchas.md` + entry here
- Every session end → `POST /retrospective/analyze` to extract log patterns
- If evidence is missing, the work is NOT done. Period.

### Rule 5: Known Environment Traps
- The npm `jules.cmd` shim hangs on Windows; prefer `C:\Users\abdul\AppData\Roaming\npm\bin\jules.exe`
- `jules.exe` temp binary at `%TEMP%\jules_tmp\jules.exe` gets cleaned by Windows; fix with `npm install -g @google/jules`
- Quantower license modal blocks ALL UI work; requires manual dismissal or Quantower restart
- `pyautogui` requires a display; `/ui/*` routes fail headless — this is expected, not a regression
- `POST /shell` averages 58s — don't call it in tight loops
- Bridge token is `JULES-SECURE-999` — always include `Authorization: Bearer JULES-SECURE-999`


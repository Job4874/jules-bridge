# Jules Proof Run - 2026-06-28

The operator wants proof of how far Jules can really go after more than two days. This is not a status-note task. Produce a concrete proof packet.

## Operator Intent

Show the strongest real capability available right now:

- Use the live bridge, not remembered state.
- Move the Oracle/Quantower system forward if it is safe.
- If you cannot move it forward, prove the blocker with screenshots, route responses, exact commands, and exact output.
- Do not ask the operator to interpret vague blockers.

## Fresh Starting Evidence

Captured by Codex on 2026-06-28 before dispatch:

- Public bridge `/ping`: PASS, `{"status":"Jules Bridge Online"}`.
- Public authenticated `/tentacles`: PASS, 50 tentacles.
- Local `/oracle/status`: PASS.
- Quantower process: running, window title `Quantower`, PID observed as `40832`.
- Oracle V5 instance: exists, `f9eb0699-4c73-4ee2-b377-87c92468b6c7`.
- Oracle state: `50`.
- Primary symbol label in Oracle instance: `MES`.
- Symbol bound: true.
- Account bound: true. Do not print account identifiers.
- Enable Live Trading: `false`.
- Enable Dry Run Mode: `false`.
- Gates:
  - `g2_dll_deployed=false`
  - `g3_dry_run_proof=false`
  - `g4_dom_l2=false`
  - `g5_order_lifecycle=false`
- Telemetry file: `heartbeat_2026-06-27.csv`.
- Telemetry last write: `2026-06-27T03:56:38.352926+00:00`.
- `BROKER_SUBMISSION_BLOCKED_DRY_RUN` grep: no hit in searched Oracle telemetry / Quantower script logs.
- Foreground Quantower screenshot: `jules_inbox/screenshots/screen_20260628-200153.png`.
- Remote proof session `16797126457435464612` failed because it saved raw `/ui/screenshot` JSON as `latest_screenshot.png`. That is not acceptable evidence.
- Use `self_created_tools/safe_bridge_probe.py` for route proof so `image_base64` is omitted and only screenshot paths plus concise route summaries are printed.

Screenshot state observed:

- Quantower is foregrounded.
- A connection modal is open on an Alpaca demo connection form.
- Chart panes show no data available.
- DOM surface is visible for a non-MES instrument.
- This screenshot proves UI access and a concrete UI blocker/state. It is not G3 proof.

## Mandatory Read Order

Read these before acting:

1. `JULES_TOOL_REQUIREMENTS.md`
2. `JULES_SELF_UNBLOCKING_PROTOCOL.md`
3. `JULES_FULL_OBJECTIVE_20260628.md`
4. `JULES_MASTER_PROMPT_QUANTOWER_OPERATOR.md`
5. `JULES_PROOF_RUN_20260628.md`

## Mission

Produce a `SHOWOFF PROOF REPORT` in `JULES_RESPONSE.md`.

The report must contain one of these outcomes:

1. **Forward progress made**
   - exact action taken
   - before screenshot path
   - after screenshot path
   - route responses used
   - files changed, commit, tests, or runtime proof
   - which gate changed from false to true, if any

2. **Hard blocker proven**
   - blocker class from `JULES_SELF_UNBLOCKING_PROTOCOL.md`
   - three bounded HRE passes attempted
   - exact tool, file, route, command, and output for each pass
   - screenshot path showing the blocker
   - why operator input is genuinely required
   - smallest requested operator action

## Allowed Moves

- Prefer `python self_created_tools/safe_bridge_probe.py all` for first-pass bridge evidence.
- Use `GET /tentacles`, `GET /oracle/status`, `GET /ui/screenshot?save=true`, `POST /fs/grep`, `POST /fs/read`, `POST /inbox/write`, and other bridge routes discovered from `/tentacles`.
- Use screenshots before and after UI actions.
- Use guarded UI actions only when the target is clear from the screenshot and the action is safe.
- Use secrets only through existing guarded routes and only when the route requires explicit `allow_secret_use=true`; never print secret values.
- Run non-live build/profile/deploy/restart steps only if route/file evidence says they are the next safe action.

## Forbidden Moves

- Do not enable live trading.
- Do not place live orders.
- Do not print account identifiers, API keys, tokens, passwords, or bearer strings.
- Do not apply helper-code diffs that hardcode bridge tokens.
- Do not claim Quantower/Oracle proof from a screenshot that only shows Codex or a generic desktop.
- Do not save the raw `/ui/screenshot` response body as a `.png`; the JSON includes `image_base64`, not a PNG byte stream.
- Do not commit raw `image_base64` output into the repo.
- Do not call a plan a proof packet.

## Proof Bar

A useful proof packet has at least four concrete artifacts:

- one current route response summary
- one screenshot path showing the real runtime state
- one command or grep result that confirms or falsifies G3
- one saved inbox response with the exact next action or completed gate

If no gate can be advanced, the proof packet must still be strong enough that another operator can reproduce the blocker without guessing.

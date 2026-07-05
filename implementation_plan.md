# Human-Mimic UI & VM Driver — H/L/ACT Architecture Plan

## Security Lock

- Credentials are operator-authorized secrets only.
- Windows implementation uses OS-backed storage: Credential Manager or DPAPI-backed APIs.
- No plaintext credential persistence in repository files, `.env`, memory markdown, logs, screenshots, evidence JSON, test fixtures, or pull request text.
- Any runtime action that can retrieve or type a secret requires `allow_secret_use=true`.
- Tests use mock secret providers only.
- UI automation must not bypass authentication or access controls; it may only automate authorized local workflows that a human operator could legitimately perform.
- Two-Node Zero-Trust mode: the Cloud Node owns policy/planning logic, while the Local Windows Node acts only as the bridge executor for UI/VM actions. Do not install bridge OS files or credential storage on an Academic Node/school computer.

## H-Level Plan

1. Build `ui_automation` into a state-aware desktop driver that can classify screenshots into safe UI states such as login screen, authentication prompt, Quantower loading, ready workspace, unknown, or error.
2. Add an OS-backed secret abstraction with a mock provider for tests and a Windows provider for local operator secrets.
3. Add guarded UI actions that can type credentials only when the current UI state is compatible, the requested secret target is allowlisted, and `allow_secret_use=true` is present.
4. Add `vm_manager` as a deep module that detects local resource pressure and selects approved VM boot scripts or hypervisor commands without hardcoding credentials.
5. Expose thin bridge routes only after module contracts are stable and covered by tests.
6. Record evidence while redacting secrets and avoiding raw screenshots around credential fields unless explicitly requested by the operator.

## L-Level Module Design

### `modules/ui_automation.py`

Public contracts to add:

- `SecretResult(dict)`: keys include `status`, `target`, `username`, `secret_available`, `error`.
- `UIDetectionResult(dict)`: keys include `state`, `confidence`, `signals`, `error`.
- `UIActionResult(dict)`: keys include `status`, `state`, `acted`, `error`.

Public functions to add:

- `get_secret(target: str, allow_secret_use: bool = False, provider: object | None = None) -> SecretResult`
  - Returns blocked status unless `allow_secret_use` is true.
  - Uses injected provider in tests.
  - Production provider must be OS-backed.
  - Never returns password/secret values in result payloads.

- `detect_ui_state(image_path: str | None = None, ocr_text: str = "", template_signals: dict | None = None) -> UIDetectionResult`
  - Accepts OCR text for deterministic tests.
  - Later integrates OCR/OpenCV behind private helpers.
  - Classifies `quantower_login`, `auth_prompt`, `quantower_loading`, `quantower_ready`, `unknown`.

- `login_quantower(target: str = "quantower_login", allow_secret_use: bool = False, provider: object | None = None) -> UIActionResult`
  - Calls state detection and secret retrieval.
  - Types only through `pyautogui` after explicit authorization and compatible UI state.
  - Redacts all secret-bearing data from return values.

### `modules/vm_manager.py`

Public contracts to add:

- `ResourcePressureResult(dict)`: keys include `status`, `cpu_percent`, `memory_percent`, `maxed_out`, `reasons`, `error`.
- `VMBootResult(dict)`: keys include `status`, `selected_script`, `started`, `dry_run`, `error`.

Public functions to add:

- `detect_resource_pressure(cpu_percent: float | None = None, memory_percent: float | None = None, thresholds: dict | None = None) -> ResourcePressureResult`
  - Uses injected metrics in tests.
  - Later reads local metrics with stdlib or existing dependencies.

- `boot_secondary_vm(script_name: str, allow_vm_boot: bool = False, dry_run: bool = True) -> VMBootResult`
  - Requires explicit `allow_vm_boot=true` for real execution.
  - Only runs scripts from an allowlisted configured directory.
  - Defaults to dry-run.

## ACT Execution Loop

1. Write failing tests for mock secret provider and UI state detection.
2. Implement the smallest `ui_automation` interfaces to pass those tests.
3. Add failing tests for resource pressure and VM boot dry-run gating.
4. Implement `vm_manager` module.
5. Export new public module symbols from `modules/__init__.py`.
6. Add bridge routes only after module tests pass.
7. Update `context/02_architecture.md`, `context/05_gotchas.md`, and `context/06_progress_tracker.md`.
8. Run full `python -m pytest tests/ -q` and record evidence through `/retrospective/record_evidence` when the bridge is available.

## Status

- 2026-06-26: Steps 3-6 completed for `vm_manager`. Added module-boundary tests, `modules/vm_manager.py`, exports, and thin `/vm/resource_pressure` plus `/vm/boot_secondary` routes. Full suite passed 274 tests with 1 existing warning; evidence hash `9c9f9477f26ebdcc9c8696bb67ed1cffbdc54f6632be10242c27c41aaed2de7a`.

# Jules REST API Local Bridge Plan

## Goal

Run Jules control through the local bridge without depending on the Windows
Jules CLI when REST API credentials are configured.

## Scope

1. Add a deep `modules/jules_api.py` module for the Jules REST API.
2. Add direct local routes:
   - `POST /jules/api/sources`
   - `POST /jules/api/sessions/list`
   - `POST /jules/api/sessions`
   - `POST /jules/api/sessions/get`
   - `POST /jules/api/sessions/activities`
   - `POST /jules/api/sessions/send-message`
   - `POST /jules/api/sessions/approve-plan`
3. Keep existing `/jules/preflight`, `/jules/sessions`, `/jules/launch`, and
   `/jules/pull` behavior unchanged unless `JULES_USE_REST_API=1` is set.
4. Use only `.env`/environment variables for credentials; never hardcode or
   return API keys in route payloads.
5. Preserve safe defaults: dry-run stays dry-run, live REST session creation
   still requires the caller to send `dry_run=false` through existing launch
   routes or explicitly call the direct create-session route.

## Env Contract

- `JULES_API_KEY`: API key sent as `X-Goog-Api-Key`.
- `JULES_SOURCE`: Default source name such as `sources/github/owner/repo`.
- `JULES_USE_REST_API=1`: Prefer REST over the CLI in existing Jules routes.
- `JULES_API_BASE_URL`: Optional override, default
  `https://jules.googleapis.com/v1alpha`.
- `JULES_STARTING_BRANCH`: Optional default branch for created sessions.

# Repo Context Guard Dashboard Slice Plan

## Goal

Make the first production-grade dashboard upgrade source-of-truth aware: the
bridge must know which Git repos are present, what provenance labels identify
them, and where ports, server nodes, or local dependencies collide before Jules
or Codex agents are dispatched.

## Scope

1. Add `modules/repo_context_guard.py` as a deep module with one public
   function: `build_repo_context_guard(...)`.
2. Add protected `GET /repo/context-guard` for full repo inventory and collision
   inspection.
3. Add compact `repo_context` status into `GET /dashboard/status` so the
   dashboard can show counts and top collisions without polling a full scan.
4. Add a dashboard panel for repo count, collision count, warning count, cache
   age, and top collision rows.
5. Record gotchas for secret handling, port extraction, scan caching, and
   no-slop collision review.

## Guardrails

- Public module functions never raise.
- Env secret values are never returned; only key names/readiness can surface.
- Full repo details require the protected route; the dashboard status endpoint
  remains compact.
- Repo scans are bounded by `max_depth`, `max_repos`, and
  `REPO_CONTEXT_GUARD_CACHE_TTL_S`.
- `port_collision`, `node_ref_collision`, and
  `local_dependency_cross_project` are the warnings to inspect before sharing
  servers, nodes, or dependencies across projects.

# Gemini CLI Bridge Plan

## Goal

Add Gemini CLI as a coherent, protected bridge capability that can run
alongside Jules without replacing the existing Jules dispatch, REST, or
VM/browser model-loop surfaces.

## Scope

1. Install and verify `@google/gemini-cli` through npm.
2. Add `modules/gemini_cli.py` as the deep module for:
   - CLI command resolution on Windows.
   - `gemini --version` and capability preflight.
   - Optional authenticated smoke checks.
   - Dry-run-first `gemini -p` headless prompt execution.
   - Compact dashboard status from persisted preflight state.
3. Add protected routes:
   - `POST /gemini/preflight`
   - `POST /gemini/prompt`
4. Add Gemini route entries to `TENTACLES`.
5. Add dashboard `gemini_cli` status without spawning CLI subprocesses on every
   poll.

## Guardrails

- `/gemini/prompt` defaults to `dry_run=true` and `approval_mode="plan"`.
- Auth, quota, or model failures are reported as environment blockers, not
  bridge-health failures.
- Do not log or return raw API keys. Only booleans and `likely_blocker` labels
  may describe auth state.
- Keep Gemini CLI separate from `chat_service` and `reasoning_module`; no
  provider SDK dependency is added to the bridge model loop.

# Antigravity CLI Bridge Addendum

## Goal

Add Google's supported `agy` terminal-agent CLI as a first-class proof surface
after the legacy Gemini CLI started returning the official individual-tier
`UNSUPPORTED_CLIENT` migration blocker.

## Scope

1. Install and verify Antigravity CLI locally.
2. Add `modules/antigravity_cli.py` as the deep module for:
   - Windows command resolution through env vars and `%LOCALAPPDATA%\agy\bin`.
   - `agy --version`, `agy models`, and `agy plugin list` preflight.
   - Optional bounded `agy -p` model smoke checks.
   - Dry-run-first prompt execution with prompt redaction.
   - Compact dashboard status from persisted preflight state.
3. Add protected routes:
   - `POST /gemini/antigravity/preflight`
   - `POST /gemini/antigravity/prompt`
4. Add Antigravity route entries to `TENTACLES`.
5. Extend `POST /proof/collaboration` with separate Antigravity gates so a
   supported Google terminal-agent pass does not hide the legacy Gemini blocker.

## Guardrails

- `/gemini/antigravity/prompt` defaults to `dry_run=true`.
- Do not pass `--dangerously-skip-permissions` from bridge-managed prompts.
- Keep `gemini_model_execution` and `google_terminal_model_execution` separate.
- Dashboard polling reads persisted state and must not spawn `agy` repeatedly.

# Alliance Switchboard Plan

## Goal

Create a coherent bridge-level switchboard for complex work where Jules is the
preferred creator/actual change owner and the supported Google terminal-agent
lane is the preferred implementer/reviewer support.

## Scope

1. Add `modules/alliance_switchboard.py` as the deep module for:
   - Jules, Antigravity, legacy Gemini, AKC, and proof readiness intake.
   - Preferred and fallback role selection.
   - A switching decision table and handoff contract.
   - Dry-run-first markdown role packets.
2. Add protected `POST /alliance/switchboard`.
3. Export the module through `modules/__init__.py`.
4. Add module and route tests for the default Jules/Antigravity alliance,
   fallback behavior, input validation, and packet writing.
5. Imprint architecture, gotchas, library docs, and ubiquitous language.

## Guardrails

- The switchboard assigns roles and writes packets only. It does not launch
  Jules sessions, run edit-capable prompts, or modify source files.
- `include_live_checks=true` is bounded preflight work.
- `run_implementer_smoke=true` is the only optional Google model prompt and
  must remain small, non-editing, and timeout-bound.
- Do not call a fallback plan simultaneous two-agent mode unless
  `roles.mode == "two_agent_alliance"`.

# Interactive TIU Workbench Plan

## Goal

Add a simple dashboard control surface over the complex Jules/Google/Codex
bridge so an operator can choose scope, model lane, mode, and cloud gating, then
generate a safe local packet without silently launching workers or mutating Git.

## Scope

1. Add `modules/tiu_workbench.py` as the deep module for:
   - Alliance readiness intake.
   - Codebase route/module/test snapshot intake.
   - Cloud-sync publish gate intake.
   - Scope/lane/mode target-file mapping.
   - Local markdown/JSON packet persistence.
2. Add protected `POST /tiu/workbench`.
3. Add the dashboard TIU rail item and TIU Workbench panel.
4. Fix protected-route browser CORS preflight for dashboard actions.
5. Verify with module/route tests, lint/build, live route proof, and rendered
   desktop/mobile QA on `127.0.0.1:6001`.

## Guardrails

- The TIU workbench is a packet planner only.
- It must not launch Jules sessions, run Gemini/Antigravity prompts, approve
  plans, stage files, commit, push, or pull.
- `publish_blocked` is a valid UI state when cloud sync is required and the
  worktree is dirty.
- Saved packets under `jules_inbox/tiu_workbench/` are review artifacts, not
  approval for live execution.

# Cloud Publish Packet Plan

## Goal

Close the gap between cloud-sync status and actual publish by giving the
operator a safe, reviewable packet that classifies dirty work, names generated
noise, and shows the exact commands needed for intentional commit/push.

## Scope

1. Extend `modules/cloud_sync.py` with `build_cloud_publish_packet(...)`.
2. Add protected `POST /sync/publish-packet`.
3. Export `CloudPublishPacketResult` through `modules/__init__.py`.
4. Add module and route tests for dirty-file classification, packet writing,
   repo-local output validation, and route delegation.
5. Add a Cloud Sync dashboard action that builds the packet, shows compact
   family counts and commands, saves local artifacts, and stages the packet to
   Comms.

## Guardrails

- The publish packet may write markdown/JSON review artifacts only.
- It must never run `git add`, `git commit`, `git fetch`, `git pull`, or
  `git push`.
- Generated/noisy files must be reported separately and excluded from generated
  `git add -- ...` commands.
- A blocked packet still counts as useful evidence; cloud sync is complete only
  after the intended files are committed and pushed.

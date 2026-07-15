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

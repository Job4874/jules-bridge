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

---

# Real-Time Jules Nexus Dashboard Enhancement Plan

## Goal

Turn the existing Vite/React dashboard into a real-time Codex-style command
center for Jules Bridge without inventing data sources or bypassing the
dashboard circuit-breaker discipline.

## Design Decisions

- Keep `/dashboard/status` as the single dashboard data contract.
- Add an explicit `bypass_cache=true` query path for operator-triggered refreshes
  while leaving normal polling cached by default.
- Make the frontend feel live through client-side history, event diffing,
  freshness indicators, and pause/resume controls instead of high-frequency API
  calls.
- Preserve provider truth: Gemini/OpenRouter failures stay visible, VM fallback
  is shown separately, and PR/readiness blockers are not greenwashed.
- Keep chat as a real bridge-backed comm panel with existing `/chat` behavior.

## Implementation Slices

1. Extend `modules.dashboard_module.get_dashboard_status(...)` with a
   `bypass_cache` option and route it from `GET /dashboard/status`.
2. Rebuild `dashboard-ui/src/App.jsx` around reusable dashboard primitives:
   command bar, metric tiles, provider matrix, fleet timeline, worker topology,
   event stream, terminal log, and comm panel.
3. Replace `dashboard-ui/src/index.css` with responsive dense dashboard styles
   that keep text inside stable containers on desktop and mobile.
4. Verify with targeted Python dashboard tests, dashboard lint/build, live
   route checks, and browser screenshot inspection.

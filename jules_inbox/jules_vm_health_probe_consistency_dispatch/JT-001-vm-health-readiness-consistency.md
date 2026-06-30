# Jules Worker Packet JT-001-vm-health-readiness

- instance_index: 1
- status: pending
- task_type: code_health
- source: codex-live-audit
- fingerprint: vm-health-readiness
- repo_path: C:\Users\abdul\jules-bridge

## Objective
Fix VM chat health readiness consistency so health endpoints do not show a false VM failure when real chat is currently succeeding through the VM worker.

## Task Details
- Files: modules/chat_service.py, modules/health_service.py, tests/test_chat_service.py, tests/test_health_deep.py as needed
- Issue: Live evidence showed `/chat` succeeding with `model_used=vm/jules-worker`, while `/chat/test` and `/health/deep` could still report `vm_worker=fail` from a transient health-probe response: `VM fallback provider unavailable: worker reported no LLM available`.
- Language: python
- Rationale: Production readiness must be truthful. It should fail when VM fallback is genuinely unavailable, but it should not show a false VM outage when there is fresh successful real VM chat evidence.

## Implementation Requirements
1. Inspect the current provider readiness flow in `modules/chat_service.py` and any health mapping in `modules/health_service.py`.
2. Add the smallest production-quality fix so recent successful VM chat fallback evidence can clear or override stale local failure evidence for readiness checks without hiding genuine failures.
3. Preserve dashboard lightweight behavior. Do not enqueue VM work on every dashboard poll.
4. Keep bounded freshness if you add success evidence, for example a TTL. Do not make success permanent.
5. Add focused tests covering:
   - failed VM probe followed by recent VM chat success reports healthy/ok;
   - genuine failure with no recent success still reports failure;
   - success/failure evidence is bounded if a TTL is introduced.
6. Run the narrowest relevant tests first, then the broader suite if practical.
7. Do not expose secrets. Do not edit unrelated dispatch telemetry. Do not commit; leave a pullable diff for Codex review.

## Current Live Evidence
- Bridge: http://127.0.0.1:5000
- Public tunnel: https://neat-oranges-wink.loca.lt/ping returned Jules Bridge Online
- `/dashboard/status`: Gemini error, OpenRouter error, VM status may flip based on latest local evidence
- `/chat`: can return `model_used=vm/jules-worker`
- `/chat/test` and `/health/deep`: can report VM failure from a flaky VM probe

## Operating Rules
- Work on this one card only.
- Do not stop at a plan or ask for plan approval.
- Preserve existing behavior unless this card explicitly asks for behavior change.
- Record concrete evidence: commands, test summaries, and files changed.
- Keep bridge routes thin and module logic in modules.

## Completion Report
Write a short report with:
- what changed
- verification performed
- files touched
- whether a PR/commit was created
- next action or blocker

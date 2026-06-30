# Jules Worker Packet JT-001-provider-classification-health-current-head

Repo: `Job4874/jules-bridge`
Local branch/head to target: `codex/jules-production-finish` at `ffe34b40a4d9ed64152f8bc630bef6ac2954f5a5`
PR: `https://github.com/Job4874/jules-bridge/pull/64`

## Objective

Rebase on the current pushed head and add only the missing provider-classification propagation needed for production-readiness evidence.

Current live truth after commit `ffe34b4`:
- `/chat/test` returns provider `error_type` correctly:
  - Gemini: `status=error`, `code=400`, `error_type=invalid_key`
  - OpenRouter: `status=error`, `code=401`, `error_type=invalid_key`
  - VM worker: `status=ok`
- `/health/deep` still maps provider rows through `modules.health_service._map_chat_provider_result(...)` and currently drops `error_type`.
- Dashboard status already carries raw `test_chat_providers(...)` rows and should preserve classification metadata unless your verification proves otherwise.

## Hard Constraints

- Do not remove or relocate `bridge.py` circuit breaker wiring.
- Do not add backup or snapshot modules like `modules/chat_service_087c5da.py`.
- Do not replay old broad `modules/chat_service.py` hunks. Provider classification, OpenRouter model fallback, plural key rotation, and VM recent-success invalidation are already integrated in `ffe34b4`.
- Do not touch secrets or print raw API keys.
- Keep bridge routes thin. Any change should stay in service modules/tests unless live evidence proves otherwise.

## Requested Work

1. Inspect current `modules/health_service.py` and tests.
2. If still missing, propagate `error_type` from chat provider results into `/health/deep` provider rows.
3. Add/update focused tests in `tests/test_health_deep.py` proving `error_type` survives mapping for Gemini/OpenRouter failures.
4. If dashboard already preserves provider `error_type`, leave it alone. If not, add the smallest service/test change needed.
5. Run focused tests:
   - `python -m pytest tests/test_health_deep.py tests/test_chat_service.py tests/test_dashboard_module.py -q`
6. Return only a minimal diff. If no code change is needed, return a report with the current evidence and no diff.

## Success Evidence

- A minimal diff against `ffe34b4`.
- No `bridge.py` circuit-breaker deletion.
- No backup files.
- Tests passing.
- Live expected shape: `/health/deep.providers.gemini.error_type == "invalid_key"` and `/health/deep.providers.openrouter.error_type == "invalid_key"` when current invalid credentials are present.

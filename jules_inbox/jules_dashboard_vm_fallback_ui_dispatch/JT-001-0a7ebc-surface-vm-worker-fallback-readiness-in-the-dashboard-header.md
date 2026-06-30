# Jules Worker Packet JT-001-0a7ebc

- instance_index: 1
- status: ready_for_review
- task_type: code_health
- source: inline
- fingerprint: 0a7ebc3a5878
- repo_path: C:\Users\abdul\jules-bridge

## Objective
Complete exactly this Jules card: Surface vm_worker fallback readiness in the dashboard header and comm link so the UI does not look broken when Gemini/OpenRouter are failing but chat is functional through the VM worker

## Task Details
- File: dashboard-ui/src/App.jsx
- Issue: Surface vm_worker fallback readiness in the dashboard header and comm link so the UI does not look broken when Gemini/OpenRouter are failing but chat is functional through the VM worker
- Language: javascript
- Rationale: Current live /dashboard/status includes providers.vm_worker.status = ok and /chat works through model_used vm/jules-worker, but the dashboard header only shows GEMINI: ERROR and OPENROUTER: ERROR. This makes the product look broken even though production chat is functional through the VM fallback. The dashboard should truthfully show local provider failures and also clearly show VM fallback readiness.

## Operating Rules
- Work on one card only; do not opportunistically refactor unrelated code.
- Do not stop at a plan or ask for plan approval; plan briefly in the report and proceed unless a hard blocker prevents work.
- Preserve existing behavior unless the card explicitly asks for behavior change.
- Run the narrowest relevant verification first, then the broader suite if practical.
- Record concrete evidence: commands, test result summaries, hashes, screenshots, or PR links.
- Do not reveal private chain-of-thought. Use a concise rationale, decision log, and evidence checklist instead.
- If blocked, write the blocker, attempted evidence, and the exact next question.

## Completion report
Write a short report with:
- what changed
- verification performed
- files touched
- whether a PR/commit was created
- next action or blocker

## Raw Card Excerpt
```text
Code Health Improvement Task
You are a production-focused Jules dashboard worker. Implement only the narrow dashboard readiness clarity fix described here. Do not refactor unrelated source. Do not print or persist raw secrets.

Task Details
File: dashboard-ui/src/App.jsx Issue: Surface vm_worker fallback readiness in the dashboard header and comm link so the UI does not look broken when Gemini/OpenRouter are failing but chat is functional through the VM worker

Language: javascript

Rationale: Current live /dashboard/status includes providers.vm_worker.status = ok and /chat works through model_used vm/jules-worker, but the dashboard header only shows GEMINI: ERROR and OPENROUTER: ERROR. This makes the product look broken even though production chat is functional through the VM fallback. The dashboard should truthfully show local provider failures and also clearly show VM fallback readiness.

Implementation requirements:
1. In dashboard-ui/src/App.jsx, extend default provider state to include vm_worker with status no_key/offline-safe fallback.
2. Add a compact header badge such as VM CHAT: OK / OFFLINE / ERROR based on providers.vm_worker.status. Use success styling when ok, danger for error/offline, neutral for no_key/unknown.
3. In the Comm Link panel header or near the model selector, show the active route/readiness summary so operators can tell that chat will use VM fallback when Gemini/OpenRouter are down. Keep it compact and operational, not marketing copy.
4. Preserve truthful GEMINI and OPENROUTER badges. Do not hide their error states.
5. Avoid layout overflow in the header at desktop width and keep mobile/short widths readable. If needed, let badges wrap cleanly.
6. If CSS changes are needed, scope them in dashboard-ui/src/index.css and keep the existing dark operations-console style.
7. Do not edit backend code or generated dispatch/runtime state.

Verification expected from Jules:
- Run dashboard-ui lint/build if available.
- Report files changed and exact test/build commands/results.
Ready for review
```

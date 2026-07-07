# TIU Workbench Packet

- objective: Build the next polished dashboard and model-bridge UI slice.
- scope: dashboard
- mode: design_review
- model_lane: alliance
- cloud_sync_required: true

## Lanes

- Jules: creator and actual-change owner
- Google terminal agent: antigravity_cli implementer/reviewer support
- Codex: local dependency, route, test, and browser verification owner

## Target Files

- dashboard-ui/src/App.jsx
- dashboard-ui/src/dashboardModel.js
- dashboard-ui/src/index.css
- modules/dashboard_module.py
- tests/test_dashboard_module.py

## Readiness

- alliance: ready (8/8 switchboard gates passed; Jules creator and antigravity_cli implementer are assigned.)
- codebase: 78 routes, 35 modules, 46 tests
- cloud_sync: blocked on master -> origin/master; 14 dirty

## Operator Gates

- BLOCKED: cloud_sync:dirty_worktree
- WARNING: live_work_gated

## Next Actions

1. Review this packet and target scope.
2. Keep live Jules launch and Google edit prompts disabled unless explicitly approved.
3. Implement locally, run focused tests, then browser QA on the Jules dashboard.
4. Resolve cloud sync blockers before claiming push/simultaneous sync complete.
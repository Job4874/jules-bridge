# Cloud Publish Packet

- generated_at_utc: 2026-07-05T20:46:12.864538+00:00
- objective: final pre-commit cloud publish audit
- state: blocked
- branch: master
- upstream: origin/master
- ahead_behind: 0 / 0
- dirty_count: 48
- blockers: dirty_worktree
- warnings: remote_tracking_stale

## Change Families
- Bridge routes: 2 files (2 publish candidates)
  - bridge.py
  - modules/__init__.py
- Backend modules: 10 files (10 publish candidates)
  - modules/chat_service.py
  - modules/dashboard_module.py
  - modules/inbox_service.py
  - modules/alliance_switchboard.py
  - modules/antigravity_cli.py
- Dashboard UI: 3 files (3 publish candidates)
  - dashboard-ui/src/App.jsx
  - dashboard-ui/src/dashboardModel.js
  - dashboard-ui/src/index.css
- Tests: 11 files (11 publish candidates)
  - tests/test_bridge_routes.py
  - tests/test_chat_service_pro.py
  - tests/test_dashboard_module.py
  - tests/test_inbox_service.py
  - tests/test_alliance_switchboard.py
- Context and memory: 8 files (8 publish candidates)
  - UBIQUITOUS_LANGUAGE.md
  - context/02_architecture.md
  - context/05_gotchas.md
  - context/06_progress_tracker.md
  - context/07_library_docs.md
- Config surface: 1 files (1 publish candidates)
  - .env.example
- Evidence packets: 12 files (12 publish candidates)
  - jules_inbox/jules_dispatch/JULES_PREFLIGHT.json
  - jules_inbox/alliance/ALLIANCE_CREATOR_JULES.md
  - jules_inbox/alliance/ALLIANCE_IMPLEMENTER_GOOGLE_TERMINAL.md
  - jules_inbox/alliance/ALLIANCE_SWITCHBOARD_STATE.json
  - jules_inbox/alliance/ALLIANCE_SWITCHING_POLICY.md
- Other: 1 files (1 publish candidates)
  - .gitignore

## Publish Candidates
- include: 48
- exclude_or_review_separately: 0

## Review Commands
- Review: `git status --short`
- Stage reviewed candidates: `git add -- ".env.example" ".gitignore" "UBIQUITOUS_LANGUAGE.md" "bridge.py" "context/02_architecture.md" "context/05_gotchas.md" "context/06_progress_tracker.md" "context/07_library_docs.md" "dashboard-ui/src/App.jsx" "dashboard-ui/src/dashboardModel.js" "dashboard-ui/src/index.css" "implementation_plan.md" "jules_inbox/jules_dispatch/JULES_PREFLIGHT.json" "memory/general.md" "memory/test_evidence.json" "modules/__init__.py" "modules/chat_service.py" "modules/dashboard_module.py" "modules/inbox_service.py" "tests/test_bridge_routes.py" "tests/test_chat_service_pro.py" "tests/test_dashboard_module.py" "tests/test_inbox_service.py" "jules_inbox/alliance/ALLIANCE_CREATOR_JULES.md" "jules_inbox/alliance/ALLIANCE_IMPLEMENTER_GOOGLE_TERMINAL.md" "jules_inbox/alliance/ALLIANCE_SWITCHBOARD_STATE.json" "jules_inbox/alliance/ALLIANCE_SWITCHING_POLICY.md" "jules_inbox/gemini/ANTIGRAVITY_PREFLIGHT.json" "jules_inbox/gemini/GEMINI_PREFLIGHT.json" "jules_inbox/proof/AGENT_POINT_OF_VIEW_PROOF.md" "jules_inbox/proof/ANTIGRAVITY_CLI_PROOF.json" "jules_inbox/proof/COLLABORATION_PROOF.json" "jules_inbox/tiu_workbench/TIU_WORKBENCH_PACKET_20260705T201807.md" "jules_inbox/tiu_workbench/TIU_WORKBENCH_STATE.json" "modules/alliance_switchboard.py" "modules/antigravity_cli.py" "modules/cloud_sync.py" "modules/codebase_analyzer.py" "modules/collaboration_proof.py" "modules/gemini_cli.py" "modules/tiu_workbench.py" "tests/test_alliance_switchboard.py" "tests/test_antigravity_cli.py" "tests/test_cloud_sync.py" "tests/test_codebase_analyzer.py" "tests/test_collaboration_proof.py" "tests/test_gemini_cli.py" "tests/test_tiu_workbench.py"`
- Commit: `git commit -m "feat: strengthen Jules Google bridge dashboard"`
- Verify: `python -m pytest tests/ -q`
- Dashboard lint (cwd: dashboard-ui): `npm run lint`
- Dashboard build (cwd: dashboard-ui): `npm run build`
- Push after commit: `git push origin master`

## Safety
- This packet did not run git add, git commit, git fetch, git pull, or git push.
- Generated/noisy files should be reviewed separately before staging.

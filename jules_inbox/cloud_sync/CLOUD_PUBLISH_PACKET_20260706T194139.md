# Cloud Publish Packet

- generated_at_utc: 2026-07-06T19:41:37.992730+00:00
- objective: Publish and synchronize the current Jules Bridge dashboard/model-agent work.
- state: blocked
- branch: master
- upstream: origin/master
- ahead_behind: 0 / 0
- dirty_count: 36
- blockers: dirty_worktree
- warnings: none

## Change Families
- Bridge routes: 1 files (1 publish candidates)
  - bridge.py
- Backend modules: 1 files (1 publish candidates)
  - modules/cloud_sync.py
- Dashboard UI: 5 files (5 publish candidates)
  - dashboard-ui/package.json
  - dashboard-ui/src/App.jsx
  - dashboard-ui/src/dashboardModel.js
  - dashboard-ui/src/dashboardModel.test.js
  - dashboard-ui/src/index.css
- Tests: 3 files (3 publish candidates)
  - tests/test_bridge_routes.py
  - tests/test_cloud_sync.py
  - tests/test_dashboard_cache.py
- Context and memory: 3 files (3 publish candidates)
  - context/06_progress_tracker.md
  - memory/general.md
  - memory/test_evidence.json
- Evidence packets: 14 files (14 publish candidates)
  - jules_inbox/cloud_sync/CLOUD_PUBLISH_STATE.json
  - jules_inbox/jules_dispatch/JULES_COT_LEDGER.json
  - jules_inbox/jules_dispatch/JULES_COT_LEDGER.md
  - jules_inbox/jules_dispatch/JULES_CYCLE_STATE.json
  - jules_inbox/jules_dispatch/JULES_LAUNCH_STATE.json
- Other: 9 files (9 publish candidates)
  - .codex/tmp_app_diff.txt
  - .codex/verification/dashboard-mobile-current-crop.png
  - .codex/verification/dashboard-mobile-current.png
  - .codex/verification/dashboard-tunnel-desktop-after.png
  - .codex/verification/dashboard-tunnel-desktop-before.png

## Publish Candidates
- include: 36
- exclude_or_review_separately: 0

## Review Commands
- Review: `git status --short`
- Stage reviewed candidates: `git add -- "bridge.py" "context/06_progress_tracker.md" "dashboard-ui/package.json" "dashboard-ui/src/App.jsx" "dashboard-ui/src/dashboardModel.js" "dashboard-ui/src/dashboardModel.test.js" "dashboard-ui/src/index.css" "jules_inbox/cloud_sync/CLOUD_PUBLISH_STATE.json" "jules_inbox/jules_dispatch/JULES_COT_LEDGER.json" "jules_inbox/jules_dispatch/JULES_COT_LEDGER.md" "jules_inbox/jules_dispatch/JULES_CYCLE_STATE.json" "jules_inbox/jules_dispatch/JULES_LAUNCH_STATE.json" "jules_inbox/tiu_workbench/TIU_WORKBENCH_STATE.json" "memory/general.md" "memory/test_evidence.json" "modules/cloud_sync.py" "tests/test_bridge_routes.py" "tests/test_cloud_sync.py" "tests/test_dashboard_cache.py" ".codex/tmp_app_diff.txt" ".codex/verification/dashboard-mobile-current-crop.png" ".codex/verification/dashboard-mobile-current.png" ".codex/verification/dashboard-tunnel-desktop-after.png" ".codex/verification/dashboard-tunnel-desktop-before.png" ".codex/verification/dashboard-tunnel-mobile.png" "__tmp_App.diff" "__tmp_Model.diff" "__tmp_cloud.diff" "jules_inbox/cloud_sync/CLOUD_PUBLISH_PACKET_20260705T231101.md" "jules_inbox/cloud_sync/CLOUD_PUBLISH_PACKET_20260706T064710.md" "jules_inbox/cloud_sync/CLOUD_PUBLISH_PACKET_20260706T064903.md" "jules_inbox/cloud_sync/CLOUD_PUBLISH_PACKET_20260706T193951.md" "jules_inbox/tiu_workbench/TIU_WORKBENCH_PACKET_20260706T030534.md" "jules_inbox/tiu_workbench/TIU_WORKBENCH_PACKET_20260706T030612.md" "jules_inbox/tiu_workbench/TIU_WORKBENCH_PACKET_20260706T041408.md" "jules_inbox/cloud_sync/CLOUD_PUBLISH_PACKET_20260706T194139.md"`
- Commit: `git commit -m "feat: strengthen Jules Google bridge dashboard"`
- Verify: `python -m pytest tests/ -q`
- Dashboard lint (cwd: dashboard-ui): `npm run lint`
- Dashboard build (cwd: dashboard-ui): `npm run build`
- Push after commit: `git push origin master`

## Safety
- This packet did not run git add, git commit, git fetch, git pull, or git push.
- Generated/noisy files should be reviewed separately before staging.

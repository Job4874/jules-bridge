# Jules Automation Dashboard Public Packet - 2026-06-30

## Boundary

Codex has prepared the GitHub/bridge connection slice. Jules owns the next production implementation pass. Do not assume the private operator inventory is present in this public repo; refresh account-level repo data through authenticated GitHub tooling when needed.

## Current Remote Base

- Branch: `codex/repo-context-guard-dashboard`
- Purpose: repo context guard, dashboard connection surface, and safe Jules CLI resolution
- PR: draft PR for review/continuation

## What Is Ready

- Protected `GET /repo/context-guard` returns bounded local Git repo inventory, provenance labels, collisions, and guardrails.
- `GET /dashboard/status` returns only compact repo context: counts, severity counts, truncated collision rows, guardrails, cache age. It must not expose repo sample names, full paths, env keys, or private inventory.
- Dashboard UI has a compact Repo Context Guard panel for connection health and top collision visibility.
- `modules/repo_context_guard.py` detects:
  - duplicate remotes
  - duplicate repo/package names
  - port collisions
  - node/server/worker ref collisions
  - workspace/local cross-project dependencies
  - dependency version drift
- Private inventory handoffs matching `jules_inbox/JULES_AUTOMATION_GITHUB_DASHBOARD_HANDOFF_*.md` are intentionally ignored.

## Jules Next Implementation Pass

1. Re-read `context/02_architecture.md`, `context/05_gotchas.md`, and this packet.
2. Verify the PR branch state and tests before editing.
3. Add authenticated GitHub inventory ingestion as a protected connection source, not as public dashboard raw data.
4. Extend the dashboard only with compact counts and status, keeping private repo names and full inventory behind protected routes.
5. Add math/analysis capability context before claiming production-grade analytics:
   - identify the owning repo/module for each formula or analytics worker
   - bind formulas to evidence-backed tests or fixtures
   - prevent copying math logic into unrelated project extensions unless explicitly requested
6. Before launching or dispatching workers, check repo-context collisions and require operator approval for shared ports, shared nodes, cross-project dependencies, or extension-to-extension coupling.
7. Keep `/jules/*` launch/fleet/watch routes dry-run-first unless the operator explicitly sends `dry_run=false`.

## Verification To Preserve

- `python -m pytest tests/ -q`
- `npm.cmd run build` in `dashboard-ui`
- Protected repo guard smoke with auth
- Dashboard status smoke proving compact summary omits `sample_repos`


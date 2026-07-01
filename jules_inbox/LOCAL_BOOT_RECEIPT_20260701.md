# Local Jules Boot Receipt - 2026-07-01T18:48Z

Status: **JULES ONLINE** — boot verified and all core checks passed.

## Evidence

| Check | Result |
| --- | --- |
| Bridge `/ping` | HTTP 200 — Jules Bridge Online |
| Bridge `/health` | HTTP 200 — uptime ~32m, identity School-PC-RAM-15GB |
| AKC readiness | `ready=true`, checkpoint status ready |
| Jules REST preflight | `ready=true`, source `sources/github/Job4874/jules-bridge` |
| Tentacles manifest | HTTP 200 (authenticated) |
| Chat provider | `healthy=true`, vm provider ok |
| Dashboard API | HTTP 200 — bridge running, GCP 1/1 online |
| Dashboard UI | HTTP 200 on `127.0.0.1:5173` |
| GCP worker boot | Spawned `Boot-GCP-Worker.ps1` in background |

## Endpoints

- **Bridge (local):** http://127.0.0.1:5000
- **Dashboard UI:** http://127.0.0.1:5173
- **Mission Control (static):** `dashboard-ui/dist/index.html`

## Current blockers / caveats

- **Memory pressure:** 96.7% RAM — avoid heavy local launch loops until memory is freed.
- **ngrok tunnel:** Public URL `parade-marrow-pulp.ngrok-free.dev` returned 404 on `/ping`; local bridge remains fully usable at 127.0.0.1:5000.
- **Jules CLI:** Not on PATH; REST API path is configured and preferred (`JULES_USE_REST_API=1`).

## Next steps (from WAKE_UP.txt)

1. Read inbox mission files via `POST /inbox/read`
2. Monday mission tickets 007 → 008 → 009 in order
3. Reply via `POST /inbox/write` → `JULES_RESPONSE.md`

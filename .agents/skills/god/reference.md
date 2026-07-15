# /god — Reference

## Key files

| Path | Role |
|------|------|
| `Setup-NoAdminGuest.cmd` | One-click full boot (guest / no-admin) |
| `Run-JulesBridge.cmd` | Bridge + ngrok via `start.py` |
| `Open-JulesCLI.cmd` | Jules CLI with user-local shim |
| `Boot-AlwaysOn.cmd` | Setup + start (interactive) |
| `Boot-AlwaysOn-Silent.cmd` | Logon hook (hidden) |
| `scripts/Setup-NoAdminGuest.ps1` | Install, auth restore, startup |
| `scripts/Ensure-UserPersist.ps1` | Auth/.env backup + restore |
| `scripts/Install-AlwaysOnBackdoor.ps1` | Always-on bridge + optional black screen |
| `scripts/Start-AlwaysOnAtLogon.ps1` | Logon: restore → bridge → monitor off |
| `scripts/setup-jules.ps1` | Node + `@google/jules` (user prefix) |
| `start.py` | Flask + ngrok + tunnel watchdog |
| `bridge.py` | Flask API (local only if no ngrok) |

## Persistence locations

| Store | Contents |
|-------|----------|
| `%LOCALAPPDATA%\JulesBridge\` | Auth backup, `.env`, `manifest.json`, `user-env.cmd` |
| `user-persist/` (repo mirror) | Same data; survives some guest profile wipes |
| `%USERPROFILE%\.npm-packages\` | Jules CLI + global npm tools |
| `%LOCALAPPDATA%\Programs\Python\Python312\` | Typical user Python install |
| `%APPDATA%\jules`, `%LOCALAPPDATA%\jules` | Jules CLI auth tokens |

## URLs and endpoints

| Name | Value |
|------|-------|
| Local bridge | `http://127.0.0.1:5000` |
| Health ping | `GET /ping` |
| Reserved ngrok domain | `parade-marrow-pulp.ngrok-free.dev` |
| Remote ping | `GET https://parade-marrow-pulp.ngrok-free.dev/ping` |
| ngrok header | `ngrok-skip-browser-warning: true` |

## Environment

Copy `.env.example` → `.env` (or use persisted copy in `%LOCALAPPDATA%\JulesBridge\.env`).

Common vars:

- `BRIDGE_TOKEN=JULES-SECURE-999` — API auth header
- `JULES_API_KEY`, `JULES_SOURCE`, `JULES_USE_REST_API` — optional REST routes

## Tunnel watchdog

`start.py` writes `jules_inbox/TUNNEL_HEALTH.json` every 60s. After 3 failures it reconnects ngrok. After 3 reconnect failures it writes `TUNNEL_BLOCKER.md` and may git-commit `[TUNNEL_DEAD]`.

## Common failures

| Symptom | Fix |
|---------|-----|
| `jules: CommandNotFoundException` | Run `Setup-NoAdminGuest.cmd` |
| `python was not found` | Use full path to `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` or install Python "for me only" |
| Local ping OK, ngrok 404 | Restart via `Run-JulesBridge.cmd` (kills stale port 5000 + ngrok) |
| Auth lost after reboot | Run `Setup-NoAdminGuest.cmd` (restores from `user-persist/`) |
| Guest profile wiped | Re-run setup; mirror in `user-persist/` may still have auth |

## RAM note

Target host may be labeled "64GB RAM PC". Verify with:

```powershell
[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
```

Bridge offload logic also reads pressure via `modules/vm_manager.py` when routing heavy work.

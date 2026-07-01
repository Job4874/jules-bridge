# Local Jules Boot Receipt - 2026-07-01T19:10Z

Status: **JULES ONLINE — local + remote**

## Evidence

| Check | Result |
| --- | --- |
| Ngrok authtoken | Persisted to repo `.env`, `~/.jules/.env`, `~/.jules/ngrok_authtoken`, ngrok CLI |
| Bridge local | http://127.0.0.1:5000 — HTTP 200 |
| Bridge remote | https://parade-marrow-pulp.ngrok-free.dev/ping — HTTP 200 |
| Token mirror | `BRIDGE_TOKEN` + `LOCAL_BRIDGE_TOKEN` synced |

## Persistence

`Run-JulesBridge.cmd` runs `Ensure-JulesSecrets.ps1` before every launch. Secrets restore from `~/.jules/.env` if repo `.env` is reset.

## Note

`start.py` now retries public `/ping` for up to ~15s after ngrok connect to avoid false 404 on cold tunnel bind.

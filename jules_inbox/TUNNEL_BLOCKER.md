# Ngrok tunnel blocker — actionable fix

Status: remote tunnel down until ngrok authtoken is configured on this machine.

## Root cause

`ERR_NGROK_4018` — ngrok CLI has no authtoken. Local bridge at http://127.0.0.1:5000 is fine; public URL returns 404.

## One-time fix (token persists after this)

1. Get authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
2. Run from repo root:

```powershell
.\scripts\Ensure-JulesSecrets.ps1 -NgrokAuthtoken "YOUR_TOKEN_HERE"
```

Or double-click `Ensure-JulesSecrets.cmd` and paste when prompted.

3. Restart remote bridge:

```cmd
Run-JulesBridge.cmd
```

4. Verify from anywhere:

```powershell
.\scripts\Reach-SchoolBridge.ps1
```

## What persists automatically

| Secret | Repo `.env` | `~/.jules/.env` mirror | `~/.jules/ngrok_authtoken` | ngrok CLI |
|--------|-------------|------------------------|----------------------------|-----------|
| BRIDGE_TOKEN | yes | yes | — | — |
| LOCAL_BRIDGE_TOKEN | yes | yes | — | — |
| NGROK_AUTHTOKEN | yes | yes | yes | yes |

`Run-JulesBridge.cmd` runs `Ensure-JulesSecrets.ps1` before every launch so tokens are restored from the mirror if repo `.env` is ever reset.

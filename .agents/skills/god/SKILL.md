---
name: god
description: >-
  Boots Jules Bridge, Jules CLI, and ngrok always-on remote access on Windows without
  admin (guest-safe). Restores auth, registers logon startup, keeps PC online with
  monitor off. Use when the user says /god, god mode, boot bridge, always-on backdoor,
  black screen boot, or Jules Bridge startup on the 64GB RAM PC.
disable-model-invocation: true
---

# /god — Jules God-Mode Boot

## User directive (verbatim)

boot up brige and jules cli and boot up back door to the pc 64ram to alwasy stay oline eney if skren is power done on if turned of boot back up comp but not scren keep black

## Purpose

Bring the **local Jules Bridge**, **Jules CLI auth**, and **ngrok remote tunnel** online on a Windows host (guest / no-admin OK). Persist credentials across reboots. Auto-start at logon with **monitor off, PC still running**.

## When to run

Invoke this skill when the user types **`/god`** or asks to boot/start the bridge, Jules CLI, always-on tunnel, or black-screen headless operation.

## Copy-paste payload (zero prompts)

Paste this **entire line** into PowerShell:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; $r='c:\jules-bridge-master'; if (-not (Test-Path "$r\bridge.py")) { $r=@('c:\jules-bridge-master',"$env:USERPROFILE\jules-bridge-master")|?{Test-Path "$_\bridge.py"}|Select -First 1 }; if (-not $r){throw 'Put jules-bridge at c:\jules-bridge-master first'}; & "$r\scripts\God-Paste.ps1"
```

Black screen when done:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; & "c:\jules-bridge-master\scripts\God-Paste.ps1" -BlackScreenNow
```

## Ghost mode (code `48741721`) — use before leaving PC

Full boot + black screen + mesh + laptop connect card. Paste in **terminal** (not Cursor `.cmd` click):

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; & "c:\jules-bridge-master\scripts\Ghost-Ready.ps1" -Code 48741721 -UnlockPassword "YOUR_PASSWORD"
```

Or File Explorer double-click **`48741721.cmd`** (add `-UnlockPassword` by editing `GHOST-READY.txt` one-liner instead for lock).

See **`GHOST-READY.txt`** and **`LAPTOP-CONNECT.txt`** in repo root.

### Laptop Cursor -> this PC (while ghost runs)

School PC exposes: `https://parade-marrow-pulp.ngrok-free.dev` with `Authorization: Bearer JULES-SECURE-999`

On **laptop**, paste **`LAPTOP-CONNECT.txt`** in PowerShell after cloning jules-bridge.

Card file written at ghost boot: `jules_inbox/LAPTOP_CURSOR_CONNECT.json`

## Ghost mode (legacy one-liner)

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; & "c:\jules-bridge-master\scripts\Ghost-Mode.ps1" -Code 48741721 -UnlockPassword "YOUR_OPERATOR_PASSWORD"
```

Or double-click **`48741721.cmd`** in File Explorer (do not open `.cmd` in Cursor editor).

### Ghost lock (password-protected)

Once locked, ghost state **must not stop** and always-on **must not be disabled** unless the operator password is entered. Password is stored as a hash under `%LOCALAPPDATA%\JulesBridge\ghost_state.json` only — never in the repo.

**Unlock (stops bridge + removes logon startup):**

```powershell
& "c:\jules-bridge-master\scripts\Ghost-Unlock.ps1" -Password "YOUR_OPERATOR_PASSWORD"
```

### Host identity for remote Jules agents

When any remote agent or operator connects, **always introduce this host**:

- **Location:** school
- **RAM:** 64 GB
- **Host ID:** `school-64gb`

Fetch live identity:

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/host/identity" -Headers @{ Authorization = "Bearer $env:BRIDGE_TOKEN" }
```

Fleet file: `jules_inbox/HOST_IDENTITY.json` (written when ghost locks).

GitHub CLI auth (`.config/gh`, `GitHub CLI`) is backed up with Jules auth via `Ensure-UserPersist.ps1`.

Source: `scripts/God-Paste.ps1` — no `Read-Host`, skips interactive `jules login` (restores saved auth only).

## Repo entry points (use these — do not reinvent)

| Action | Command |
|--------|---------|
| **Full boot (preferred)** | **File Explorer:** double-click `GOD-BOOT.cmd` or `GOD-BOOT.ps1` |
| Alt full boot | Double-click `Setup-NoAdminGuest.cmd` (do **not** click `.cmd` links in Cursor chat) |
| Bridge + ngrok only | `Run-JulesBridge.cmd` |
| Jules CLI shell | `Open-JulesCLI.cmd` |
| Always-on + startup | `Boot-AlwaysOn.cmd` |
| Silent logon hook | `Boot-AlwaysOn-Silent.cmd` (Startup folder) |

PowerShell equivalents (from repo root):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Setup-NoAdminGuest.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Install-AlwaysOnBackdoor.ps1 -StartNow
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Setup-NoAdminGuest.ps1 -BlackScreenNow
```

## Agent workflow

Copy this checklist and execute in order:

```
/god Progress:
- [ ] Step 1: Locate repo root (contains bridge.py, Run-JulesBridge.cmd)
- [ ] Step 2: Check current health (local ping, tunnel ping, jules CLI)
- [ ] Step 3: Run Setup-NoAdminGuest (restore auth, install tools, startup)
- [ ] Step 4: Verify bridge + tunnel + Jules CLI
- [ ] Step 5: Report URLs and what survives reboot
```

### Step 1 — Repo root

Default: directory containing `bridge.py`. On this project that is `jules-bridge-master/`.

### Step 2 — Health check (read-only first)

```powershell
Invoke-RestMethod http://127.0.0.1:5000/ping
Invoke-RestMethod https://parade-marrow-pulp.ngrok-free.dev/ping -Headers @{"ngrok-skip-browser-warning"="true"}
Test-Path "$env:USERPROFILE\.npm-packages\bin\jules.exe"
```

Expected local response: `{"status":"Jules Bridge Online"}`.

If `jules` is missing (`CommandNotFoundException`), Step 3 installs it user-locally.

### Step 3 — Boot (no admin required)

Run **`Setup-NoAdminGuest.cmd`** or:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Setup-NoAdminGuest.ps1
```

This script (via `scripts/Ensure-UserPersist.ps1`):

- Restores Jules auth + `.env` from `%LOCALAPPDATA%\JulesBridge\` and `user-persist/`
- Installs portable Node + `@google/jules` under `%USERPROFILE%\.npm-packages\`
- Runs `pip install --user -r requirements.txt`
- Opens **`jules login`** in browser if auth missing
- Registers **Startup folder** shortcut (no admin)
- Starts bridge via `start.py` (Flask + ngrok + tunnel watchdog)

**If shell execution is blocked:** tell the operator to open **File Explorer** → `jules-bridge-master` → double-click **`GOD-BOOT.cmd`** (not a chat link). Paste terminal output back.

**Cursor IDE:** clicking `.cmd` in chat opens the editor and fails with "Unable to resolve resource". Always run from Explorer or integrated terminal instead.

**Python path** (when `python` not on PATH):

`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`

### Step 4 — Verify

| Check | Pass criteria |
|-------|----------------|
| Local bridge | `GET http://127.0.0.1:5000/ping` → 200 |
| Remote tunnel | `GET https://parade-marrow-pulp.ngrok-free.dev/ping` → 200 |
| Jules CLI | `jules version` or `%USERPROFILE%\.npm-packages\bin\jules.exe version` → exit 0 |
| Auth persisted | `%LOCALAPPDATA%\JulesBridge\manifest.json` exists after login |
| Logon startup | Startup shortcut `JulesBridge-AlwaysOn.lnk` exists |

Bridge logs: `bridge.log`. Always-on log: `%LOCALAPPDATA%\JulesBridge\always_on.log`.

### Step 5 — Report to operator

Always include:

- Local URL: `http://127.0.0.1:5000`
- Remote URL: `https://parade-marrow-pulp.ngrok-free.dev`
- Auth store: `%LOCALAPPDATA%\JulesBridge\` + `user-persist/`
- Re-run after guest profile wipe: `Setup-NoAdminGuest.cmd`
- Admin-only gap: global sleep disable needs admin; user keep-awake runs without admin

## Black screen + reboot behavior

- **Monitor off now:** `-BlackScreenNow` on setup scripts, or logon hook in `scripts/Start-AlwaysOnAtLogon.ps1`
- **PC stays online:** bridge + ngrok keep running; display off does not stop bridge
- **After reboot:** Startup shortcut runs `Boot-AlwaysOn-Silent.cmd` → restore auth → start bridge → turn monitor off
- **BIOS (operator, needs physical access):** set **Restore on AC Power Loss → Power On** so the box boots after power loss; screen stays black via logon script

## No-admin vs admin

| Works without admin | Needs admin |
|---------------------|-------------|
| Jules CLI + `jules login` | Global `powercfg` sleep off |
| Bridge + ngrok (`start.py`) | Scheduled task (Startup folder used instead) |
| Startup folder auto-run | Some guest GPO sleep locks |
| Monitor off API | BIOS auto-power-on |

## Escalation

Escalate only when:

- `jules login` browser auth cannot complete
- ngrok tunnel dead after 3 watchdog reconnects (check `jules_inbox/TUNNEL_HEALTH.json`)
- Python not installed at all (operator must install Python 3.12 **for me only** from python.org)

Escalation format: blocker class, commands run, exact error, smallest operator action.

## Additional resources

- Paths, tokens, env vars: [reference.md](reference.md)

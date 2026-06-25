# Jules Bridge

```
        ~~~  ONE URL  ~~~
           \   |   /
    mail -----(O)----- shell
           /   |   \
    inbox ----+---- fs read/write
              |
         ui / eyes / hand / voice
```

**The octopus isn't decoration — it's the architecture.**

Jules sits in the cloud. The bridge is the body. Each HTTP route is a **tentacle**: a distinct reach into your Windows host. One ngrok URL grants all of them. No bridge URL, no access.

## Setup

```powershell
pip install -r requirements.txt
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

Copy `.env.example` to `.env` and add a Gmail App Password for the **mail** tentacle.

## Run

**Recommended — dedicated CMD window (stays up when you scroll in Cursor):**

Double-click or run:

```powershell
C:\Users\abdul\.jules\Open-JulesBridge-Window.cmd
```

This opens a green **“Jules Bridge - KEEP THIS WINDOW OPEN”** terminal. Do not close it while Jules is working. Logs also append to `bridge.log`.

**Alternative — inside current terminal:**

```powershell
cd C:\Users\abdul\.jules
$env:PYTHONIOENCODING='utf-8'
python start.py
```

## Tentacles (endpoints)

| Tentacle | Route | Reach |
|----------|-------|-------|
| pulse | `GET /ping` | Health check |
| manifest | `GET /tentacles` | List all tentacles |
| session_log | `GET /session/log` | Audit recent Jules requests |
| oracle_status | `GET /oracle/status` | Oracle health, blockers, telemetry |
| oracle_build | `POST /oracle/build-deploy` | Build + deploy + verify |
| codex_handover | `GET /codex/handover` | Index Codex handover files on host |
| list | `POST /fs/list` | List directory |
| tail | `POST /fs/tail` | Tail log/CSV |
| grep | `POST /fs/grep` | Search files for gate strings |
| shell | `POST /shell` | Run PowerShell |
| read | `POST /fs/read` | Read a file |
| write | `POST /fs/write` | Write a file |
| inbox_read | `POST /inbox/read` | Read `jules_inbox/` message |
| inbox_write | `POST /inbox/write` | Write `jules_inbox/` reply |
| eyes | `GET /ui/screenshot` | Desktop screenshot (base64) |
| hand | `POST /ui/click` | Mouse click |
| voice | `POST /ui/type` | Keyboard input |
| mail | `POST /notify/email` | Email operator (Gmail → iCloud) |

**Access model:** the public ngrok URL *is* the key. Guard it like a password.

## Inbox (operator ↔ Jules)

- Operator writes: `jules_inbox/OPERATOR_RESPONSE.md`
- Jules replies: `POST /inbox/write` → `JULES_RESPONSE.md`
- Or use `/fs/read` and `/fs/write` for any path

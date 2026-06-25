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

Jules sits in the cloud. The bridge is the body. Each HTTP route is a distinct reach into your Windows host. One ngrok URL grants all of them. No bridge URL, no access.

## Setup

```powershell
pip install -r requirements.txt
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

Copy `.env.example` to `.env` and add a Gmail App Password for the mail endpoint.

## Run

Recommended dedicated CMD window:

```powershell
C:\Users\abdul\.jules\Open-JulesBridge-Window.cmd
```

This opens a "Jules Bridge - KEEP THIS WINDOW OPEN" terminal. Do not close it while Jules is working. Logs also append to `bridge.log`.

Alternative inside the current terminal:

```powershell
cd C:\Users\abdul\.jules
$env:PYTHONIOENCODING='utf-8'
python start.py
```

## Tentacles

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
| shell | `POST /shell` | Run PowerShell, cmd.exe, or Git Bash |
| read | `POST /fs/read` | Read a file |
| write | `POST /fs/write` | Write a file |
| inbox_read | `POST /inbox/read` | Read `jules_inbox/` message |
| inbox_write | `POST /inbox/write` | Write `jules_inbox/` reply |
| eyes | `GET /ui/screenshot` | Desktop screenshot (base64) |
| hand | `POST /ui/click` | Mouse click |
| voice | `POST /ui/type` | Keyboard input |
| mail | `POST /notify/email` | Email operator (Gmail to iCloud) |

Access model: the public ngrok URL is the key. Guard it like a password. No auth layer is currently enforced.

## Request Contract

POST routes expect a JSON object. Missing bodies are treated as `{}` so validators can return field-specific `400` errors. Malformed JSON or a non-JSON body returns:

```json
{"error": "Malformed JSON or missing Content-Type header."}
```

Common error mappings:

| Status | Meaning |
|--------|---------|
| `400` | Invalid input, schema mismatch, unsupported shell, malformed JSON |
| `403` | Windows access denied |
| `404` | File or directory not found |
| `504` | Subprocess timeout |
| `500` | Internal operational failure |

## POST /shell

Executes a host command through a selected native shell.

```json
{
  "command": "Get-Process",
  "shell": "powershell",
  "timeout": 30
}
```

Supported selectors:

- `powershell` (default): runs `powershell -Command`.
- `cmd`: runs `cmd.exe /d /s /c`.
- `bash`: runs Git Bash, using `JULES_BASH_PATH` first, then local Git install paths, then `PATH`.

WSL is intentionally rejected because this host exposes `wsl.exe` without an installed distribution.

## File And Inbox Payloads

```json
POST /fs/read
{"path": "C:\\Windows\\win.ini", "offset": 0, "limit": 50}
```

```json
POST /fs/write
{"path": "C:\\tmp\\bridge.txt", "content": "hello"}
```

```json
POST /inbox/read
{"file": "OPERATOR_RESPONSE.md"}
```

```json
POST /inbox/write
{"file": "JULES_RESPONSE.md", "content": "message"}
```

`/fs/write` accepts either `content` or `data`; one must be explicitly present.

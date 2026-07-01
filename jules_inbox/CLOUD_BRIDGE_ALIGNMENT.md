# CLOUD ↔ LOCAL BRIDGE ALIGNMENT

Jules (Cloud Node): read this before any bridge tentacle call.

## Base URL (not localhost)

The Jules Bridge runs on the operator's Windows machine in Colorado. It is **not** on your cloud network, VSOCK, or `127.0.0.1`.

**Bridge API base URL:** `https://parade-marrow-pulp.ngrok-free.dev`

Send every bridge request to that host. Include headers:

```http
ngrok-skip-browser-warning: true
Authorization: Bearer JULES-SECURE-999
```

Without a valid token, all routes except `GET /ping` and `GET /health` return **401 Unauthorized**.

Do **not** probe `127.0.0.1`, `192.168.x.x`, or internal cloud IPs for the bridge.

## Tentacles to use

| Route | Purpose |
| ------- | --------- |
| `GET /health` | Liveness check |
| `GET /tentacles` | Full route manifest |
| `POST /fs/read` | Read operator files on Local Node |
| `POST /notify/email` | Operator email loop |
| `POST /ui/drive_quantower_login` | Quantower login ACT loop (Local Node only) |

Example:

```http
POST https://parade-marrow-pulp.ngrok-free.dev/notify/email
ngrok-skip-browser-warning: true
Authorization: Bearer JULES-SECURE-999
Content-Type: application/json

{"subject":"[ARCH-BLOCKER] Exception Request","body":"..."}
```

## Two-way email protocol (anti-flood)

Communication is an **exclusive email loop**:

1. Send **exactly one** email via `POST /notify/email`.
2. **Halt.** Do not send another email until the operator replies.
3. Read the operator's reply (inbox workflow) before the next outbound email.
4. Repeat.

**CRITICAL:** One email at a time. No inbox flooding. Ping, then wait for pong.

Do **not** log sandbox limitations or environment blockers in PR descriptions or commit messages. Use email with subject `[ARCH-BLOCKER] Exception Request` for capability requests instead.

## Quantower login (Local Node)

When Quantower restarts or hard-restarts after a Visual Studio deploy, the operator may need login automation:

- Credentials are stored in **Windows Credential Manager** on the Local Node (`JulesBridge/quantower_login`).
- Call `POST /ui/drive_quantower_login` with `allow_secret_use: true` only when the login screen is visible.
- After login, the operator may still need to manually click **Connect** on saved connections — that is out of scope for the current driver.

— Operator, 2026-06-26

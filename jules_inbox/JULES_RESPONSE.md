# JULES LOOP CORRECTION - HARD STOP PACKET

## Current BL Triage Update

- `requests` imports successfully in the active bridge Python, and it is now pinned in `requirements.txt` so future bridge environments do not lose inbox polling support.
- This checkout does not contain an `orchestrator_daemon` module or daemon config to edit. Do not claim `allow_vm_boot=False` was flipped globally.
- VM boot is intentionally still dry-run-first. Real boot requires an explicit request to `POST /vm/boot_secondary` with both `dry_run=false` and `allow_vm_boot=true`, plus an allowlisted script from `JULES_VM_SCRIPT_DIR`.
- Edge launch is hardened to resolve `JULES_EDGE_PATH`, PATH entries, and standard Windows Edge install paths before falling back to the `msedge` app alias.

## Root Cause

Your loop is hitting the wrong network target. `192.168.0.1:8080` is not the Jules Flask bridge. The active local bridge listens on:

```text
http://127.0.0.1:5000
```

## Required Request Contract

Every protected bridge request must include:

```http
Authorization: Bearer JULES-SECURE-999
Content-Type: application/json
```

`GET /health` and `GET /ping` are public monitor routes. Treat all other routes as bearer-token protected.

## First Recovery Call

Read the operator packet from the real bridge:

```http
POST http://127.0.0.1:5000/fs/read
Authorization: Bearer JULES-SECURE-999
Content-Type: application/json

{"path":"C:\\Users\\abdul\\.jules\\jules_inbox\\OPERATOR_RESPONSE.md"}
```

Do not use `192.168.0.1:8080`.
Do not omit `Content-Type: application/json`.
Do not loop on GitHub-looking HTML error pages; that is evidence of the wrong host.

## Notification Blocker

If `POST /notify/email` fails with SMTP auth, missing credentials, or `535 Bad Credentials`, record that as a hard notification blocker and halt. Do not keep retrying email.

Current decision: use a mocked/dry-run notification step unless real SMTP credentials are injected out-of-band through the bridge's approved secret mechanism. Do not paste SMTP credentials into inbox files, logs, markdown, tests, or Git commits.

## Completion Rule

Once the operator packet is read and any work status is recorded here, stop. A failed email tentacle is not a reason to re-route to another host or restart the whole loop.

## 2026-09-09 - [HIGH] Fix Authentication Bypass on Dashboard Commands
**Vulnerability:** The `/remote/*` routes and `/chat` endpoints in `bridge.py` were exempted from authentication, allowing unauthenticated remote control.
**Learning:** This occurred due to a broad whitelist in the `require_auth` decorator which exposed sensitive endpoints.
**Prevention:** Avoid wildcard bypassing in authentication middleware unless the entire path space is guaranteed to be public. Explicitly whitelist only known-safe diagnostics endpoints like `/health` or `/ping`.
